import os
import flet as ft
from typing import Optional
from datetime import datetime

from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_SURFACE, 
    COLOR_ZEN_GOLD, COLOR_ZEN_DIVIDER, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM
)
from ui.views.scan_view import ScanView
from ui.views.migration_view import MigrationView
from ui.views.auth_view import AuthView
from ui.views.result_view import ResultView
from ui.views.splash import SplashView

class ZenCleanApp(ft.Column):
    """
    根视图管理器。负责沉浸式顶栏、侧边导航栏、页面容器、路由切换。
    """

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=0)
        self.page = page
        self.is_activated = False
        self.lease_expiry_date: Optional[str] = None
        self.total_expiry_date: Optional[str] = None

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

        _window_controls = ft.Row([
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
            bgcolor=COLOR_ZEN_BG,
        )

        # 根布局：加入顶栏，下方左右分割
        self.controls = [
            self._title_bar,
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
        
        # 启动时进行一次延时的静默版本检查广播接收
        self._start_silent_update_check()
        
    def _start_silent_update_check(self):
        import time
        import threading
        from core.updater import check_for_updates

        def _silent_callback(has_new, latest_version, url, msg):
            if has_new:
                # 接收到含更新的高能通知，展示顶部提示条
                def _ui_update():
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Row([
                            ft.Icon(ft.icons.SYSTEM_UPDATE, color=COLOR_ZEN_PRIMARY),
                            ft.Text(f"系统播报：发现新版本 v{latest_version}，{msg}"),
                            ft.TextButton("立即去下载", on_click=lambda _: self.page.launch_url(url) if url else None)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor="#252525",
                        duration=15000,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                
                if self.page:
                    self.page.invoke_callback(_ui_update)
                
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
                        # 如果已经被其他机制降级（例如在前台点退出、或者上一次轮询已经降级），直接退出探测循环
                        if not self.is_activated:
                            break

                        # 传入 is_auto_check=True，防止服务端对于已解绑的激活码执行误判自动重新绑定
                        success, msg = verify_license_online(license_key, is_auto_check=True)
                        logger.info(f"[BG_VERIFY] result: success={success}, msg={msg}")
                        
                        if not success and ("[REVOKED]" in msg or ("网络" not in msg and "服务端异常" not in msg)):
                            # 以下的所有 UI 操作必须在主循环或其协程中安全执行，否则会引发线程死锁
                            async def update_ui_safe():
                                logger.warning(f"[BG_VERIFY] license revoked! Executing downgrade.")
                                # 主动清除本地验证状态，降级为非 VIP
                                if AUTH_DAT_PATH.exists():
                                    try:
                                        AUTH_DAT_PATH.unlink()
                                        logger.info("[BG_VERIFY] Local auth cache removed.")
                                    except Exception as e:
                                        logger.error(f"[BG_VERIFY] Failed to remove auth cache: {e}")
                                        pass
                                
                                self.set_activated(False)

                                # 获取明确的拦截原因
                                alert_msg = "您的授权已失效或在其他设备被解绑，当前已恢复为免费版。"
                                if "[REVOKED]" in msg:
                                    alert_msg = msg.replace("[REVOKED]", "").strip()

                                # 弹窗提示用户授权已失效
                                self.page.snack_bar = ft.SnackBar(
                                    ft.Text(alert_msg),
                                    bgcolor=ft.colors.RED_800,
                                )
                                self.page.snack_bar.open = True
                                self.page.update()

                            # 送入 Flet 主 UI 线程的安全更新队列
                            self.page.run_task(update_ui_safe)
                            
                            # 已经完成降级，停止循环探测
                            break
                            
                        # 没问题的话，睡半小时再检查兜底
                        time.sleep(1800)

                threading.Thread(target=_bg_verify, daemon=True).start()


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
            self._title_bar.visible = True

        self._page_container.content = self._view_cache[route]
        self.update()

        # 闪屏视图需要在挂载后主动触发倒计时
        view = self._view_cache[route]
        if hasattr(view, "start"):
            view.start()

    def _window_minimize(self, e):
        self.page.window.minimized = True
        self.page.update()

    def _window_maximize(self, e):
        self.page.window.maximized = not getattr(self.page.window, "maximized", False)
        self.page.update()

    def _window_close(self, e):
        try:
            if hasattr(self.page.window, "close"):
                self.page.window.close()
            else:
                self.page.window.destroy()
        except Exception:
            self.page.window_destroy()
