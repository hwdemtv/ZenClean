import os
import sys
import flet as ft

# 【关键】强制切换为 HTML 渲染器，配合自动化探针解析 DOM 树
os.environ["FLET_WEB_RENDERER"] = "html"

# 引入项目主逻辑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from src.main import main

def find_free_port(start_port=8550, max_port=8560):
    import socket
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            pass
    return start_port

if __name__ == '__main__':
    port = find_free_port()
    print(f"🚀 启动自动化测试专用 Web 节点 (端口: {port})...")
    # 为了避免闪屏图找不到，挂载 assets 目录
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, assets_dir=assets_dir)
