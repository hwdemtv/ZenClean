import json
import time
import hmac
import hashlib
import uuid
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

# 客户端与发卡中心约定的防刷加盐密钥（硬编码在代码中，配合后续的 Cython 混淆）
API_SIGNATURE_SECRET = "zc-hwas-v1-x9fq8p2m"

def get_device_id() -> str:
    """获取设备唯一硬件标识（此处使用 py-machineid）"""
    try:
        return machineid.id()
    except Exception as e:
        logger.error(f"Failed to get machine ID: {e}")
        # 降级方案：使用一个占位 MAC 或 fallback
        return "fallback-device-id"


def _check_time_drift() -> bool:
    """内部辅助：简易 NTP 时间检测。如果彻底离线，由于无法比对，视为通过（信任本地 JWT 的 exp）。"""
    try:
        # 尝试从服务端获取时间，只要有一个通了就比对
        server_time = None
        for url in LICENSE_SERVER_URLS:
            try:
                res = requests.head(url, timeout=3)
                server_date_str = res.headers.get("Date")
                if server_date_str:
                    from email.utils import parsedate_to_datetime
                    server_time = parsedate_to_datetime(server_date_str).timestamp()
                    break
            except Exception:
                continue
        
        if server_time is None:
            # 彻底离线，无法获取网络基准时间，跳过 NTP 检查
            logger.info("Offline: Unable to sync server time, skipping NTP drift check.")
            return True
            
        local_time = time.time()
        if abs(local_time - server_time) > NTP_MAX_DRIFT_SECONDS:
            logger.warning(f"Time drift detected! Local={local_time}, Server={server_time}, Abs={abs(local_time - server_time)}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"NTP drift check encountered error: {e}")
        return True


import platform

def get_device_name() -> str:
    """获取当前计算机名称"""
    try:
        return platform.node() or "Unknown-Device"
    except Exception as e:
        logger.error(f"Failed to get device name: {e}")
        return "Unknown-Device"

def _generate_api_signature(payload_str: str, timestamp: str, nonce: str) -> str:
    """生成防刷接口所需的防重放 HMAC-SHA256 签名"""
    # 按照 约定好 的顺序拼接将要签名的字符串
    message = f"{payload_str}{timestamp}{nonce}"
    signature = hmac.new(
        API_SIGNATURE_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_license_online(license_key: str, is_auto_check: bool = False) -> tuple[bool, str, Optional[dict]]:
    """
    通过 HTTP POST 向 hw-license-center 发起在线校验。
    成功则缓存 JWT token 到本地 AUTH_DAT_PATH。
    is_auto_check=True: 标识本次为后台静默探活，请求服务端『仅查询状态，禁止自动接管闲置的激活码并绑定当前设备』。
    返回: (是否成功, 消息, 可选的通知对象)
    """
    device_id = get_device_id()
    device_name = get_device_name()
    payload_dict = {
        "license_key": license_key,
        "device_id": device_id,
        "device_name": device_name,
        "product_id": LICENSE_PRODUCT_ID,
        "mode": "silent" if is_auto_check else "active"
    }
    
    # 构建安全头 (Security Headers)
    payload_str = json.dumps(payload_dict, separators=(',', ':')) # 紧凑格式确保不产生空格漂移
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    signature = _generate_api_signature(payload_str, timestamp, nonce)
    
    headers = {
        "Content-Type": "application/json",
        "X-Request-Timestamp": timestamp,
        "X-Request-Nonce": nonce,
        "X-Request-Signature": signature
    }
    
    masked_key = f"{license_key[:7]}******" if len(license_key) > 7 else "******"
    logger.info(f"Verifying license online (auto={is_auto_check}): {masked_key}")

    # 循环请求各节点
    last_error_msg = "网络连接失败，请检查网络"
    connection_errors = []
    
    for url in LICENSE_SERVER_URLS:
        try:
            res = requests.post(
                f"{url}/api/v1/auth/verify",
                data=payload_str,
                headers=headers,
                timeout=10
            )
            # 无论成功失败，尝试抓取可能存在的全局广播通知
            notification = None
            try:
                res_data = res.json()
                notification = res_data.get("notification")
            except Exception:
                pass

            if res.status_code == 200:
                data = res.json()
                if data.get("success"):
                    products = data.get("products", [])
                    my_sub = next((p for p in products if p.get("product_id") == LICENSE_PRODUCT_ID), None)

                    if my_sub and my_sub.get("status") == "active":
                        token = data.get("token")
                        expires_at = my_sub.get("expires_at")
                        if token:
                            # 防御性编程：如果是自动后台检查，我们需要检查是否发生了“服务端自动换发新令牌”（即解绑后由服务器无感地为该机器又颁发了一个新绑定）。
                            if is_auto_check:
                                _, old_payload = check_local_auth_status()
                                if old_payload:
                                    try:
                                        import base64
                                        def decode_jwt(t):
                                            parts = t.split('.')
                                            if len(parts) < 2: return {}
                                            payload_b64 = parts[1]
                                            payload_b64 += '=' * (-len(payload_b64) % 4)
                                            return json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
                                            
                                        new_payload = decode_jwt(token)
                                        old_iat = old_payload.get('iat', 0)
                                        new_iat = new_payload.get('iat', 0)
                                        
                                        logger.info(f"IAT Comparison: server={new_iat}, local={old_iat}, diff={new_iat - old_iat}")
                                        
                                        # 如果服务器下发了全新的 Token（签发时间更晚），说明它在后台把我们当做空置码的“新设备”重新执行了绑定。
                                        # 为了严格尊重管理员在后台的“解绑”操作，静默探活时我们主动拒绝这种被动重绑，并执行本地降级。
                                        if new_iat > old_iat:
                                            logger.warning(f"Detected auto-rebind (server iat > local iat). This means the device was unbound and auto-rebound. Blocking.")
                                            return False, "[REVOKED] 您的设备已在后台解绑，请重新输入激活码", notification
                                    except Exception as e:
                                        logger.error(f"Failed to compare tokens for auto-rebind prevention: {e}")
                            
                            _save_local_token(token, expires_at, license_key=license_key)
                            # 掩盖具体 URL，防止日志暴露验证节点
                            masked_url = f"{url.split('//')[0]}//{url.split('//')[1].split('.')[0]}.***.***" if "//" in url else "***"
                            logger.info(f"Online verification passed via {masked_url}. Token cached.")
                            return True, "激活成功", notification
                        else:
                            return False, "服务端未返回授权令牌", notification
                    else:
                        return False, "未发现有效的本产品订阅", notification
                else:
                    return False, data.get("msg", "验证失败"), notification
            else:
                # 尝试解析 4xx 业务级拦截的 JSON 错误信息
                try:
                    err_data = res.json()
                    last_error_msg = err_data.get("msg", f"授权拒绝: {res.status_code}")
                    # 对于 400/401/403/404 明确的授权失效，返回特殊标识以触发客户端降级
                    if res.status_code in (400, 401, 403, 404):
                        return False, f"[REVOKED] {last_error_msg}", notification
                except Exception:
                    last_error_msg = f"服务端异常: {res.status_code} ({res.text[:100]})"
                logger.warning(f"授权服务端返回 {res.status_code}")
        except requests.RequestException as e:
            # 对用户提示屏蔽具体域名，仅保留错误类型；完整细节写入日志便于排查
            error_detail = f"{type(e).__name__}: {str(e)[:100]}"
            connection_errors.append(error_detail)
            logger.warning(f"授权服务器连接失败: {type(e).__name__}")
            continue

    # 增强错误消息，包含诊断信息（但不暴露具体域名）
    if connection_errors:
        error_msg = "网络连接失败，请检查网络\n\n详细错误:\n"
        error_msg += "\n".join(f"- {e}" for e in connection_errors[:2])
        error_msg += "\n\n建议: 检查防火墙/杀毒软件是否拦截了 ZenClean 的网络请求，或联系管理员排查代理/网关策略"
        return False, error_msg, None
    return False, last_error_msg, None


def _save_local_token(token: str, backend_expires_at: Optional[str] = None, *, license_key: Optional[str] = None) -> None:
    """持久化保存 JWT token 和服务端返回的总过期时间"""
    try:
        AUTH_DAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # 存储为 JSON
        payload = {"token": token, "backend_expires_at": backend_expires_at}
        if license_key:
            payload["license_key"] = license_key
        with open(AUTH_DAT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception as e:
        logger.error(f"Failed to save local token: {e}")


def _load_local_token() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """加载本地的 JWT token 及后端的过期时间及 license_key"""
    if AUTH_DAT_PATH.exists():
        try:
            with open(AUTH_DAT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("{"):
                    data = json.loads(content)
                    return data.get("token"), data.get("backend_expires_at"), data.get("license_key")
                else:
                    return content, None, None  # 兼容旧版本纯文本的 token
        except Exception as e:
            logger.error(f"Failed to read local token: {e}")
    return None, None, None


def check_local_auth_status(is_startup: bool = False) -> tuple[bool, Optional[dict]]:
    """
    隐式校验：读取本地缓存。
    is_startup: 如果为 True，则跳过耗时的 NTP 网络比对，优先保证 UI 瞬间启动。
    """
    token, backend_expires_at, license_key = _load_local_token()
    if not token:
        return False, None

    # 1. 只有在非启动状态（如例行检查）才进行耗时的 NTP 防篡改检查
    if not is_startup:
        if not _check_time_drift():
            logger.warning("Local time is fake. Forcing online verification.")
            return False, None
    else:
        logger.info("Startup: Skipping NTP check to speed up launch.")

    # 2. 解析 JWT（由于客户端无 Secret，关闭验签，仅校验 payload 内容）
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        decoded["_backend_expires_at"] = backend_expires_at
        decoded["_local_license_key"] = license_key
        
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
