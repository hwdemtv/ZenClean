"""
cloud_engine.py — ZenClean 云端 AI 分析引擎（真实后端代理网关版）

流程：
  1. 客户端用本地缓存的 VIP JWT Token 作为 Authorization 鉴权
  2. 将脱敏后的目录路径 POST 到 hw-license-center 的 AI 代理网关
  3. 后端校验 JWT + 扣减今日额度 → 转发请求至智谱清言
  4. 客户端接收 SSE 流式响应并拼装为完整文本
  5. 从 AI 回复中提取 risk_level 和 ai_advice
"""

import time
import json
import requests
import threading
from typing import Dict
from collections import deque

from core.logger import logger
from core.auth import _load_local_token
from config.settings import (
    AI_ANALYZE_URL,
    AI_QUOTA_URL,
    AI_REQUEST_TIMEOUT,
    AI_CLIENT_RATE_LIMIT,
    AI_CLIENT_RATE_WINDOW,
    AI_CACHE_FILE,
)
import uuid
from core.auth import _generate_api_signature

# ── 线程安全的目录级缓存 ──────────────────────────────────────────────────────
# 同一目录下的数千个缓存文件共享同一判定结果，避免重复请求
_dir_cache: Dict[str, dict] = {}
_cache_lock = threading.Lock()
_cache_write_lock = threading.Lock()  # 写盘操作的信号量，防止并发写文件

