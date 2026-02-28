import flet as ft
from typing import Optional
from datetime import datetime

from ui.views.scan_view import ScanView
from ui.views.migration_view import MigrationView
from ui.views.auth_view import AuthView
from ui.views.result_view import ResultView
from ui.views.splash import SplashView
from core.updater import check_for_updates


class ZenCleanApp(ft.Column):
    """
    根视图管理器。继承 ft.Column 替代已废弃的 ft.UserControl。
    负责侧边导航栏、页面容器、路由切换与全局激活状态管理。
    """

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=0)
        self.page = page
        self.is_activated = False
        self.lease_expiry_date: Optional[str] = None
        self.total_expiry_date: Optional[str] = None

        # 分割线：单独持引用，避免硬编码 controls 索引
        self._divider = ft.VerticalDivider(width=1, color="#333333", visible=False)

        # 侧边导航栏
        self._nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=200,
            bgcolor="#1A1A1A",
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.CLEANING_SERVICES_OUTLINED,
                    selected_icon=ft.icons.CLEANING_SERVICES,
                    label="智能清扫",
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
            ],
            on_change=self._on_nav_change,
            visible=False,
        )

        # 页面内容容器
        self._page_container = ft.Container(
            expand=True,
            padding=ft.padding.all(20),
            bgcolor="#0D0D0D",
        )

        # 根布局：左右分割
        self.controls = [
            ft.Row(
                controls=[
                    self._nav_rail,
                    self._divider,
                    self._page_container,
                ],
                expand=True,
                spacing=0,
            )
        ]

        # 路由表：工厂函数惰性构造，保证每次导航都能拿到最新状态
        self._route_factories = {
            "/":          lambda: SplashView(self),
            "/scan":      lambda: ScanView(self),
            "/result":    lambda: ResultView(self),
            "/migration": lambda: MigrationView(self),
            "/auth":      lambda: AuthView(self),
        }
        # 缓存已构建的视图（除 /scan、/result 需每次重建以刷新激活状态）
        self._view_cache: dict[str, ft.Control] = {}
        
        # 共享数据层
        self.scan_nodes: list[dict] = []
        
        # 启动时进行离线免联鉴权（如果本地缓存合法 Token 则静默激活此设备）
        from core.auth import check_local_auth_status
        is_val, payload = check_local_auth_status()
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

    def set_activated(self, is_activated: bool, lease_expiry: Optional[str] = None, total_expiry: Optional[str] = None):
        """全局设置激活状态及到期时间并刷新 UI"""
        self.is_activated = is_activated
        self.lease_expiry_date = lease_expiry
        self.total_expiry_date = total_expiry
        # 刷新导航栏图标显示
        self._nav_rail.destinations[2].selected_icon = ft.icons.VERIFIED_USER if is_activated else ft.icons.LOCAL_POLICE
        self._nav_rail.destinations[2].icon = ft.icons.VERIFIED_USER if is_activated else ft.icons.LOCAL_POLICE_OUTLINED
        self.page.update()

    # ── 导航 ──────────────────────────────────────────────────────────────────

    def _on_nav_change(self, e):
        idx_to_route = {0: "/scan", 1: "/migration", 2: "/auth"}
        self.navigate_to(idx_to_route.get(e.control.selected_index, "/scan"))

    def navigate_to(self, route: str) -> None:
        """切换到指定路由，重建需要反映最新状态的视图。"""
        if route not in self._route_factories:
            return

        # 需要强制每次重建的视图（刷新动态数据或激活状态）
        if route in ["/scan", "/result", "/auth"] or route not in self._view_cache:
            self._view_cache[route] = self._route_factories[route]()

        # 闪屏结束后显示导航栏与分割线
        if route != "/":
            self._nav_rail.visible = True
            self._divider.visible = True

        self._page_container.content = self._view_cache[route]
        self.update()

        # 闪屏视图需要在挂载后主动触发倒计时
        view = self._view_cache[route]
        if hasattr(view, "start"):
            view.start()

