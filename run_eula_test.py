import os
import sys
import flet as ft

# 强制切换为 HTML 渲染器，配合自动化探针解析 DOM 树
os.environ["FLET_WEB_RENDERER"] = "html"

# 引入项目主逻辑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from src.main import main

if __name__ == '__main__':
    print("🚀 启动自动化测试专用 Web 节点 (端口: 8555)...")
    # 强制清除本地缓存，模拟首次启动
    def _test_wrapper(page: ft.Page):
        page.client_storage.remove("zen_eula_accepted")
        main(page)

    ft.app(target=_test_wrapper, view=ft.AppView.WEB_BROWSER, port=8555)
