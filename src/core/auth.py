import json
import time
from pathlib import Path
from typing import Optional

import jwt
import machineid
import requests

from config.settings import (
    AUTH_DAT_PATH,
    LICENSE_PRODUCT_ID,
    LICENSE_SERVER_URLS,
    NTP_MAX_DRIFT_SECONDS,
)

# 使用统一的全局 logger
from core.logger import logger


def get_device_id() -> str:
    """获取设备唯一硬件标识（此处使用 py-machineid）"""
    try:
        return machineid.id()
    except Exception as e:
        logger.error(f"Failed to get machine ID: {e}")
        # 降级方案：使用一个占位 MAC 或 fallback
        return "fallback-device-id"


def _check_time_drift() -> bool:
    """内部辅助：简易 NTP 时间防篡改检测（通过 HTTP Date 响应头）"""
    try:
        # 循环尝试各服务端进行时间校准
        for url in LICENSE_SERVER_URLS:
            try:
                res = requests.head(url, timeout=3)
                server_date_str = res.headers.get("Date")
                if server_date_str:
                    # 解析 RFC 2822 时间
                    from email.utils import parsedate_to_datetime
                    server_time = parsedate_to_datetime(server_date_str).timestamp()
                    local_time = time.time()
                    if abs(local_time - server_time) > NTP_MAX_DRIFT_SECONDS:
                        logger.warning("NTP time drift detected!")
                        return False
                    return True
            except requests.RequestException:
                continue
        # 所有节点都请求失败则视为离线，暂时放行
        logger.info("Offline: Skip NTP check.")
        return True
    except requests.RequestException:
        # 离线时无法校验防篡改，暂时放行（依赖后续基于 JWT 过期时间的防御）
        logger.info("Offline: Skip NTP check.")
        return True
    except Exception as e:
        logger.error(f"NTP drift check error: {e}")
        return True


import platform

def get_device_name() -> str:
    """获取当前计算机名称"""
    try:
        return platform.node() or "Unknown-Device"
    except Exception as e:
        logger.error(f"Failed to get device name: {e}")
        return "Unknown-Device"

def verify_license_online(license_key: str) -> tuple[bool, str]:
    """
    通过 HTTP POST 向 hw-license-center 发起在线校验。
    成功则缓存 JWT token 到本地 AUTH_DAT_PATH。
    """
    device_id = get_device_id()
    device_name = get_device_name()
    payload = {
        "license_key": license_key,
        "device_id": device_id,
        "device_name": device_name
    }
    logger.info(f"Verifying license online: {license_key} for product: {LICENSE_PRODUCT_ID}")

    # 循环请求各节点
    last_error_msg = "网络连接失败，请检查网络"
    
    for url in LICENSE_SERVER_URLS:
        try:
            res = requests.post(f"{url}/api/v1/auth/verify", json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("success"):
                    products = data.get("products", [])
                    my_sub = next((p for p in products if p.get("product_id") == LICENSE_PRODUCT_ID), None)

                    if my_sub and my_sub.get("status") == "active":
                        token = data.get("token")
                        expires_at = my_sub.get("expires_at")
                        if token:
                            _save_local_token(token, expires_at)
                            logger.info(f"Online verification passed via {url}. Token cached.")
                            return True, "激活成功"
                        else:
                            return False, "服务端未返回授权令牌"
                    else:
                        return False, "未发现有效的本产品订阅"
                else:
                    return False, data.get("msg", "验证失败")
            else:
                last_error_msg = f"服务端异常: {res.status_code} ({res.text[:100]})"
                logger.warning(f"Server {url} returned {res.status_code}: {res.text}")
        except requests.RequestException as e:
            logger.warning(f"Failed to connect to {url}: {e}")
            continue

    return False, last_error_msg


def _save_local_token(token: str, backend_expires_at: Optional[str] = None) -> None:
    """持久化保存 JWT token 和服务端返回的总过期时间"""
    try:
        AUTH_DAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # 存储为 JSON
        payload = {"token": token, "backend_expires_at": backend_expires_at}
        with open(AUTH_DAT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception as e:
        logger.error(f"Failed to save local token: {e}")


def _load_local_token() -> tuple[Optional[str], Optional[str]]:
    """加载本地的 JWT token 及后端的过期时间"""
    if AUTH_DAT_PATH.exists():
        try:
            with open(AUTH_DAT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("{"):
                    data = json.loads(content)
                    return data.get("token"), data.get("backend_expires_at")
                else:
                    return content, None  # 兼容旧版本纯文本的 token
        except Exception as e:
            logger.error(f"Failed to read local token: {e}")
    return None, None


def check_local_auth_status() -> tuple[bool, Optional[dict]]:
    """
    启动时隐式校验：读取本地缓存的 JWT Token 判断当前设备是否处于授权保护期内。
    """
    token, backend_expires_at = _load_local_token()
    if not token:
        logger.info("No local token found.")
        return False, None

    # 1. NTP 防篡改检查
    if not _check_time_drift():
        logger.warning("Local time is fake. Forcing online verification.")
        return False, None

    # 2. 解析 JWT（由于客户端无 Secret，关闭验签，仅校验 payload 内容）
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        decoded["_backend_expires_at"] = backend_expires_at
        
        # 效验过期时间
        exp = decoded.get("exp")
        if exp and exp < time.time():
            logger.info("Local token expired.")
            return False, decoded
            
        # 效验设备是否匹配（防止直接拷贝缓存文件到别机）
        token_device_id = decoded.get("device_id")
        current_device_id = get_device_id()
        if token_device_id and token_device_id != current_device_id:
            logger.warning(f"Device ID mismatch: {token_device_id} vs {current_device_id}")
            return False, decoded
            
        logger.info("Offline verification passed using cached JWT token.")
        return True, decoded

    except Exception as e:
        logger.error(f"Failed to decode or verify local token: {e}")
        return False, None
