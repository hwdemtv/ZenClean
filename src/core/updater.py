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
                update_api = f"{base_url}/api/v1/update?product=zenclean&version={APP_VERSION}"
                logger.info("[Updater] 正在检查商业网关更新...")
                try:
                    res = requests.get(update_api, timeout=5)
                    if res.status_code == 200:
                        data = res.json()
                        # 假设后端返回 {"code": 200, "data": {"has_update": true, "version": "v0.2.0", "url": "...", "desc": "..."}}
                        if data.get("code") == 200 and data.get("data"):
                            d = data["data"]
                            if d.get("has_update") and d.get("version") != APP_VERSION:
                                on_result(True, d.get("version"), d.get("url") or FALLBACK_DOWNLOAD_URL, d.get("desc", "发现新版本！"))
                                return
                            elif manual:
                                on_result(False, APP_VERSION, "", "恭喜，当前已是最新版本。")
                                return
                    else:
                        logger.info(f"[Updater] 商业网关返回状态: {res.status_code}")
                except Exception as e:
                    logger.warning(f"[Updater] 商业网关检查失败: {type(e).__name__}")

            # 降级：如果商业网关未配置或失败，尝试多重镜像轮询 (GitHub Releases)
            # 方案优化：改用 /releases 列表接口，以支持获取最新的 Pre-release 版本 (Beta 版常用)
            MIRRORS = [
                "https://api.kkgithub.com/repos/hwdemtv/ZenClean/releases",
                "https://gh-api.99988866.xyz/repos/hwdemtv/ZenClean/releases",
                "https://ghapi.paniy.xyz/repos/hwdemtv/ZenClean/releases",
                "https://api.github.com/repos/hwdemtv/ZenClean/releases" 
            ]
            
            headers = {'User-Agent': f'ZenClean-Client/{APP_VERSION}'}
            for mirror_url in MIRRORS:
                try:
                    logger.info(f"[Updater] 尝试镜像源 #{MIRRORS.index(mirror_url)+1}...")
                    res = requests.get(mirror_url, timeout=6, headers=headers)
                    
                    if res.status_code == 200:
                        data = res.json()
                        if not data or not isinstance(data, list):
                            continue
                            
                        # 获取列表中的第一个 Release (即绝对意义上的最新版，包含 Prerelease)
                        latest_release = data[0]
                        latest_version = latest_release.get("tag_name", "").lstrip("v")
                        current_clean = APP_VERSION.lstrip("v")
                        
                        if latest_version and latest_version != current_clean:
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
                    logger.warning(f"[Updater] 镜像源访问失败: {type(e).__name__}")
                    continue

            # 如果走到这里还没 return，说明要么没配置地址，要么全部失败
            if manual:
                on_result(False, APP_VERSION, "", "版本检测链路波动，请稍后再试（您可以直接访问官网或网盘查看）。")
        except Exception as e:
            logger.error(f"[Updater] Uncaught error in _check: {e}")
            if manual:
                on_result(False, APP_VERSION, "", f"检查更新过程中出现异常: {e}")

    threading.Thread(target=_check, daemon=True).start()
