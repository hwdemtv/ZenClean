import flet as ft
import threading
import time
from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_PRIMARY, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM
)

class SplashView(ft.Container):
    def __init__(self, app):
        self.app = app
        super().__init__(
            content=ft.Column(
                [
                    ft.Image(
                        src="icon.png",
                        width=100,
                        height=100,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    ft.Text(
                        "ZenClean 禅清",
                        size=40,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_ZEN_TEXT_MAIN,
                    ),
                    ft.Text(
                        "初始化深层防护扫描引擎...",
                        size=16,
                        color=COLOR_ZEN_TEXT_DIM,
                    ),
                    ft.Container(height=30),
                    ft.ProgressBar(width=400, color=COLOR_ZEN_PRIMARY, bgcolor="#333333"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor=COLOR_ZEN_BG,
            alignment=ft.alignment.center,
        )

    def start(self) -> None:
        """由 app.navigate_to 在将本视图挂载到页面后调用，启动倒计时跳转。"""
        def _jump():
            time.sleep(1.5)
            self.app.navigate_to("/scan")

        threading.Thread(target=_jump, daemon=True).start()
