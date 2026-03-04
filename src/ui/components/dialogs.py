import flet as ft
from config.settings import COLOR_ZEN_DANGER, COLOR_ZEN_TEXT_DIM

def show_confirm_clean_dialog(page: ft.Page, size_str: str, node_count: int, on_confirm, on_cancel=None):
    """最终清理的确认对话框"""
    def _close(_):
        dlg.open = False
        page.update()
        if on_cancel:
            on_cancel()

    def _confirm(_):
        dlg.open = False
        page.update()
        on_confirm()

    dlg = ft.AlertDialog(
        title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=COLOR_ZEN_DANGER), ft.Text("确认开始物理清理？")]),
        content=ft.Text(f"系统即将正式处理 {node_count} 个勾选项，共计约 {size_str}。\n\n提示：低风险项将被直接删除，中/高风险项将移入回收站。"),
        actions=[
            ft.TextButton("我再想想", on_click=_close, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
            ft.ElevatedButton("开始清理", bgcolor=COLOR_ZEN_DANGER, color="white", on_click=_confirm),
        ]
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def show_empty_recycle_bin_dialog(page: ft.Page, on_confirm, on_cancel):
    """清空回收站提示对话框"""
    def _close(_):
        dlg.open = False
        page.update()
        on_cancel()

    def _confirm(_):
        dlg.open = False
        page.update()
        on_confirm()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=COLOR_ZEN_DANGER), ft.Text("高能预警：清空回收站")]),
        content=ft.Text("部分争议文件（MEDIUM/HIGH级别）已移入系统回收站作为您的最后防线。\n\n是否立即【彻底清空系统回收站】斩草除根？\n警告：此操作不可逆转！"),
        actions=[
            ft.TextButton("先保留在回收站", on_click=_close, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
            ft.ElevatedButton("彻底清空 (免责)", bgcolor=COLOR_ZEN_DANGER, color="white", on_click=_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
