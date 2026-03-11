import os
import flet as ft
from typing import Optional
from datetime import datetime

from config.settings import (
    AUTH_DAT_PATH,
    LICENSE_PRODUCT_ID,
    LICENSE_SERVER_URLS,
    NTP_MAX_DRIFT_SECONDS,
    COLOR_ZEN_BG, COLOR_ZEN_SURFACE,
    COLOR_ZEN_GOLD, COLOR_ZEN_DIVIDER, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM,
    COLOR_ZEN_PRIMARY
)
from ui.views.scan_view import ScanView
from ui.views.migration_view import MigrationView
from ui.views.auth_view import AuthView
from ui.views.result_view import ResultView
from ui.views.splash import SplashView
from ui.views.quarantine_view import QuarantineView
from ui.views.settings_view import SettingsView
from ui.views.app_migration_view import AppMigrationView
from ui.components.dialogs import show_eula_dialog

class ZenCleanApp(ft.Column):
    """
    根视图管理器。负责沉浸式顶栏、侧边导航栏、页面容器、路由切换。
    """

    def __init__(self, page: ft.Page, auto_scan_path: str = None):
        super().__init__(expand=True, spacing=0)
        self.page = page
        self.auto_scan_path = auto_scan_path
        self.is_activated = False
        self.lease_expiry_date: Optional[str] = None
        self.total_expiry_date: Optional[str] = None
        self._eula_accepted: Optional[bool] = None  # 本地缓存，避免 clientStorage 超时

        _assets_dir = page.client_storage.get("assets_dir") or ""
        _icon_img_path = os.path.join(_assets_dir, "icon.png") if _assets_dir else "icon.png"

        # ── 自定义沉浸式顶栏 ──────────────────────────────────────────────────
        _drag_content = ft.Container(
            content=ft.Stack([
                ft.Row([
                    ft.Container(width=5), # 左侧微调
                    ft.Image(src=_icon_img_path, width=18, height=18),
                    ft.Text("禅清 (ZenClean)", size=12, color=COLOR_ZEN_TEXT_DIM, weight=ft.FontWeight.W_500),
                ], spacing=10, alignment=ft.MainAxisAlignment.START),
                # 为确保大字标题处于下方 PageContainer 的绝对视觉中心，
                # 使用绝对展开并补全由于右侧窗体控制按钮和左侧 NavRail 引起的中轴线数学偏差。
                ft.Container(
                    content=ft.Text("互为螺旋 - C盘AI极速清理大师", size=13, color=COLOR_ZEN_GOLD, weight=ft.FontWeight.BOLD),
                    alignment=ft.alignment.center,
                    left=0, right=0, top=0, bottom=0,
                    padding=ft.padding.only(left=205),
                ),
            ], expand=True),
            padding=ft.padding.only(left=15, top=8, bottom=8, right=10),
        )

        self.btn_theme_toggle = ft.IconButton(
            icon=ft.icons.LIGHT_MODE if self.page.theme_mode == ft.ThemeMode.DARK else ft.icons.DARK_MODE,
            icon_size=16, 
            icon_color=COLOR_ZEN_TEXT_DIM, 
            tooltip="切换日/夜模式",
            on_click=self._toggle_theme_mode
        )

        _window_controls = ft.Row([
            self.btn_theme_toggle,
            ft.IconButton(ft.icons.MINIMIZE, icon_size=16, icon_color=COLOR_ZEN_TEXT_DIM, on_click=self._window_minimize),
            ft.IconButton(ft.icons.CROP_SQUARE, icon_size=16, icon_color=COLOR_ZEN_TEXT_DIM, on_click=self._window_maximize),
            ft.IconButton(ft.icons.CLOSE, icon_size=16, icon_color=COLOR_ZEN_TEXT_DIM, hover_color=ft.colors.RED_600, on_click=self._window_close),
        ], spacing=0)

        self._title_bar = ft.Container(
            content=ft.Row([
                ft.WindowDragArea(content=_drag_content, expand=True),
                _window_controls,
            ]),
            bgcolor=COLOR_ZEN_SURFACE, # 挂入卡片层色值
            height=45,
            visible=False 
        )

        # 分割线
        self._divider = ft.VerticalDivider(width=1, color=COLOR_ZEN_DIVIDER, visible=False)

        # 侧边导航栏
        self._nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=200,
            bgcolor=COLOR_ZEN_SURFACE,
            indicator_color=ft.colors.TRANSPARENT, # 去除整块背景高亮
            unselected_label_text_style=ft.TextStyle(color=COLOR_ZEN_TEXT_DIM, size=12),
            selected_label_text_style=ft.TextStyle(color=COLOR_ZEN_TEXT_MAIN, size=12, weight=ft.FontWeight.BOLD), # 选中文本泛白
            group_alignment=-0.9, # 让图标整体靠上方一点
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.CLEANING_SERVICES_OUTLINED,
                    selected_icon=ft.icons.CLEANING_SERVICES,
                    label="禅清看板",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.DATA_SAVER_OFF_OUTLINED,
                    selected_icon=ft.icons.DATA_SAVER_ON,
                    label="系统搬家",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.LOCAL_POLICE_OUTLINED,
                    selected_icon=ft.icons.LOCAL_POLICE,
                    label="VIP 激活",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.HOURGLASS_EMPTY,
                    selected_icon=ft.icons.HOURGLASS_FULL,
                    label="时光机",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED,
                    selected_icon=ft.icons.SETTINGS,
                    label="系统设置",
                ),
            ],
            on_change=self._on_nav_change,
            visible=False,
        )

        # 页面内容容器
        self._page_container = ft.Container(
            expand=True,
            padding=ft.padding.all(20),
            bgcolor=COLOR_ZEN_BG,
        )

        # 通知区域挂载点
        self._notification_column = ft.Column(spacing=10, animate_size=300)
        
        # 将通知条与内容容器垂直组合
        self._main_content_area = ft.Column(
            [
                self._notification_column,
                self._page_container
            ],
            expand=True,
            spacing=0
        )

        # 根布局：加入顶栏，下方左右分割
        self.controls = [
            self._title_bar,
            ft.Row(
                controls=[
                    self._nav_rail,
                    self._divider,
                    self._main_content_area,
                ],
                expand=True,
                spacing=0,
            )
        ]

        self._route_factories = {
            "/":          lambda: SplashView(self),
            "/scan":      lambda: ScanView(self),
            "/result":    lambda: ResultView(self),
            "/migration": lambda: MigrationView(self),
            "/app_migration": lambda: AppMigrationView(self),
            "/auth":      lambda: AuthView(self),
            "/quarantine":lambda: QuarantineView(self),
            "/settings":  lambda: ft.Container(content=SettingsView(self), expand=True, padding=ft.padding.only(bottom=20)),
        }
        # 缓存已构建的视图（除 /scan、/result 需每次重建以刷新激活状态）
        self._view_cache: dict[str, ft.Control] = {}
        
        # 共享数据层
        self.scan_nodes: list[dict] = []
        
        # 启动时进行一次延时的静默版本检查广播接收
        self._start_silent_update_check()
        
    def _start_silent_update_check(self):
        import time
        import threading
        from core.updater import check_for_updates

        def _silent_callback(has_new, latest_version, url, msg):
            if has_new:
                # 接收到含更新的高能通知，展示顶部卡片式通知条 (方案 B)
                def _ui_update():
                    # 提取第一行作为摘要，防止文字墙
                    summary = msg.split('\n')[0][:60]
                    if len(msg.split('\n')) > 1 or len(msg) > 60:
                        summary += "..."
                        
                    self.show_notification(
                        title=f"发现新版本 v{latest_version}",
                        content=summary,
                        icon=ft.icons.SYSTEM_UPDATE,
                        actions=[
                            ("立即更新", lambda: self.page.launch_url(url) if url else None, True),
                            ("查看日志", lambda: self._show_markdown_dialog(f"ZenClean v{latest_version} 更新日志", msg), False)
                        ]
                    )
                
                if self.page:
                    _ui_update()
                
        def _delayed_check():
            time.sleep(8)  # 避开启动首屏资源高峰
            check_for_updates(_silent_callback, manual=False)
            
        threading.Thread(target=_delayed_check, daemon=True).start()
        
        # 启动时进行离线免联鉴权（启动阶段跳过网络对时，极致加速）
        from core.auth import check_local_auth_status
        is_val, payload = check_local_auth_status(is_startup=True)
        if is_val and payload:
            exp_ts = payload.get("exp")
            self.is_activated = True
            self.lease_expiry_date = datetime.fromtimestamp(exp_ts).strftime("%Y-%m-%d %H:%M")
            backend_exp = payload.get("_backend_expires_at")
            if backend_exp:
                try:
                    dt = datetime.fromisoformat(backend_exp.replace("Z", "+00:00"))
                    self.total_expiry_date = dt.astimezone().strftime("%Y-%m-%d %H:%M")
                except Exception:
                    self.total_expiry_date = backend_exp[:16].replace("T", " ")
            else:
                self.total_expiry_date = self.lease_expiry_date

            # ---- 新增：如果缓存了 license_key，发起异步的后台权限效验以同步后端解绑状态 ----
            license_key = payload.get("_local_license_key")
            if license_key:
                import threading
                def _bg_verify():
                    import time
                    from core.auth import verify_license_online
                    from core.logger import logger
                    from config.settings import AUTH_DAT_PATH

                    # 初始稍微延后，避免阻塞启动流程
                    time.sleep(2)

                    while True:
                        if not self.is_activated:
                            break

                        # 支持通知对象解包
                        success, msg, note = verify_license_online(license_key, is_auto_check=True)
                        logger.info(f"[BG_VERIFY] result: success={success}, msg={msg}")
                        
                        # 如果有来自云端的广播通知，立即处理
                        if note:
                            self.process_server_notification(note)

                        if not success and ("[REVOKED]" in msg or ("网络" not in msg and "服务端异常" not in msg)):
                            async def update_ui_safe():
                                logger.warning(f"[BG_VERIFY] license revoked! Executing downgrade.")
                                if AUTH_DAT_PATH.exists():
                                    try: AUTH_DAT_PATH.unlink()
                                    except: pass
                                self.set_activated(False)
                                alert_msg = msg.replace("[REVOKED]", "").strip() if "[REVOKED]" in msg else "您的授权已失效，当前已恢复为免费版。"
                                self.page.snack_bar = ft.SnackBar(ft.Text(alert_msg), bgcolor=ft.colors.RED_800)
                                self.page.snack_bar.open = True
                                self.page.update()

                            self.page.run_task(update_ui_safe)
                            break
                            
                        # 每半小时巡检一次
                        time.sleep(1800)

                threading.Thread(target=_bg_verify, daemon=True).start()

    def process_server_notification(self, note: dict):
        """
        处理来自后端的广播通知载荷，实现去重展示与强/弱提醒分离。
        """
        if not note or not self.page: return
        note_id = note.get("id")
        content = note.get("content", "")
        # 生成唯一标识：ID + 内容摘要，支持“同 ID 内容更新”重新提醒
        notice_fingerprint = f"{note_id}_{hash(content)}"
        
        last_fingerprint = self.page.client_storage.get("last_notice_fingerprint")
        
        from core.logger import logger
        logger.info(f"[Notification] Check: {notice_fingerprint}, Last: {last_fingerprint}")
        
        if last_fingerprint == notice_fingerprint:
            return

        is_force = note.get("is_force", False)
        title = note.get("title", "系统消息")
        url = note.get("action_url")
        
        async def _ui_action():
            if is_force:
                def _close(e):
                    dlg.open = False
                    self.page.update()
                actions = [ft.TextButton("我知道了", on_click=_close)]
                if url:
                    actions.insert(0, ft.ElevatedButton("查看详情", on_click=lambda _: self.page.launch_url(url)))
                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([ft.Icon(ft.icons.CAMPAIGN, color=COLOR_ZEN_PRIMARY), ft.Text(title)]),
                    content=ft.Container(
                        content=ft.Markdown(content, selectable=True),
                        width=500, height=400,
                    ),
                    actions=actions,
                )
                self.page.overlay.append(dlg)
                dlg.open = True
            else:
                # 非强制通知也改为卡片式展示
                summary = content.split('\n')[0][:50] + "..." if len(content) > 50 else content
                actions = []
                if url:
                    actions.append(("去看看", lambda: self.page.launch_url(url), True))
                
                self.show_notification(
                    title=title,
                    content=summary,
                    icon=ft.icons.NOTIFICATIONS,
                    actions=actions
                )
            
            self.page.update()
            # 记录指纹，用于去重
            self.page.client_storage.set("last_notice_fingerprint", notice_fingerprint)

        self.page.run_task(_ui_action)

    def show_notification(self, title: str, content: str, icon: str = ft.icons.INFO, actions: list = None):
        """
        在顶部通知区域挂载一个简洁的交互卡片 (方案 B 实现)
        :param actions: list of (label, on_click_func, is_primary)
        """
        if not self.page: return

        # 闭包：关闭通知
        def _close_notice(e):
            self._notification_column.controls.remove(notification_card)
            self._notification_column.update()

        action_buttons = []
        if actions:
            for label, func, is_prim in actions:
                if is_prim:
                    action_buttons.append(
                        ft.ElevatedButton(
                            label, 
                            on_click=lambda _, f=func: f(), 
                            bgcolor=COLOR_ZEN_PRIMARY, 
                            color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
                        )
                    )
                else:
                    action_buttons.append(
                        ft.TextButton(label, on_click=lambda _, f=func: f(), style=ft.ButtonStyle(color=COLOR_ZEN_PRIMARY))
                    )

        notification_card = ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=COLOR_ZEN_PRIMARY, size=24),
                ft.Column([
                    ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Text(content, size=12, color=COLOR_ZEN_TEXT_DIM, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=2, expand=True),
                ft.Row(action_buttons, spacing=10),
                ft.IconButton(ft.icons.CLOSE, icon_size=16, icon_color=COLOR_ZEN_TEXT_DIM, on_click=_close_notice)
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=ft.colors.with_opacity(0.1, COLOR_ZEN_PRIMARY),
            border=ft.border.all(1, ft.colors.with_opacity(0.2, COLOR_ZEN_PRIMARY)),
            border_radius=10,
            margin=ft.margin.only(bottom=10)
        )

        self._notification_column.controls.insert(0, notification_card)
        self._notification_column.update()

    def _show_markdown_dialog(self, title: str, markdown_content: str):
        """展示 Markdown 渲染的详情对话框 (解决文字墙)"""
        def _close(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.icons.ARTICLE, color=COLOR_ZEN_PRIMARY), ft.Text(title)]),
            content=ft.Container(
                content=ft.Markdown(
                    markdown_content,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
                width=600,
                height=500,
            ),
            actions=[ft.TextButton("关闭", on_click=_close)],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()


    def set_activated(self, is_activated: bool, lease_expiry: Optional[str] = None, total_expiry: Optional[str] = None):
        """全局设置激活状态及到期时间并刷新 UI"""
        self.is_activated = is_activated
        self.lease_expiry_date = lease_expiry
        self.total_expiry_date = total_expiry
        # 刷新导航栏图标显示
        self._nav_rail.destinations[2].selected_icon = ft.icons.VERIFIED_USER if is_activated else ft.icons.LOCAL_POLICE
        self._nav_rail.destinations[2].icon = ft.icons.VERIFIED_USER if is_activated else ft.icons.LOCAL_POLICE_OUTLINED
        self.page.update()
        
        # 强制刷新当前可能受到影响的视图
        current_idx = self._nav_rail.selected_index
        if current_idx == 2:
            self.navigate_to("/auth")
        elif current_idx == 0:
            self.navigate_to("/scan")

    def _on_nav_change(self, e):
        idx_to_route = {0: "/scan", 1: "/migration", 2: "/auth", 3: "/quarantine", 4: "/settings"}
        self.navigate_to(idx_to_route.get(e.control.selected_index, "/scan"))

    def navigate_to(self, route: str) -> None:
        """切换到指定路由，重建需要反映最新状态的视图。"""
        if route not in self._route_factories:
            return

        # ── EULA 首次启动拦截 ─────────────────────────────────────────
        # 优先读取本地缓存，避免高频交互下 clientStorage.get 超时
        if self._eula_accepted is None:
            try:
                self._eula_accepted = self.page.client_storage.get("zen_eula_accepted") or False
            except Exception:
                self._eula_accepted = False  # 出现通讯超时时，保守处理为 False

        if route == "/scan" and not self._eula_accepted:
            # 弹出 EULA 弹窗
            def _on_eula_accepted():
                self._eula_accepted = True
                self.navigate_to("/scan")
                
            show_eula_dialog(self.page, on_accepted=_on_eula_accepted)
            # 先显示导航栏等 UI 框架
            self._nav_rail.visible = True
            self._divider.visible = True
            self._title_bar.visible = True
            self.update()
            return

        # 需要强制每次重建的视图（刷新动态数据或激活状态）
        if route in ["/scan", "/result", "/auth", "/quarantine", "/app_migration"] or route not in self._view_cache:
            self._view_cache[route] = self._route_factories[route]()

        # 闪屏结束后显示导航栏与分割线
        if route != "/":
            self._nav_rail.visible = True
            self._divider.visible = True
            self._title_bar.visible = True

        self._page_container.content = self._view_cache[route]
        self.update()

        # 闪屏视图需要在挂载后主动触发倒计时
        view = self._view_cache[route]
        if hasattr(view, "start"):
            view.start()

    def trigger_auto_scan(self, path: str):
        """主实例通过 IPC 接收到扫描请求时的分发接口"""
        import os
        if not path or not os.path.exists(path):
            return
        self.auto_scan_path = path
        # 强制重建 ScanView 以触发 did_mount 中的自动扫描消费
        if "/scan" in self._view_cache:
            del self._view_cache["/scan"]
        self.navigate_to("/scan")
        # 尝试将窗口显示并前置
        try:
            self.page.window.visible = True
            self.page.window.minimized = False
            self.page.window.to_front()
        except Exception:
            pass
        self.page.update()


    def _window_minimize(self, e):
        self.page.window.minimized = True
        self.page.update()

    def _window_maximize(self, e):
        self.page.window.maximized = not getattr(self.page.window, "maximized", False)
        self.page.update()

    def _window_close(self, e):
        self.page.window.visible = False
        self.page.update()

    def _toggle_theme_mode(self, e):
        new_mode = ft.ThemeMode.LIGHT if self.page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        self.page.theme_mode = new_mode
        self.page.client_storage.set("zen_theme_mode", "dark" if new_mode == ft.ThemeMode.DARK else "light")
        self.btn_theme_toggle.icon = ft.icons.LIGHT_MODE if new_mode == ft.ThemeMode.DARK else ft.icons.DARK_MODE
        self.page.update()
