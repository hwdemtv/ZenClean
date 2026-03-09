import datetime
import flet as ft
from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_SURFACE, COLOR_ZEN_PRIMARY,
    COLOR_ZEN_DANGER, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM,
    COLOR_ZEN_DIVIDER
)
from core.quarantine import list_quarantined, restore, delete_item, auto_clean_expired, _get_best_sandbox_dir
from ui.components.dialogs import show_confirm_dialog


class QuarantineView(ft.Column):
    """
    时光机恢复舱界面
    展示被隔离的文件列表，提供无损回滚与彻底粉碎功能。
    """
    def __init__(self, app):
        super().__init__(expand=True, spacing=20)
        self.app = app
        
        # 页面标题与顶部状态栏
        self.title_text = ft.Text("时光机恢复舱", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN)
        self.subtitle_text = ft.Text("沙箱隔离可为您保留 72 小时的反悔期。过期项目将被系统静默物理粉碎。", size=13, color=COLOR_ZEN_TEXT_DIM)
        
        self.btn_auto_clean = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.CLEANING_SERVICES, color="white", size=18),
                ft.Text("立即清理过期项目", color="white", weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=15),
            height=40,
            border_radius=8,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#00B894", "#00C2FF"],
            ),
            border=ft.border.all(1, ft.colors.with_opacity(0.12, "onSurface")),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.colors.with_opacity(0.15, "#00B894")),
            ink=True,
            on_click=self._on_auto_clean
        )
        
        header = ft.Row([
            ft.Column([self.title_text, self.subtitle_text], spacing=5),
            self.btn_auto_clean
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        sandbox_path = str(_get_best_sandbox_dir())
        warning_box = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.SHIELD, color=COLOR_ZEN_PRIMARY, size=20),
                ft.Text(f"当前沙箱据点: {sandbox_path}", size=13, weight=ft.FontWeight.W_500, color=COLOR_ZEN_TEXT_MAIN),
                ft.VerticalDivider(width=1, color=COLOR_ZEN_DIVIDER),
                ft.Text("⚠️ 警告：沙箱位于隐藏系统目录，请勿使用其他第三方清理工具扫描或强删此目录，否则将导致恢复数据永久损坏！", 
                        size=12, color=COLOR_ZEN_DANGER, expand=True)
            ], spacing=10, alignment=ft.MainAxisAlignment.START),
            padding=10,
            bgcolor=ft.colors.with_opacity(0.08, "error"),
            border_radius=6,
            border=ft.border.all(1, "outline")
        )
        
        # 列表容器
        self.list_view = ft.ListView(expand=True, spacing=10)
        
        self.controls = [header, warning_box, ft.Divider(color=COLOR_ZEN_DIVIDER), self.list_view]
        
    def did_mount(self):
        self._refresh_list()
        
    def _refresh_list(self):
        items = list_quarantined()
        self.list_view.controls.clear()
        
        if not items:
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.HOURGLASS_EMPTY, size=64, color=COLOR_ZEN_TEXT_DIM),
                        ft.Text("隔离沙箱空空如也", size=16, color=COLOR_ZEN_TEXT_DIM)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=100
                )
            )
        else:
            for item in items:
                self.list_view.controls.append(self._build_item_card(item))
                
        self.update()
        
    def _build_item_card(self, item: dict) -> ft.Control:
        q_id = item["id"]
        name = item.get("name", "Unknown")
        orig_path = item.get("original_path", "")
        size_bytes = item.get("size_bytes", 0)
        q_time_str = item.get("quarantined_at", "")
        
        try:
            dt = datetime.datetime.fromisoformat(q_time_str)
            time_display = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_display = q_time_str
            
        size_mb = size_bytes / (1024 * 1024)
        
        # UI 组件
        icon = ft.Icon(ft.icons.FOLDER if item.get("is_dir") else ft.icons.INSERT_DRIVE_FILE, color=COLOR_ZEN_PRIMARY)
        
        info_col = ft.Column([
            ft.Text(name, size=15, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(f"原路径: {orig_path}", size=12, color=COLOR_ZEN_TEXT_DIM, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(f"隔离时间: {time_display}  |  大小: {size_mb:.2f} MB", size=12, color=COLOR_ZEN_TEXT_DIM)
        ], spacing=2, expand=True)
        
        def _on_restore(e):
            if restore(q_id):
                self.app.page.snack_bar = ft.SnackBar(ft.Text(f"已成功恢复: {name}"), bgcolor=ft.colors.GREEN_800)
                self.app.page.snack_bar.open = True
                self._refresh_list()
            else:
                self.app.page.snack_bar = ft.SnackBar(ft.Text(f"恢复失败，目标路径可能被占用或文件已丢失"), bgcolor=ft.colors.RED_800)
                self.app.page.snack_bar.open = True
                self.app.page.update()
                
        def _on_delete(e):
            def _confirm_delete(is_ok):
                if is_ok:
                    if delete_item(q_id):
                        self.app.page.snack_bar = ft.SnackBar(ft.Text(f"物理粉碎成功: {name}"))
                        self.app.page.snack_bar.open = True
                        self._refresh_list()
                    else:
                        self.app.page.snack_bar = ft.SnackBar(ft.Text("粉碎失败，请检查沙箱是否被其它程序占用"), bgcolor=ft.colors.RED_800)
                        self.app.page.snack_bar.open = True
                        self.app.page.update()
            
            show_confirm_dialog(
                self.app.page,
                title="警告：不可逆操作",
                content=ft.Text(f"您确定要彻底从磁盘擦除【{name}】吗？此操作无法通过任何软件恢复。"),
                on_result=_confirm_delete,
                confirm_text="物理粉碎",
                is_danger=True
            )
            
        actions_row = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.RESTORE, color="white", size=16),
                    ft.Text("原路恢复", color="white", size=13, weight=ft.FontWeight.W_600)
                ], alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                border_radius=6,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#00B894", "#00C2FF"],
                ),
                border=ft.border.all(1, ft.colors.with_opacity(0.1, "onSurface")),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.colors.with_opacity(0.1, "#00B894")),
                ink=True,
                on_click=_on_restore
            ),
            ft.IconButton(ft.icons.DELETE_FOREVER, icon_color=COLOR_ZEN_DANGER, tooltip="物理粉碎", on_click=_on_delete)
        ])
        
        return ft.Container(
            content=ft.Row([icon, info_col, actions_row], spacing=15, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=15,
            border_radius=8,
            bgcolor=COLOR_ZEN_SURFACE,
            border=ft.border.all(1, color=COLOR_ZEN_DIVIDER)
        )
        
    def _on_auto_clean(self, e):
        # 静默清理默认过期项目
        freed = auto_clean_expired()
        if freed > 0:
            freed_mb = freed / (1024 * 1024)
            self.app.page.snack_bar = ft.SnackBar(ft.Text(f"已成功清理过期隔离项目，释放 {freed_mb:.2f} MB"))
        else:
            self.app.page.snack_bar = ft.SnackBar(ft.Text("当前没有已过期的沙箱项目"))
        self.app.page.snack_bar.open = True
        self._refresh_list()
