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
                logger.info(f"[Updater] Checking backend API: {update_api}")
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
                        logger.info(f"[Updater] Backend API returned status: {res.status_code}")
                except Exception as e:
                    logger.warning(f"[Updater] Backend API check failed (ignore if not deployed): {e}")

            # 降级：如果商业网关未配置或失败，尝试多重镜像轮询 (GitHub Release)
            # 定义国内高质量镜像列表，按稳定性排序
            MIRRORS = [
                "https://api.kkgithub.com/repos/hwdemtv/ZenClean/releases/latest",
                "https://gh-api.99988866.xyz/repos/hwdemtv/ZenClean/releases/latest",
                "https://ghapi.paniy.xyz/repos/hwdemtv/ZenClean/releases/latest",
                "https://api.github.com/repos/hwdemtv/ZenClean/releases/latest" # 官方兜底
            ]
            
            headers = {'User-Agent': f'ZenClean-Client/{APP_VERSION}'}
            for mirror_url in MIRRORS:
                try:
                    logger.info(f"[Updater] Checking mirror: {mirror_url}")
                    res = requests.get(mirror_url, timeout=6, headers=headers)
                    
                    if res.status_code == 200:
                        data = res.json()
                        latest_version = data.get("tag_name", "").lstrip("v")
                        current_clean = APP_VERSION.lstrip("v")
                        
                        if latest_version and latest_version != current_clean:
                            # 强制丢弃 GitHub 原生的 html_url 释放地址，全部使用国内直链
                            html_url = FALLBACK_DOWNLOAD_URL
                            body = data.get("body", "发现了新的版本，建议您立刻更新。")
                            on_result(True, latest_version, html_url, body)
                            return
                        elif manual:
                            on_result(False, APP_VERSION, "", "恭喜，当前已是最新版本。")
                            return
                    elif res.status_code == 404:
                        logger.info(f"[Updater] 404 on {mirror_url}, repo may have no releases.")
                        if manual:
                            on_result(False, APP_VERSION, "", "云端尚未发布新版本，当前已是最新。")
                            return
                    else:
                        logger.warning(f"[Updater] Mirror {mirror_url} returned {res.status_code}")
                except Exception as e:
                    logger.warning(f"[Updater] Mirror {mirror_url} failed: {e}")
                    continue # 尝试下一个镜像

            # 如果走到这里还没 return，说明要么没配置地址，要么全部失败
            if manual:
                on_result(False, APP_VERSION, "", "版本检测链路波动，请稍后再试（您可以直接访问官网或网盘查看）。")
        except Exception as e:
            logger.error(f"[Updater] Uncaught error in _check: {e}")
            if manual:
                on_result(False, APP_VERSION, "", f"检查更新过程中出现异常: {e}")

    threading.Thread(target=_check, daemon=True).start()
