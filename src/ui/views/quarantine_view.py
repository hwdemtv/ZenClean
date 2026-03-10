import datetime
import flet as ft
from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_SURFACE, COLOR_ZEN_PRIMARY,
    COLOR_ZEN_DANGER, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM,
    COLOR_ZEN_DIVIDER
)
from core.quarantine import list_quarantined, restore, delete_item, clear_all, restore_all, _get_best_sandbox_dir
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
        
        self.btn_restore_all = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.RESTORE_PAGE_ROUNDED, color="white", size=18),
                ft.Text("一键全量恢复", color="white", weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=15),
            height=40,
            border_radius=8,
            bgcolor="#009688",
            border=ft.border.all(1, ft.colors.with_opacity(0.12, "onSurface")),
            ink=True,
            on_click=self._on_restore_all
        )

        self.btn_clear_all = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.DELETE_SWEEP, color="white", size=18),
                ft.Text("清空全部沙箱", color="white", weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=15),
            height=40,
            border_radius=8,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#E74C3C", "#C0392B"],
            ),
            border=ft.border.all(1, ft.colors.with_opacity(0.12, "onSurface")),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.colors.with_opacity(0.15, "#E74C3C")),
            ink=True,
            on_click=self._on_clear_all
        )
        
        header = ft.Row([
            ft.Column([self.title_text, self.subtitle_text], spacing=5),
            ft.Row([self.btn_restore_all, self.btn_clear_all], spacing=15)
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
                self.app.page.open(ft.SnackBar(ft.Text(f"已成功恢复: {name}"), bgcolor=ft.colors.GREEN_800))
                self._refresh_list()
            else:
                self.app.page.open(ft.SnackBar(ft.Text(f"恢复失败，目标路径可能被占用或文件已丢失"), bgcolor=ft.colors.RED_800))
                self.app.page.update()
                
        def _on_delete(e):
            def _confirm_delete(is_ok):
                if is_ok:
                    if delete_item(q_id):
                        self.app.page.open(ft.SnackBar(ft.Text(f"物理粉碎成功: {name}")))
                        self._refresh_list()
                    else:
                        self.app.page.open(ft.SnackBar(ft.Text("粉碎失败，请检查沙箱是否被其它程序占用"), bgcolor=ft.colors.RED_800))
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
        
    def _on_restore_all(self, e):
        items = list_quarantined()
        if not items:
            self.app.page.open(ft.SnackBar(ft.Text("当前隔离沙箱为空，无需恢复")))
            return
            
        def _confirm_restore(is_ok):
            if is_ok:
                original_content = self.btn_restore_all.content
                self.btn_restore_all.content = ft.Row([
                    ft.ProgressRing(width=16, height=16, color="white", stroke_width=2),
                    ft.Text("正在恢复...", color="white", weight=ft.FontWeight.BOLD)
                ], alignment=ft.MainAxisAlignment.CENTER)
                self.btn_restore_all.disabled = True
                self.btn_clear_all.disabled = True
                self.update()

                succ, fail = restore_all()
                
                self.btn_restore_all.content = original_content
                self.btn_restore_all.disabled = False
                self.btn_clear_all.disabled = False
                
                msg = f"全量恢复完成：成功 {succ}项"
                if fail > 0:
                    msg += f"，失败 {fail}项（路径被占用或无效）"
                self.app.page.open(ft.SnackBar(ft.Text(msg), bgcolor=ft.colors.GREEN_800))
                self._refresh_list()
                
        show_confirm_dialog(
            self.app.page,
            title="一键全量恢复",
            content=ft.Text(f"您确定要将沙箱内全部 {len(items)} 个项目原路还原到系统中吗？\n如果同名文件已存在，将被跳过。"),
            on_result=_confirm_restore,
            confirm_text="确认恢复"
        )
        
    def _on_clear_all(self, e):
        items = list_quarantined()
        if not items:
            self.app.page.open(ft.SnackBar(ft.Text("当前隔离沙箱为空，无需清理")))
            return
            
        def _confirm_clear(is_ok):
            if is_ok:
                original_content = self.btn_clear_all.content
                self.btn_clear_all.content = ft.Row([
                    ft.ProgressRing(width=16, height=16, color="white", stroke_width=2),
                    ft.Text("正在粉碎...", color="white", weight=ft.FontWeight.BOLD)
                ], alignment=ft.MainAxisAlignment.CENTER)
                self.btn_restore_all.disabled = True
                self.btn_clear_all.disabled = True
                self.update()

                freed = clear_all()
                
                self.btn_clear_all.content = original_content
                self.btn_restore_all.disabled = False
                self.btn_clear_all.disabled = False
                
                freed_mb = freed / (1024 * 1024)
                self.app.page.open(ft.SnackBar(ft.Text(f"已排空沙箱隔舱，共物理释放空间 {freed_mb:.2f} MB")))
                self._refresh_list()
                
        show_confirm_dialog(
            self.app.page,
            title="极度危险：全量物理粉碎",
            content=ft.Text(f"您确定要立即摧毁沙箱内的全部 {len(items)} 个项目吗？\n操作执行后，所有处于反悔期的文件将被视为抛弃，并在磁盘上进行不可逆的擦写。"),
            on_result=_confirm_clear,
            confirm_text="确认全量粉碎",
            is_danger=True
        )