def _load_cache_from_disk():
    """程序启动时，从本地 JSON 加载曾经的 AI 判决记忆"""
    if AI_CACHE_FILE.exists():
        try:
            with open(AI_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                with _cache_lock:
                    _dir_cache.update(data)
            logger.info(f"Loaded {len(data)} AI judgments from local persistent cache.")
        except Exception as e:
            logger.error(f"Failed to load AI cache from {AI_CACHE_FILE}: {e}")

def _save_cache_to_disk():
    """将运行期间收集的新 AI 判决增量保存到本地硬盘（线程安全）"""
    # 使用信号量防止并发写盘导致的数据竞争
    if not _cache_write_lock.acquire(blocking=False):
        # 如果已有写盘线程在运行，跳过本次写操作
        return

    try:
        AI_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _cache_lock:
            # 安全拷贝一份当前数据进行写盘，避免一直占据锁
            data_to_save = _dir_cache.copy()

        with open(AI_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save AI cache to disk: {e}")
    finally:
        _cache_write_lock.release()

# 初始化时自动加载持久化缓存
_load_cache_from_disk()

# ── 客户端侧滑动窗口限流器 ────────────────────────────────────────────────────
_request_timestamps: deque = deque()
_rate_lock = threading.Lock()


def _is_rate_limited() -> bool:
    """检查是否超过客户端侧的请求频率限制"""
    now = time.time()
    with _rate_lock:
        # 清除窗口外的旧时间戳
        while _request_timestamps and _request_timestamps[0] < now - AI_CLIENT_RATE_WINDOW:
            _request_timestamps.popleft()
        if len(_request_timestamps) >= AI_CLIENT_RATE_LIMIT:
            return True
        _request_timestamps.append(now)
        return False


def _get_parent_dir(sanitized_path: str) -> str:
    """获取脱敏路径的父目录作为分析特征"""
    import os
    try:
        return os.path.dirname(sanitized_path)
    except Exception:
        return sanitized_path


def _parse_sse_stream(response: requests.Response) -> str:
    """
    解析 SSE (Server-Sent Events) 流式响应，拼装成完整的 AI 回复文本。
    后端使用 OpenAI 兼容格式的 SSE：
      data: {"choices":[{"delta":{"content":"..."}}]}
      data: [DONE]
    """
    full_text = ""
    response.encoding = 'utf-8'  # 强制使用 UTF-8 解码，防止中文乱码
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
            # 兼容 OpenAI 标准 SSE 格式
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_text += content
        except json.JSONDecodeError:
            # 非标准行，跳过
            continue
    return full_text


def _extract_risk_from_text(ai_text: str) -> dict:
    """
    从 AI 大模型的自然语言回复中提取结构化的 risk_level 和 ai_advice。
    AI 被提示返回类似 "风险等级: LOW\n建议: ..." 的格式。
    如果无法解析则默认为 UNKNOWN。
    """
    # 清理可能存在的 Markdown 代码块包裹
    cleaned_text = ai_text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    cleaned_text = cleaned_text.strip()

    # 尝试解析 JSON 格式的回复
    try:
        parsed = json.loads(cleaned_text)
        if "risk_level" in parsed:
            return {
                "risk_level": parsed["risk_level"].upper(),
                "ai_advice": parsed.get("ai_advice", parsed.get("advice", ai_text)),
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # 尝试从纯文本中提取风险等级关键词
    text_upper = ai_text.upper()
    risk_level = "UNKNOWN"
    for level in ("CRISIS", "HIGH", "MEDIUM", "LOW"):
        if level in text_upper:
            risk_level = level
            break

    return {
        "risk_level": risk_level,
        "ai_advice": ai_text.strip()[:200],  # 截取前 200 字符作为建议
    }


def query(sanitized_path: str) -> dict:
    """
    接收来自 local_engine 的脱敏路径，通过后端代理网关请求 AI 分析。

    返回:
        {"risk_level": "LOW|MEDIUM|HIGH|CRISIS|UNKNOWN", "ai_advice": "..."}
    """
    dir_path = _get_parent_dir(sanitized_path)

    # 1. 查询高速缓存
    with _cache_lock:
        if dir_path in _dir_cache:
            return _dir_cache[dir_path]

    # 2. 客户端侧限流检查
    if _is_rate_limited():
        logger.warning("客户端侧 AI 请求限流触发，跳过本次请求")
        return _fallback("客户端请求频率超限，请稍后再试。", dir_path)

    # 3. 获取本地缓存的 VIP JWT Token
    token, _, _ = _load_local_token()
    if not token:
        logger.warning("未找到有效的 JWT Token，无法请求 AI 网关")
        return _fallback("请先激活 VIP 以使用云端 AI 分析功能。", dir_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # 4. 构造请求体并计算签名
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 Windows 系统清理专家。用户会给你一个 Windows 文件路径，"
                    "请判断该路径下的文件是否为可安全删除的缓存/临时文件。"
                    "请直接返回 JSON 格式：{\"risk_level\": \"LOW|MEDIUM|HIGH|CRISIS\", \"ai_advice\": \"简短描述\"}"
                    "\n- LOW: 安全删除的缓存/临时文件"
                    "\n- MEDIUM: 可能有用但非关键的文件"
                    "\n- HIGH: 包含用户数据或重要配置"
                    "\n- CRISIS: 系统关键文件，绝不可删除"
                ),
            },
            {
                "role": "user",
                "content": f"请分析这个路径: {dir_path}",
            },
        ],
        "stream": True,
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    signature = _generate_api_signature(payload_str, timestamp, nonce)
    
    headers.update({
        "X-Request-Timestamp": timestamp,
        "X-Request-Nonce": nonce,
        "X-Request-Signature": signature
    })

    logger.info(f"向云端 AI 网关发送分析请求: {dir_path}")

    try:
        # 5. 发送 SSE 流式请求
        res = requests.post(
            AI_ANALYZE_URL,
            data=payload_str,
            headers=headers,
            timeout=AI_REQUEST_TIMEOUT,
            stream=True,
        )

        if res.status_code == 200:
            # 解析 SSE 流
            ai_text = _parse_sse_stream(res)
            if ai_text:
                result = _extract_risk_from_text(ai_text)
                logger.info(f"云端 AI 判定: {dir_path} → {result['risk_level']}")

                # 写入内存缓存
                with _cache_lock:
                    _dir_cache[dir_path] = result
                    
                # 【新功能】如果判定结果不是 UNKNOWN 或出错，则持久化到硬盘，避免后续重启产生计费
                if result["risk_level"] != "UNKNOWN":
                    # 使用异步线程落盘，不影响当前扫描性能
                    threading.Thread(target=_save_cache_to_disk, daemon=True).start()
                    
                return result
            else:
                logger.warning("云端 AI 返回了空响应")

        elif res.status_code == 429:
            logger.warning("云端 AI 每日额度已耗尽或请求过频")
            return _fallback("今日 AI 分析额度已用完，请明日再试。", dir_path)

        elif res.status_code in (401, 403):
            logger.warning(f"云端 AI 鉴权失败: HTTP {res.status_code}")
            return _fallback("[AUTH_FAILED] VIP 授权验证失败或已被吊销，请重新激活。", dir_path)

        else:
            logger.warning(f"云端 AI 请求失败: HTTP {res.status_code}")

    except requests.exceptions.Timeout:
        logger.warning(f"云端 AI 请求超时: {dir_path}")
    except requests.exceptions.ConnectionError:
        logger.warning("无法连接到云端 AI 网关，请检查网络")
    except Exception as e:
        logger.error(f"云端 AI 请求异常: {e}")

    # 6. 任何异常，优雅降级
    return _fallback("云端 AI 服务暂不可用，无法判定风险。", dir_path)


def _fallback(advice: str, dir_path: str) -> dict:
    """返回降级结果并写入短效缓存，防止网络故障时每个文件都卡超时"""
    result = {
        "risk_level": "UNKNOWN",
        "ai_advice": advice,
    }
    with _cache_lock:
        _dir_cache[dir_path] = result
    return result


def get_quota() -> dict | None:
    """
    查询当前用户的 AI 每日剩余额度。
    返回: {"daily_limit": 100, "used_today": 5, "remaining": 95} 或 None
    """
    token, _, _ = _load_local_token()
    if not token:
        return None

    try:
        # GET 请求无需对 Payload 加密散列，传入空字符串
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        signature = _generate_api_signature("", timestamp, nonce)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Request-Timestamp": timestamp,
            "X-Request-Nonce": nonce,
            "X-Request-Signature": signature
        }
        res = requests.get(
            AI_QUOTA_URL,
            headers=headers,
            timeout=5,
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                return data.get("quota")
    except Exception as e:
        logger.debug(f"查询 AI 额度失败: {e}")

    return None


def is_mock() -> bool:
    """标识已切入真实云端引擎"""
    return False
