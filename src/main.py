import flet as ft
from ui.app import ZenCleanApp


def main(page: ft.Page):
    page.title = "ZenClean (禅清) - 现代 C 盘大扫除"
    page.window.width = 1000
    page.window.height = 700
    page.window.min_width = 800
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed="#00D4AA", use_material3=True)
    page.bgcolor = "#0D0D0D"
    page.padding = 0

    app = ZenCleanApp(page)
    page.add(app)
    # ft.Column 不参与 Flet 路由系统，直接调用自己的导航方法
    app.navigate_to("/")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    ft.app(target=main)
