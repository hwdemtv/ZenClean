import flet as ft
import threading
import time


class SplashView(ft.Container):
    def __init__(self, app):
        self.app = app
        super().__init__(
            content=ft.Column(
                [
                    ft.Icon(
                        name=ft.icons.CLEANING_SERVICES_ROUNDED,
                        size=80,
                        color="#00D4AA",
                    ),
                    ft.Text(
                        "ZenClean 禅清",
                        size=40,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                    ft.Text(
                        "初始化深层防护扫描引擎...",
                        size=16,
                        color="#888888",
                    ),
                    ft.Container(height=30),
                    ft.ProgressBar(width=400, color="#00D4AA", bgcolor="#333333"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )

    def start(self) -> None:
        """由 app.navigate_to 在将本视图挂载到页面后调用，启动倒计时跳转。"""
        def _jump():
            time.sleep(1.5)
            self.app.navigate_to("/scan")

        threading.Thread(target=_jump, daemon=True).start()
