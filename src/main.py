import os
import os
import flet as ft
from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_PRIMARY, WINDOW_WIDTH, WINDOW_HEIGHT
)
from ui.app import ZenCleanApp

# 项目根目录（src 的上一级）
_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_ASSETS_DIR = os.path.join(_ROOT, "assets")
_ICON_PATH = os.path.join(_ASSETS_DIR, "icon.ico")


def main(page: ft.Page):
    page.title = "禅清 (ZenClean) ：互为螺旋- C盘AI极速清理大师"
    
    # 启用沉浸式全屏渲染（隐藏原生白条）
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = False # 保留原生关闭/最小化按钮但背景透明

    # Windows 桌面端需要绝对路径指向 .ico 文件
    if os.path.isfile(_ICON_PATH):
        page.window.icon = _ICON_PATH

    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT + 40 # 增加一点高度给自定义顶栏
    page.window.min_width = 800
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=COLOR_ZEN_PRIMARY, use_material3=True)
    page.bgcolor = COLOR_ZEN_BG
    page.padding = 0

    app = ZenCleanApp(page)
    page.add(app)
    # ft.Column 不参与 Flet 路由系统，直接调用自己的导航方法
    app.navigate_to("/")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    ft.app(target=main, assets_dir=_ASSETS_DIR)

