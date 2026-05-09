import os
import threading
import requests
import json
from config.settings import UPDATE_CHECK_URL, LICENSE_SERVER_URLS, FALLBACK_DOWNLOAD_URL
from config.version import __version__ as APP_VERSION
from core.logger import logger

def check_for_updates(on_result, manual=False):
    """
    异步检查是否有新版本。
    :param on_result: 回调函数 `def callback(has_new: bool, version: str, url: str, msg: str)`
    :param manual: 是否为用户手动点击，如果是手动点击，即使没有新版也要给予回馈。
    """
    def _check():
        try:
            # 优先尝试从咱们的商业授权网关获取更新通知 (方案二)
            if LICENSE_SERVER_URLS:
                base_url = LICENSE_SERVER_URLS[0].rstrip("/")
                # 修正路径：服务端 publicRoutes 挂载在 /api/v1/auth 下，对应的更新接口应当是 /auth/update
                update_api = f"{base_url}/api/v1/auth/update?product=zenclean&version={APP_VERSION}"
                # 尝试 2 次重试机制以应对瞬时网络抖动 (如 502/504)
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        # 缩短超时时间，网关抖动时快速失败并切镜像
                        res = requests.get(update_api, timeout=3)
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("code") == 200 and data.get("data"):
                                d = data["data"]
                                if d.get("has_update") and d.get("version") != APP_VERSION:
                                    on_result(True, d.get("version"), d.get("url") or FALLBACK_DOWNLOAD_URL, d.get("desc", "发现新版本！"))
                                    return
                                elif manual:
                                    on_result(False, APP_VERSION, "", "恭喜，当前已是最新版本。")
                                    return
                            break # code 不对，不再重试
                        elif 400 <= res.status_code <= 599:
                            # 如果是 4xx 或 5xx 错误，说明服务端该端点不可用，直接中断重试进入镜像降级流程
                            logger.info(f"[Updater] 商业网关响应异常 ({res.status_code})，将尝试镜像源...")
                            break
                        else:
                            logger.info(f"[Updater] 商业网关返回状态: {res.status_code}, 停止重试。")
                            break
                    except (requests.Timeout, requests.ConnectionError):
                        logger.warning(f"[Updater] 商业网关请求超时/连接失败 ({attempt+1}/{max_retries})")
                        if attempt == max_retries - 1: break
                    except Exception as e:
                        logger.warning(f"[Updater] 商业网关请求异常: {type(e).__name__}")
                        break

            # 降级：如果商业网关未配置或失败，尝试多重镜像轮询 (GitHub Releases)
            # 方案优化：改用 /releases 列表接口，以支持获取最新的 Pre-release 版本 (Beta 版常用)
            _REPO = "hwdemtv/ZenClean"
            _SELF_HOSTED_PROXY = os.environ.get(
                "GITHUB_PROXY_URL", "https://git.hubinwei.top"
            )
            MIRRORS = [
                f"{_SELF_HOSTED_PROXY}/repos/{_REPO}/releases",
                f"https://api.gitmirror.com/repos/{_REPO}/releases",
                f"https://gh.ddlc.top/https://api.github.com/repos/{_REPO}/releases",
                f"https://ghproxy.net/https://api.github.com/repos/{_REPO}/releases",
                f"https://api.github.com/repos/{_REPO}/releases",
            ]

            import urllib3

            headers = {'User-Agent': f'ZenClean-Client/{APP_VERSION}'}
            for mirror_url in MIRRORS:
                try:
                    logger.info(f"[Updater] 尝试镜像源 #{MIRRORS.index(mirror_url)+1}...")
                    # 首次尝试开启验证
                    try:
                        res = requests.get(mirror_url, timeout=6, headers=headers, verify=True)
                    except requests.exceptions.SSLError:
                        # 如果出现 SSL 错误（常见于部分镜像站证书配置问题），则尝试禁用验证
                        logger.warning(f"[Updater] 镜像源 SSL 验证失败，尝试免验重试（仅用于版本检查，不涉及二进制下载）...")
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        res = requests.get(mirror_url, timeout=6, headers=headers, verify=False)
                    
                    if res.status_code == 200:
                        data = res.json()
                        if not data or not isinstance(data, list):
                            continue
                            
                        # 获取列表中的第一个 Release (即绝对意义上的最新版，包含 Prerelease)
                        latest_release = data[0]
                        latest_version = latest_release.get("tag_name", "").lstrip("v")
                        current_clean = APP_VERSION.lstrip("v")
                        
                        # 使用更加严谨的版本比较逻辑：remote > local
                        from packaging import version
                        try:
                            is_new = version.parse(latest_version) > version.parse(current_clean)
                        except Exception:
                            # 降级：如果无法解析版本号（如格式不规范），则退回到字符串不相等判断
                            is_new = latest_version != current_clean
                        
                        if latest_version and is_new:
                            html_url = FALLBACK_DOWNLOAD_URL
                            body = latest_release.get("body", "发现了新的版本，建议您立刻更新。")
                            on_result(True, latest_version, html_url, body)
                            return
                        elif manual:
                            on_result(False, APP_VERSION, "", "恭喜，当前已是最新版本。")
                            return
                    elif res.status_code == 404:
                        logger.info("[Updater] 当前镜像源无可用版本")
                        continue
                    else:
                        logger.warning(f"[Updater] 镜像源返回异常状态: {res.status_code}")
                except Exception as e:
                    # 尝试从复杂的 SSLError/ConnectionError 对象中提取深层次简明原因
                    err_msg = type(e).__name__
                    try:
                        # e.args[0].reason 可能是 urllib3 内嵌的 SSL 错误
                        if hasattr(e, 'args') and len(e.args) > 0:
                            reason = getattr(e.args[0], 'reason', e)
                            if reason:
                                err_msg = f"{type(e).__name__} ({type(reason).__name__})"
                    except Exception:
                        pass
                    
                    logger.warning(f"[Updater] 镜像源最终访问失败: {err_msg}")
                    continue

            # 如果走到这里还没 return，说明要么没配置地址，要么全部失败
            if manual:
                on_result(False, APP_VERSION, "", "版本检测链路波动，请稍后再试（您可以直接访问官网或网盘查看）。")
        except Exception as e:
            logger.error(f"[Updater] Uncaught error in _check: {e}")
            if manual:
                on_result(False, APP_VERSION, "", f"检查更新过程中出现异常: {e}")

    threading.Thread(target=_check, daemon=True).start()
