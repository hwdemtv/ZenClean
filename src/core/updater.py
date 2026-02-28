import threading
import requests
from config.settings import UPDATE_CHECK_URL, APP_VERSION
from core.logger import logger

def check_for_updates(on_update_found):
    """
    异步检查是否有新版本，如果有则通过回调函数通知主线程 UI。
    """
    if not UPDATE_CHECK_URL:
        return

    def _check():
        try:
            logger.info(f"Checking for updates at {UPDATE_CHECK_URL}")
            res = requests.get(UPDATE_CHECK_URL, timeout=5)
            if res.status_code == 200:
                data = res.json()
                latest_version = data.get("tag_name", "")
                if latest_version and latest_version != APP_VERSION:
                    logger.info(f"New version found: {latest_version}")
                    html_url = data.get("html_url", "")
                    on_update_found(latest_version, html_url)
                else:
                    logger.info("Application is up to date.")
            else:
                logger.warning(f"Failed to check updates, status code: {res.status_code}")
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")

    threading.Thread(target=_check, daemon=True).start()
