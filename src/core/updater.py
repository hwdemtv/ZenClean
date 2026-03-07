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
                except Exception as e:
                    logger.warning(f"[Updater] Backend API check failed: {e}")

            # 降级：如果商业网关未配置或失败，尝试 GitHub Release
            if UPDATE_CHECK_URL:
                logger.info(f"[Updater] Fallback checking GitHub: {UPDATE_CHECK_URL}")
                res = requests.get(UPDATE_CHECK_URL, timeout=5)
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
                        on_result(False, APP_VERSION, "", "通过全网检索，当前已是最新版本。")
                        return

            if manual:
                on_result(False, APP_VERSION, "", "无法连接到更新服务器，请稍后再试。")

        except Exception as e:
            logger.error(f"[Updater] Error checking for updates: {e}")
            if manual:
                on_result(False, "", "", f"检查更新异常: {e}")

    threading.Thread(target=_check, daemon=True).start()

