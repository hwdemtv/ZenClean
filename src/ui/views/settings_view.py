import flet as ft
from config.settings import COLOR_ZEN_BG, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM, COLOR_ZEN_PRIMARY, LOG_DIR
from config.version import __version__ as APP_VERSION
import os

class SettingsView(ft.Column):
    """
    极客控制台 (纯净版系统设置页)。
    砍掉了容易引起用户选择困难症的冗余外观项，专注系统底层控制与合规说明。
    """
    def __init__(self, app):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.app = app

        # ── 1. 顶部标题区 ──
        _header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.TUNE, size=28, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Text("系统控制台", size=24, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ft.Text("极客专属配置与应用底层维护选项", size=13, color=COLOR_ZEN_TEXT_DIM),
            ], spacing=2),
            padding=ft.padding.only(bottom=10)
        )

        # ── 2. 底层日志控制区 (Log Control) ──
        
        self.log_level_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("INFO", "标准 INFO (推荐)"),
                ft.dropdown.Option("DEBUG", "高压 DEBUG (极客排障)"),
                ft.dropdown.Option("WARNING", "仅记录警告 (省空间)"),
            ],
            value="INFO",
            expand=True,
            border_radius=8,
            text_size=13,
            dense=True,
            on_change=self._on_log_level_change
        )
        
        _log_tile = self._build_card_section(
            ft.icons.TROUBLESHOOT, "异常排障与运行日志", "调整记录颗粒度，或导出日志包以供工程师分析崩溃原因。",
            ft.Row([
                 self.log_level_dropdown,
                 ft.ElevatedButton(
                     "打开日志目录", 
                     icon=ft.icons.FOLDER_OPEN,
                     style=ft.ButtonStyle(color="white", bgcolor=COLOR_ZEN_PRIMARY),
                     on_click=lambda _: os.startfile(str(LOG_DIR)) if LOG_DIR.exists() else None
                 )
            ], spacing=15)
        )

        # ── 3. 系统集成区 (System Integration) ──
        
        # 右键菜单开关
        from core.context_menu import is_registered as _ctx_is_reg
        self._ctx_switch = ft.Switch(
            value=_ctx_is_reg(),
            active_color=COLOR_ZEN_PRIMARY,
            on_change=self._on_ctx_menu_toggle
        )
        self._ctx_status = ft.Text(
            "已启用" if _ctx_is_reg() else "未启用",
            size=12, color=COLOR_ZEN_TEXT_DIM
        )
        
        # 磁盘预警开关 + 阈值滑块
        from core.disk_watcher import is_task_registered as _dw_is_reg, get_threshold
        self._dw_switch = ft.Switch(
            value=_dw_is_reg(),
            active_color=COLOR_ZEN_PRIMARY,
            on_change=self._on_disk_watch_toggle
        )
        self._dw_status = ft.Text(
            "已启用" if _dw_is_reg() else "未启用",
            size=12, color=COLOR_ZEN_TEXT_DIM
        )
        
        _current_threshold = get_threshold()
        self._threshold_slider = ft.Slider(
            min=50, max=99, value=_current_threshold,
            divisions=49, label="{value}%",
            active_color=COLOR_ZEN_PRIMARY,
            width=200,
            on_change_end=self._on_threshold_change
        )
        self._threshold_label = ft.Text(
            f"预警阈值: {_current_threshold}%",
            size=12, color=COLOR_ZEN_TEXT_DIM
        )
        _ctx_tile = self._build_card_section(
            ft.icons.MOUSE, "Windows 右键菜单集成",
            "右键文件夹即可快速分析，写入当前用户注册表 (HKCU)，无需管理员权限。",
            ft.Row([self._ctx_switch, self._ctx_status], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )
        
        _dw_tile = self._build_card_section(
            ft.icons.DISC_FULL, "系统盘爆仓气泡预警",
            "任务计划程序定时静默复查 C 盘，超限即弹系统通知，零后台常驻。",
            ft.Column([
                ft.Row([self._dw_switch, self._dw_status], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([self._threshold_label, self._threshold_slider], spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8)
        )

        # ✨ 新增：系统级开机自启守护
        from core.autorun import is_registered as _ar_is_reg
        self._ar_switch = ft.Switch(
            value=_ar_is_reg(),
            active_color=COLOR_ZEN_PRIMARY,
            on_change=self._on_autorun_toggle
        )
        self._ar_status = ft.Text(
            "已开启" if _ar_is_reg() else "未开启",
            size=12, color=COLOR_ZEN_TEXT_DIM
        )
        _ar_tile = self._build_card_section(
            ft.icons.ROCKET_LAUNCH, "系统级开机自启守护",
            "随 Windows 启动并隐身驻留于系统托盘，实现全天候无感保护。",
            ft.Row([self._ar_switch, self._ar_status], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        # ── 4. 合规与关于 (底部通栏 - 居中 Footer 化) ──
        _legal_tile = ft.Container(
            content=ft.Column([
                ft.Row([
                     ft.TextButton(
                         "《软件许可与服务协议》", 
                         icon=ft.icons.MENU_BOOK,
                         style=ft.ButtonStyle(color=COLOR_ZEN_PRIMARY),
                         on_click=self._show_eula
                     ),
                     ft.Text("|", color=ft.colors.with_opacity(0.1, "onSurface")),
                     ft.TextButton(
                         "关于 ZenClean", 
                         icon=ft.icons.INFO_OUTLINE,
                         style=ft.ButtonStyle(color=COLOR_ZEN_PRIMARY),
                         on_click=lambda _: None # 占位
                     ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=0),
                ft.Text(f"ZenClean 禅清 - 互为螺旋极速体验版 (v{APP_VERSION})", size=12, color=COLOR_ZEN_TEXT_DIM),
                ft.Text("Copyright © 2026 HW-DEM Team. All rights reserved.", size=11, color=ft.colors.with_opacity(0.4, "onSurface")),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            padding=ft.padding.only(top=20, bottom=30),
        )

        # ── 3. 布局重构：2x2 网格 ──
        _log_tile.col = {"md": 6, "lg": 6}
        _ctx_tile.col = {"md": 6, "lg": 6}
        _dw_tile.col = {"md": 6, "lg": 6}
        _ar_tile.col = {"md": 6, "lg": 6}

        _grid = ft.ResponsiveRow([
            _log_tile,
            _ctx_tile,
            _dw_tile,
            _ar_tile
        ], spacing=15, run_spacing=15)

        self.controls = [
            _header,
            _grid,
            ft.Container(height=35), # 大幅增加间距，带来呼吸感
            _legal_tile
        ]

    def _build_card_section(self, icon: str, title: str, subtitle: str, action_control: ft.Control):
        return ft.Container(
            height=175,  # 适度舒缓高度，恢复内部呼吸感，同时解决滑块显示截断问题
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=COLOR_ZEN_PRIMARY, size=22),
                    ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=COLOR_ZEN_TEXT_MAIN),
                ], spacing=6),
                ft.Text(subtitle, size=11, color=COLOR_ZEN_TEXT_DIM),
                ft.Container(height=6), # 增加标题与控件之间的间隙
                action_control
            ], expand=True),
            bgcolor=ft.colors.with_opacity(0.03, "onSurface"),
            padding=15,
            border_radius=12,
            border=ft.border.all(1, ft.colors.with_opacity(0.08, "onSurface"))
        )
        
    def _on_log_level_change(self, e):
        level = self.log_level_dropdown.value
        self.app.page.snack_bar = ft.SnackBar(ft.Text(f"日志级别已临时切换至: {level}"), duration=2000)
        self.app.page.snack_bar.open = True
        self.app.page.update()

    def _show_eula(self, e):
        from ui.components.dialogs import show_eula_dialog
        show_eula_dialog(self.app.page, on_accepted=lambda: None)

    # ── 系统集成事件处理 ────────────────────────────────────────────────────

    def _on_ctx_menu_toggle(self, e):
        """右键菜单开关切换"""
        from core.context_menu import register, unregister
        if e.control.value:
            ok, msg = register()
        else:
            ok, msg = unregister()
        
        self._ctx_status.value = "已启用" if e.control.value and ok else ("注册失败" if not ok else "未启用")
        if not ok:
            e.control.value = not e.control.value  # 回滚开关
        
        self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), duration=2500)
        self.app.page.snack_bar.open = True
        self.update()
        self.app.page.update()

    def _on_disk_watch_toggle(self, e):
        """磁盘预警开关切换"""
        from core.disk_watcher import register_task, unregister_task
        if e.control.value:
            ok, msg = register_task()
        else:
            ok, msg = unregister_task()
        
        self._dw_status.value = "已启用" if e.control.value and ok else ("注册失败" if not ok else "未启用")
        if not ok:
            e.control.value = not e.control.value  # 回滚开关
        
        self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), duration=2500)
        self.app.page.snack_bar.open = True
        self.update()
        self.app.page.update()

    def _on_autorun_toggle(self, e):
        """开机启动开关切换"""
        from core.autorun import register, unregister
        if e.control.value:
            ok, msg = register()
        else:
            ok, msg = unregister()
            
        self._ar_status.value = "已开启" if e.control.value and ok else ("设置失败" if not ok else "未开启")
        if not ok:
            e.control.value = not e.control.value
            
        self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), duration=2500)
        self.app.page.snack_bar.open = True
        self.update()
        self.app.page.update()

    def _on_threshold_change(self, e):
        """磁盘预警阈值调整"""
        from core.disk_watcher import set_threshold
        val = int(e.control.value)
        set_threshold(val)
        self._threshold_label.value = f"预警阈值: {val}%"
        
        self.app.page.snack_bar = ft.SnackBar(ft.Text(f"预警阈值已调整为 {val}%"), duration=1500)
        self.app.page.snack_bar.open = True
        self.update()
        self.app.page.update()

