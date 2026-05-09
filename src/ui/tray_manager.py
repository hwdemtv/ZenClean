import os
import sys
import threading
import time
import pystray
from PIL import Image
import flet as ft
from core.logger import logger

class TrayManager:
    """
    ZenClean 系统托盘管理器。
    使用 pystray 在独立线程中运行，负责处理托盘图标显示、右键菜单及窗口显示/隐藏逻辑。
    """
    def __init__(self, page: ft.Page, app_instance, assets_dir: str = None):
        self.page = page
        self.app = app_instance
        self.icon = None
        # 优先使用传入的路径，其次是 client_storage，最后保底 assets
        self._assets_dir = assets_dir or self.page.client_storage.get("assets_dir") or "assets"
        self._icon_path = os.path.normpath(os.path.join(self._assets_dir, "icon.png"))
        logger.info(f"[Tray] Initialized with icon path: {self._icon_path}")
        
    def _create_menu(self):
        return pystray.Menu(
            pystray.MenuItem("打开主界面", self._show_window, default=True),
            pystray.MenuItem("一键健康扫描", self._quick_scan),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("彻底退出进程", self._exit_app)
        )

    def _show_window(self, icon=None, item=None):
        """显示并前置主窗口"""
        async def _action():
            self.page.window.visible = True
            self.page.window.minimized = False
            self.page.window.to_front()
            self.page.update()
        # Flet UI 更新必须在主线程/通过内置调度
        self.page.run_task(_action)

    def _quick_scan(self, icon=None, item=None):
        """跳转并自动开始扫描"""
        async def _action():
            self.page.window.visible = True
            self.page.window.minimized = False
            self.page.window.to_front()
            # 设置自动扫描标志，让 ScanView 加载后自动开始扫描
            self.app._auto_start_scan = True
            self.app.navigate_to("/scan")
            self.page.update()
        self.page.run_task(_action)

    def _exit_app(self, icon=None, item=None):
        """真正的销毁流程 (三保险模式)"""
        logger.info("Universal exit triggered. Entering termination sequence...")

        # [保险 1]：启动独立哨兵线程（daemon），3 秒后强制退出作为兜底
        def _forced_sentinel():
            time.sleep(3.0)  # 给正常退出流程足够时间
            logger.info("Sentinel thread forcing exit (normal shutdown timed out)...")
            os._exit(1)

        sentinel = threading.Thread(target=_forced_sentinel, daemon=True)
        sentinel.start()

        # [保险 2]：先尝试隐藏窗口，然后通过 Flet 关闭
        try:
            self.page.window.visible = False
            self.page.window.prevent_close = False
            self.page.update()
            self.page.window.close()
        except Exception as e:
            logger.warning(f"Graceful close failed: {e}")

        # [保险 3]：正常退出（触发 atexit 清理子进程）
        time.sleep(0.5)
        logger.info("Exiting via sys.exit() to allow atexit cleanup...")
        sys.exit(0)

    def run(self):
        """启动托盘线程"""
        if not os.path.exists(self._icon_path):
            logger.error(f"[Tray] Icon not found at: {self._icon_path}")
            # 尝试回退搜索项目根目录下的 assets
            fallback_path = os.path.join(os.getcwd(), "assets", "icon.png")
            if os.path.exists(fallback_path):
                logger.info(f"[Tray] Found fallback icon at: {fallback_path}")
                self._icon_path = fallback_path
            else:
                return

        def _setup():
            try:
                logger.info(f"[Tray] Attempting to load image from {self._icon_path}")
                image = Image.open(self._icon_path)
                self.icon = pystray.Icon(
                    "ZenClean",
                    image,
                    "禅清 (ZenClean)",
                    menu=self._create_menu()
                )
                logger.info("[Tray] pystray.Icon object created, calling run()...")
                self.icon.run()
            except Exception as e:
                logger.error(f"[Tray] Thread execution failed: {e}")

        tray_thread = threading.Thread(target=_setup, daemon=True)
        tray_thread.start()
        logger.info("[Tray] Background thread spawned.")
