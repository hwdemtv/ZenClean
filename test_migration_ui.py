import flet as ft
import os
import sys
# 添加 src 目录到路径
sys.path.append(os.path.join(os.getcwd(), "src"))

from ui.views.app_migration_view import AppMigrationView
from config.settings import COLOR_ZEN_BG

class MockApp:
    def __init__(self, page):
        self.page = page
        self.is_activated = True
    
    def navigate_to(self, route):
        print(f"Navigating to: {route}")
        if route == "/scan":
            self.page.snack_bar = ft.SnackBar(ft.Text("模拟返回扫描页"))
            self.page.snack_bar.open = True
            self.page.update()

    def show_snack_bar(self, msg, is_error=False):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="red" if is_error else "green")
        self.page.snack_bar.open = True
        self.page.update()

def main(page: ft.Page):
    page.title = "AppMigrationView Test"
    page.bgcolor = COLOR_ZEN_BG
    page.client_storage.set("assets_dir", os.path.join(os.getcwd(), "assets"))
    
    app = MockApp(page)
    view = AppMigrationView(app)
    
    page.add(view)
    page.update()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8559)
