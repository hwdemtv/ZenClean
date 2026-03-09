import flet as ft
from config.settings import COLOR_ZEN_BG, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM, COLOR_ZEN_PRIMARY, LOG_DIR
import os

class SettingsView(ft.Column):
    """
    极客控制台 (纯净版系统设置页)。
    砍掉了容易引起用户选择困难症的冗余外观项，专注系统底层控制与合规说明。
    """
    def __init__(self, app):
        super().__init__(expand=True)
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
            padding=ft.padding.only(bottom=20)
        )

        # ── 2. 底层日志控制区 (Log Control) ──
        
        self.log_level_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("INFO", "标准 INFO (推荐)"),
                ft.dropdown.Option("DEBUG", "高压 DEBUG (极客排障)"),
                ft.dropdown.Option("WARNING", "仅记录警告 (省空间)"),
            ],
            value="INFO", # 待后续接入实际配置读取
            width=250,
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

        # ── 3. 合规与关于区 (About & Legal) ──
        _legal_tile = self._build_card_section(
            ft.icons.GAVEL, "合规与免责声明", "查看 ZenClean 的完整用户协议及数据隐私说明。",
            ft.TextButton(
                 "查阅《软件许可与服务协议 (EULA)》", 
                 icon=ft.icons.MENU_BOOK,
                 style=ft.ButtonStyle(color=COLOR_ZEN_PRIMARY),
                 on_click=self._show_eula
            )
        )
        
        _about_tile = ft.Container(
            content=ft.Column([
                ft.Divider(height=40, color=ft.colors.with_opacity(0.1, "onSurface")),
                ft.Text("ZenClean 禅清 - 互为螺旋极速体验版 (v1.0.0-rc)", size=12, color=COLOR_ZEN_TEXT_DIM),
                ft.Text("Copyright © 2026 HW-DEM Team. All rights reserved.", size=11, color=ft.colors.with_opacity(0.4, "onSurface")),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            padding=ft.padding.only(top=20)
        )

        self.controls = [
            _header,
            _log_tile,
            ft.Container(height=10),
            _legal_tile,
            ft.Container(expand=True),
            _about_tile
        ]

    def _build_card_section(self, icon: str, title: str, subtitle: str, action_control: ft.Control):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=COLOR_ZEN_PRIMARY, size=22),
                    ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=COLOR_ZEN_TEXT_MAIN),
                ], spacing=8),
                ft.Text(subtitle, size=12, color=COLOR_ZEN_TEXT_DIM),
                ft.Container(height=8),
                action_control
            ]),
            bgcolor=ft.colors.with_opacity(0.03, "onSurface"),
            padding=20,
            border_radius=12,
            border=ft.border.all(1, ft.colors.with_opacity(0.08, "onSurface"))
        )
        
    def _on_log_level_change(self, e):
        # 此处后续可补充写入 config.json 逻辑
        level = self.log_level_dropdown.value
        self.app.page.snack_bar = ft.SnackBar(ft.Text(f"日志级别已临时切换至: {level}"), duration=2000)
        self.app.page.snack_bar.open = True
        self.app.page.update()

    def _show_eula(self, e):
        from ui.components.dialogs import show_eula_dialog
        show_eula_dialog(self.app.page, is_forced=False)
