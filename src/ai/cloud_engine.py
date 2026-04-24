"""
cloud_engine.py — ZenClean 云端 AI 分析引擎（批处理版）

流程：
  1. 客户端用本地缓存的 VIP JWT Token 作为 Authorization 鉴权
  2. 将脱敏后的目录路径通过 BatchProcessor 聚合为批量请求
  3. 批量 POST 到智谱清言 API，非流式获取 JSON 数组响应
  4. 结果写入内存缓存 + 持久化磁盘缓存
  5. 通过回调链通知 UI 局部刷新
"""

import os
import time
import json
import requests
import threading
from typing import Dict
from collections import deque

from core.logger import logger
from core.auth import _load_local_token, _generate_api_signature
from config.settings import (
    AI_ANALYZE_URL,
    AI_QUOTA_URL,
    AI_REQUEST_TIMEOUT,
    AI_MAX_RETRIES,
    AI_CLIENT_RATE_LIMIT,
    AI_CLIENT_RATE_WINDOW,
    AI_CACHE_FILE,
    LICENSE_SERVER_URLS,
)
import uuid
from .batch_processor import batch_processor

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
    try:
        return os.path.dirname(sanitized_path)
    except Exception:
        return sanitized_path


def _extract_risk_from_text(ai_text: str) -> dict:
    """
    从 AI 大模型的自然语言回复中提取结构化的 risk_level 和 ai_advice。
    作为 JSON 解析失败时的降级兜底。
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


def _normalize_batch_paths(batch_results: list[dict], submitted_paths: list[str]) -> list[dict]:
    """
    归一化 AI 返回的路径，确保与提交路径匹配。
    AI 模型可能返回大小写或末尾分隔符不同的路径，需要统一。
    """
    # 构建提交路径的归一化映射：归一化路径 → 原始路径
    normalized_submitted = {p.rstrip("\\/").lower(): p for p in submitted_paths}

    for res in batch_results:
        path = res.get("path")
        if path:
            normalized = path.rstrip("\\/").lower()
            if normalized in normalized_submitted:
                # 用提交时的原始路径替换 AI 返回的路径，确保匹配
                res["path"] = normalized_submitted[normalized]

    return batch_results


def _build_fallback_results(paths: list[str], advice: str) -> list[dict]:
    """为所有路径构建降级结果（用于 429/401/403 等不应重试的场景）"""
    results = []
    fallback_base = {"risk_level": "UNKNOWN", "ai_advice": advice}
    with _cache_lock:
        for path in paths:
            res = {**fallback_base, "path": path}
            _dir_cache[path] = res
            results.append(res)
    return results


def _batch_analyze(paths: list[str]) -> list[dict]:
    """
    实际执行批量 AI 分析的函数，由 BatchProcessor 回调。
    增强版：HTTP 状态码差异化处理 + 客户端限流 + 路径归一化 + JSON 解析降级。
    """
    if not paths: return []

    # 客户端侧限流检查
    if _is_rate_limited():
        logger.warning("BatchAnalyze: Client rate limit exceeded, skipping batch.")
        return []

    # 获取 Token
    token, _, _ = _load_local_token()
    if not token:
        logger.warning("BatchAnalyze: No token found.")
        return []

    # 构造批量 Prompt
    prompt_paths = "\n".join([f"- {p}" for p in paths])
    system_prompt = (
        "你是一个 Windows 系统清理专家。请分析以下目录路径的风险等级（LOW/MEDIUM/HIGH/CRISIS）。\n"
        "请务必返回一个精简的 JSON 数组格式，每个对象包含 'path' (原始路径), 'risk_level' (级别), 'ai_advice' (10字内建议)。\n"
        "严禁返回任何 Markdown 代码块标签或多余解释。"
    )
    user_prompt = f"分析以下路径：\n{prompt_paths}"

    payload = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "stream": False
    }

    # 动态构建网关轮询列表，保证 AI_ANALYZE_URL 优先，并追加备用的授权网关路径
    urls_to_try = [AI_ANALYZE_URL]
    for _url in LICENSE_SERVER_URLS:
        api_path = f"{_url.rstrip('/')}/api/v1/ai/chat/completions"
        if api_path not in urls_to_try:
            urls_to_try.append(api_path)

    last_error = "云端 AI 服务暂不可用，无法判定风险。"
    for attempt in range(AI_MAX_RETRIES + 1):
        # 轮询获取一个 URL进行尝试
        current_url = urls_to_try[attempt % len(urls_to_try)]
        
        try:
            # 构造签名与请求头
            timestamp = str(int(time.time()))
            nonce = uuid.uuid4().hex
            # 为了确保签名一致性，手动序列化 payload (紧凑格式)
            payload_str = json.dumps(payload, separators=(',', ':'))
            signature = _generate_api_signature(payload_str, timestamp, nonce)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                # 必须设置标准浏览器 User-Agent，否则会被 Cloudflare WAF 拦截
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            response = requests.post(current_url, headers=headers, data=payload_str, timeout=AI_REQUEST_TIMEOUT)

            # ── HTTP 429: 额度耗尽，不应重试 ──
            if response.status_code == 429:
                logger.warning("云端 AI 每日额度已耗尽或请求过频，停止重试")
                return _build_fallback_results(paths, "今日 AI 分析额度已用完，请明日再试。")

            # ── HTTP 401/403: 鉴权失败，记录后尝试下一个节点（不应立即中断，可能是当前 CDN IP 被风控） ──
            if response.status_code in (401, 403):
                try:
                    # 尝试解析业务级错误消息
                    err_json = response.json()
                    err_msg = err_json.get("msg", "未知业务授权错误")
                except Exception:
                    # 如果不是 JSON，可能是 Cloudflare WAF 的 HTML 拦截页面
                    err_msg = response.text[:200].replace("\n", " ")
                    if "<title>Just a moment...</title>" in err_msg or "Cloudflare" in err_msg:
                        err_msg = f"检测到 Cloudflare WAF 拦截 (可能是 IP 被风控或 Header 异常): {err_msg}"
                
                logger.warning(f"云端 AI 鉴权失败 (节点 {current_url}): HTTP {response.status_code} - {err_msg}")
                last_error = f"授权验证失败: {err_msg}"
                raise requests.exceptions.RequestException(f"{response.status_code} Forbidden: {err_msg}")

            # ── HTTP 400: 请求格式错误，记录服务端返回的具体原因 ──
            if response.status_code == 400:
                try:
                    err_body = response.json()
                    logger.warning(f"云端 AI 400 Bad Request: {err_body}")
                except Exception:
                    logger.warning(f"云端 AI 400 Bad Request: {response.text[:500]}")
                return _build_fallback_results(paths, "AI 请求格式错误，请更新至最新版本。")

            response.raise_for_status()

            result_data = response.json()
            content = result_data.get("choices", [{}])[0].get("message", {}).get("content", "[]")

            # 清理可能存在的 Markdown 代码块包裹
            content = content.strip().replace("```json", "").replace("```", "").strip()

            # 尝试解析 JSON
            try:
                batch_results = json.loads(content)
            except json.JSONDecodeError:
                # JSON 解析失败，用文本提取器兜底
                logger.warning("Batch AI response not valid JSON, trying text extraction fallback")
                fallback_result = _extract_risk_from_text(content)
                # 将单个结果关联到第一个路径
                batch_results = [{**fallback_result, "path": paths[0]}]

            if isinstance(batch_results, list):
                # 归一化路径匹配：确保 AI 返回的 path 与提交的 path 一致
                batch_results = _normalize_batch_paths(batch_results, paths)

                # 将分析结果存入持久化缓存
                with _cache_lock:
                    for res in batch_results:
                        path = res.get("path")
                        if path:
                            _dir_cache[path] = res
                _save_cache_to_disk()
                return batch_results

        except requests.exceptions.Timeout:
            logger.warning(f"Batch AI analyze attempt {attempt + 1} timed out on {current_url}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Batch AI analyze attempt {attempt + 1} connection error on {current_url}")
        except Exception as e:
            logger.warning(f"Batch AI analyze attempt {attempt + 1} failed on {current_url}: {type(e).__name__}")

        if attempt < AI_MAX_RETRIES:
            # 指数退避 (1s, 2s)
            time.sleep(1 * (attempt + 1))
        else:
            logger.error(f"Batch AI analyze exhausted all retries")

    # 所有重试耗尽，返回降级结果
    return _build_fallback_results(paths, last_error)

# 注册处理器
batch_processor.set_batch_handler(_batch_analyze)


def query(sanitized_path: str, callback=None) -> dict:
    """
    接收来自 local_engine 的脱敏路径，通过 BatchProcessor 实现异步分析。
    返回的 dict 中包含 _ai_query_key 字段，用于后续回调匹配。
    """
    dir_path = _get_parent_dir(sanitized_path)

    # 1. 查询高速缓存
    with _cache_lock:
        if dir_path in _dir_cache:
            result = _dir_cache[dir_path].copy()
            result["_ai_query_key"] = dir_path
            return result

    # 2. 异步提交到批处理队列（不再阻塞扫描器主线程）
    # 结果会先返回一个 "ANALYZING" 占位符，真实结果稍后通过缓存或回调填充。
    result = batch_processor.submit_async(dir_path, callback=callback)
    # 注入查询键，便于 UI 层回调时匹配节点
    result["_ai_query_key"] = dir_path
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
            else:
                logger.warning(f"AI 额度查询接口返回业务失败: {data.get('msg')}")
        else:
            logger.warning(f"AI 额度查询 HTTP 失败: {res.status_code}, URL: {AI_QUOTA_URL}")
    except requests.exceptions.Timeout:
        logger.warning("AI 额度查询请求超时")
    except Exception as e:
        logger.error(f"查询 AI 额度时发生未预料异常: {e}")

    return None


def is_mock() -> bool:
    """标识已切入真实云端引擎"""
    return False
