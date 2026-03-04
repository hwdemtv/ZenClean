import flet as ft
from config.settings import COLOR_ZEN_PRIMARY

def FileListItem(node: dict, on_check_change, size_str: str) -> ft.Container:
    """构建单行的文件列表项，包含复选框、风险徽章、路径、大小和打开目录操作"""
    
    risk_color = ft.colors.GREEN_400
    if node["risk_level"] == "MEDIUM": risk_color = ft.colors.YELLOW_400
    elif node["risk_level"] == "HIGH": risk_color = ft.colors.RED_400
    
    def _open_location(e):
        import os
        target_dir = os.path.dirname(node["path"])
        if os.path.exists(target_dir):
            os.startfile(target_dir)

    return ft.Container(
        content=ft.Row([
            ft.Checkbox(value=node.get("is_checked", False), on_change=lambda e: on_check_change(e, node)),
            ft.Icon(ft.icons.CIRCLE, color=risk_color, size=10),
            ft.Text(node["path"][-70:] if len(node["path"]) > 75 else node["path"],
                    size=12, expand=True, font_family="Consolas"),
            ft.Text(size_str, size=12, color=ft.colors.GREY_500),
            ft.IconButton(
                icon=ft.icons.FOLDER_OPEN_ROUNDED,
                icon_size=16,
                icon_color=COLOR_ZEN_PRIMARY,
                tooltip="打开文件所在目录 (手动清理)",
                on_click=_open_location
            ),
        ], spacing=5),
        padding=ft.padding.only(left=10, right=5),
        tooltip=node.get("ai_advice", ""),
    )
