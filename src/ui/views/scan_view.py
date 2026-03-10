import shutil
import time
import flet as ft

from core.scanner import ScanWorker
from ai.cloud_engine import get_quota


from config.settings import (
    COLOR_ZEN_PRIMARY, COLOR_ZEN_BG, COLOR_ZEN_GOLD, 
    COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM
)

# 风险等级 → 徽章颜色 (应用柔和色调)
_RISK_COLOR = {
    "LOW":     "#2ECC71", # 玉石绿
    "MEDIUM":  "#F1C40F", # 哑金
    "HIGH":    "#E67E22", # 暖橙
    "CRISIS":  "#E74C3C", # 朱砂红
    "UNKNOWN": "#95A5A6", 
}

# category 分组中文标签
_CATEGORY_LABEL = {
    "system_temp":    "系统临时文件",
    "browser_cache":  "浏览器缓存",
    "social_cache":   "社交软件缓存",
    "social_media":   "社交媒体文件",
    "windows_update": "Windows 更新缓存",
    "recycle_bin":    "回收站",
    "dev_cache":      "开发工具缓存",
    "dev_build_cache":"构建缓存",
    "app_cache":      "应用缓存",
    "protected":      "系统保护文件",
    "unknown":        "未识别文件",
}


class ScanView(ft.Column):
    """
    扫描主页。
    """

    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app
        self._worker: ScanWorker | None = None
        self._last_scan_update_ts = 0

        # ── 未激活横幅 ────────────────────────────────────────────────────────
        self._activation_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.INFO_OUTLINE, color=COLOR_ZEN_GOLD),
                ft.Text(
                    "当前为标准体验版，仅可手动勾选风险项。成为 VIP 解锁【AI智能引擎】与【一键物理清除】。",
                    expand=True,
                    color=COLOR_ZEN_TEXT_MAIN,
                ),
                ft.TextButton("去激活", on_click=lambda _: self.app.navigate_to("/auth"), style=ft.ButtonStyle(color=COLOR_ZEN_GOLD)),
            ]),
            bgcolor=ft.colors.with_opacity(0.08, "secondary"),
            padding=10,
            border_radius=5,
            visible=not app.is_activated,
        )

        # ── 扫描按钮（渐变光晕动能态） ───────────────────────────────────────────────
        self._scan_btn = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.RADAR, size=40, color="white"),
                    ft.Text("开始智能体检", size=18, weight=ft.FontWeight.BOLD, color="white"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            width=160, height=160,
            border_radius=80,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#00B894", "#00C2FF"], # 压深起始色，提升质感
            ),
            border=ft.border.all(1, ft.colors.with_opacity(0.12, "onSurface")), # 边缘硬化
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=30, color=ft.colors.with_opacity(0.25, "#00B894")), # 降低扩散，加深阴影
            ink=True,
            on_click=self._start_scan,
        )

        # ── 扫描中状态控件 ────────────────────────────────────────────────────
        self._status_text = ft.Text("正在初始化扫描引擎...", color=COLOR_ZEN_TEXT_DIM, size=13)
        self._counter_text = ft.Text("已发现 0 个文件", size=28,
                                     weight=ft.FontWeight.BOLD, color=COLOR_ZEN_PRIMARY, font_family="Consolas")
        self._size_text = ft.Text("可释放空间：计算中...", color=COLOR_ZEN_TEXT_DIM, size=14, font_family="Consolas")
        self._progress = ft.ProgressBar(
            width=400, color=COLOR_ZEN_PRIMARY, bgcolor="outline", visible=False
        )

        # ── 动态风险分布：用原生 Container 动画柱子替代 BarChart ──
        # Container 的 height 变化由 Flutter 引擎 GPU 加速补间，比 BarChart 丝滑得多
        _bar_max_h = 90
        _bar_labels = ["低风险", "建议清理", "高风险", "隔离深区"]
        _bar_colors = [_RISK_COLOR["LOW"], _RISK_COLOR["MEDIUM"], _RISK_COLOR["HIGH"], _RISK_COLOR["CRISIS"]]
        self._risk_bars = []
        self._risk_bar_max_h = _bar_max_h
        _bar_columns = []
        for i in range(4):
            bar = ft.Container(
                width=24,
                height=2,
                bgcolor=_bar_colors[i],
                border_radius=ft.border_radius.only(top_left=6, top_right=6),
                animate=ft.animation.Animation(400, "easeOutCubic"),
            )
            self._risk_bars.append(bar)
            col = ft.Column(
                [
                    ft.Container(content=bar, alignment=ft.alignment.bottom_center, height=_bar_max_h),
                    ft.Container(
                        content=ft.Container(width=8, height=8, bgcolor=_bar_colors[i], border_radius=50),
                        padding=ft.padding.only(top=4),
                    ),
                    ft.Text(_bar_labels[i], size=10, color=COLOR_ZEN_TEXT_DIM, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            )
            _bar_columns.append(col)
        self._risk_bar_row = ft.Row(
            _bar_columns,
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        self._cancel_btn = ft.TextButton(
            "取消扫描", on_click=self._cancel_scan, visible=False, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)
        )

        self._done_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.ROCKET_LAUNCH, color="white"),
                ft.Text("点击揭晓扫描结果", color="white", weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER),
            height=50,
            border_radius=10,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#00B894", "#00C2FF"],
            ),
            border=ft.border.all(1, ft.colors.with_opacity(0.12, "onSurface")),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.colors.with_opacity(0.2, "#00B894")),
            ink=True,
            on_click=lambda _: self.app.navigate_to("/result"),
            visible=False
        )



        # 获取 C 盘容量
        total, used, free = shutil.disk_usage("C:\\")
        total_gb = total / (1024**3)
        free_gb = free / (1024**3)
        used_gb = total_gb - free_gb

        # AI 通道额度展示（闲置态独有）
        self._quota_label = ft.Text("... / ...", color=COLOR_ZEN_PRIMARY, size=14, weight=ft.FontWeight.W_800, visible=False, font_family="Consolas")

        self._target_free_gb = free_gb
        self._target_used_gb = used_gb

        # ── 左侧：数据洞察区 (Analytics Panel) ──
        # 极简锐利科技环 (参考赛博光环设计)
        self._donut_used = ft.PieChartSection(value=total_gb, color="secondaryContainer", radius=12)
        self._donut_free = ft.PieChartSection(value=0.01, color="#2ECC71", radius=12)
        
        self._donut_chart = ft.PieChart(
            sections=[self._donut_used, self._donut_free],
            sections_space=1,      # 保留微小断层感以区分区块
            center_space_radius=90, # 压缩中空区，为下方腾空间
            expand=True,
        )
        self._free_text_control = ft.Text("0.0 GB", size=36, weight=ft.FontWeight.W_900, color="primary", font_family="Consolas")
        
        # 增强版：深层霓虹发光圆环 (带 HUD 质感)
        _glow_donut = ft.Container(
            content=ft.Stack([
                # 底层：制造大范围青紫渐隐光晕的背景盘
                ft.Container(
                    width=210, height=210,
                    border_radius=105,
                    shadow=ft.BoxShadow(
                        spread_radius=10, 
                        blur_radius=80, 
                        color=ft.colors.with_opacity(0.15, "#00E5FF"),
                        offset=ft.Offset(0, 0)
                    ),
                    alignment=ft.alignment.center,
                ),
                
                # 中层：实际的数据环形图
                self._donut_chart,
                
                # 顶层：中心包裹的数据读数
                ft.Container(
                    content=ft.Column([
                        self._free_text_control,
                        ft.Text("可用空间", size=14, color=COLOR_ZEN_TEXT_MAIN, weight=ft.FontWeight.W_500),
                        ft.Text(f"总容量: {total_gb:.1f} GB", size=11, color=COLOR_ZEN_TEXT_DIM, font_family="Consolas"),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    alignment=ft.alignment.center,
                ),
            ], alignment=ft.alignment.center),
            expand=True,
            padding=5,
            alignment=ft.alignment.center,
        )

        # ── 右侧：极客监控磁贴 (Geek Dashboard Tiling) ──
        
        # 提取极简断舍离所需的指标
        health_score = int(free_gb / total_gb * 100) if total_gb > 0 else 100
        health_color = "#2ECC71" if health_score > 30 else "#E67E22" if health_score > 10 else "#E74C3C"

        # C. 核心任务磁贴 (神之护法左右排列版)
        
        # 左侧护法：健康评分 (HUD 翼板版)
        _capsule_health = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.HEALTH_AND_SAFETY, color=health_color, size=24),
                ft.Text(f"{health_score}%", size=14, color=health_color, font_family="Consolas", weight=ft.FontWeight.W_800),
                ft.Text("系统健康", size=9, color=COLOR_ZEN_TEXT_DIM),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            padding=ft.padding.symmetric(vertical=12),
            width=100, height=85,
            bgcolor=ft.colors.with_opacity(0.05, health_color),
            border=ft.border.only(left=ft.BorderSide(2, health_color)),
            border_radius=ft.border_radius.only(top_left=15, bottom_left=15, top_right=5, bottom_right=5),
        )
        
        # 右侧护法：智能算力 (HUD 翼板版)
        _capsule_ai = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.AUTO_AWESOME_MOTION, color=COLOR_ZEN_PRIMARY, size=24),
                # 兼容闲置和刷新状态下的布局
                self._quota_label, 
                ft.Text("智能算力", size=9, color=COLOR_ZEN_TEXT_DIM),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            padding=ft.padding.symmetric(vertical=12),
            width=100, height=85,
            bgcolor=ft.colors.with_opacity(0.05, COLOR_ZEN_PRIMARY),
            border=ft.border.only(right=ft.BorderSide(2, COLOR_ZEN_PRIMARY)),
            border_radius=ft.border_radius.only(top_right=15, bottom_right=15, top_left=5, bottom_left=5),
        )

        # 组合中心护法法阵 (增加间距以释放压力)
        _center_altar = ft.Row([
            _capsule_health,
            ft.Container(self._scan_btn, margin=ft.margin.symmetric(horizontal=30)),
            _capsule_ai
        ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self._action_tile = ft.Container(
            content=ft.Column([
                ft.Text("禅清数据控制中心", size=24, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                ft.Text("通过本地 Rule Engine 与双重粉碎法释放空间", color=COLOR_ZEN_TEXT_DIM, size=12),
                ft.Container(height=10),
                _center_altar,
                ft.Container(height=10),
                ft.Text("预计扫查耗时 1.8s · 深度提权模式已开启", size=11, color="#6B7280"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(vertical=5, horizontal=0),
            alignment=ft.alignment.center,
        )

        # ── D. 极限空间挖掘 (Advanced Tiles) NEW ──
        # 1. 休眠管理
        self._tile_hibernation = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.SNOWING, color="#00D4AA", size=24),
                ft.Text("睡眠/休眠", size=13, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                ft.Text("释放 8-32GB", size=11, color=COLOR_ZEN_TEXT_DIM)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=15, bgcolor=ft.colors.with_opacity(0.03, "onSurface"), border_radius=10, expand=True,
            border=ft.border.all(1, ft.colors.with_opacity(0.2, "primary")), ink=True,
            on_click=self._on_click_hibernation_tile,
            on_hover=self._on_hover_tile
        )
        
        # 2. 应用搬家
        self._tile_app_migration = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.DRIVE_FILE_MOVE, color="#00D4AA", size=24),
                ft.Text("无损搬家", size=13, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                ft.Text("微信/Docker", size=11, color=COLOR_ZEN_TEXT_DIM)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=15, bgcolor=ft.colors.with_opacity(0.03, "onSurface"), border_radius=10, expand=True,
            border=ft.border.all(1, ft.colors.with_opacity(0.2, "primary")), ink=True,
            on_click=self._on_click_migration_tile,
            on_hover=self._on_hover_tile
        )

        # 3. 更新清理
        self._tile_update_clean = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.SECURITY_UPDATE_WARNING, color="#E74C3C", size=24),
                ft.Text("陈年补丁", size=13, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                ft.Text("无法撤回", size=11, color="#E74C3C")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=15, bgcolor=ft.colors.with_opacity(0.08, "error"), border_radius=10, expand=True,
            border=ft.border.all(1, ft.colors.with_opacity(0.3, "error")), ink=True,
            on_click=self._on_click_update_clean_tile,
            on_hover=self._on_hover_tile
        )

        # 4. 虚拟内存
        self._tile_virtual_mem = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.MEMORY, color="#E67E22", size=24),
                ft.Text("虚拟内存", size=13, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                ft.Text("转移或缩减", size=11, color="#E67E22")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=15, bgcolor=ft.colors.with_opacity(0.03, "onSurface"), border_radius=10, expand=True,
            border=ft.border.all(1, ft.colors.with_opacity(0.2, "tertiary")), ink=True,
            on_click=self._on_click_virtual_mem_tile,
            on_hover=self._on_hover_tile
        )

        _advanced_row_1 = ft.Row([self._tile_hibernation, self._tile_virtual_mem], spacing=15)
        _advanced_row_2 = ft.Row([self._tile_app_migration, self._tile_update_clean], spacing=15)

        # 组合极客大屏布局 (彻底断舍离中间层组件)
        self._idle_execution = ft.Container(
            content=ft.Column([
                self._action_tile,
                ft.Divider(height=1, thickness=1.2, color=ft.colors.with_opacity(0.3, "onSurfaceVariant")),
                _advanced_row_1,
                _advanced_row_2
            ], spacing=20, expand=True, alignment=ft.MainAxisAlignment.CENTER),
            expand=True,
        )
        
        # 右侧：引擎执行区 - 扫描态 (Active) SaaS 控制台化布局
        self._active_execution = ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.Container(
                            content=ft.ProgressRing(width=22, height=22, stroke_width=3, color=COLOR_ZEN_PRIMARY),
                            padding=ft.padding.only(right=10)
                        ),
                        ft.Text("正在执行指令集: 深度扫描中...", size=20, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    ft.Container(height=20),
                    self._counter_text,
                    self._size_text,
                    ft.Container(height=10),
                    self._progress,
                    ft.Container(height=15),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("实时数据流 (Real-time Stream)", color=COLOR_ZEN_TEXT_DIM, size=11, font_family="Consolas"),
                            self._status_text,
                        ], spacing=5),
                        bgcolor="surface", 
                        padding=15,
                        border_radius=8,
                        border=ft.border.all(1, ft.colors.with_opacity(0.15, "onSurface")),
                        width=float('inf')
                    ),
                    ft.Container(height=10),
                    ft.Row([self._cancel_btn, self._done_btn], alignment=ft.MainAxisAlignment.END),
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            expand=True,
            visible=False,
        )

        # ── E. 左侧底座：极客雷达探测大户 (Top Folders Panel) ──
        self._top_folders_panel = ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.icons.RADAR, size=16, color=COLOR_ZEN_PRIMARY),
                    ft.Text("正在隐蔽勘探深层巨兽...", size=12, color=COLOR_ZEN_TEXT_DIM, font_family="Consolas"),
                    ft.ProgressRing(width=12, height=12, stroke_width=2, color=COLOR_ZEN_PRIMARY)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            ],
            scroll=ft.ScrollMode.HIDDEN,
            expand=True,
            spacing=2,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        
        _left_panel_wrapper = ft.Container(
            content=ft.Column([
                _glow_donut,
                ft.Container(height=10),
                ft.Row([
                    ft.Text("空间大户探针 Top 5", size=15, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Icon(ft.icons.INFO_OUTLINE, size=14, color="primary")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5),
                self._top_folders_panel
            ], expand=True, spacing=2),
            expand=3, # 左 3 右 5 的比例
            padding=12,
            margin=ft.padding.only(left=20, top=20, bottom=20, right=10),
            bgcolor="surfaceVariant",
            border_radius=16,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, "onSurface")),
        )

        _execution_panel_wrapper = ft.Container(
             content=ft.Stack([self._idle_execution, self._active_execution]),
             expand=5,
             padding=20,
             margin=ft.padding.only(left=10, top=20, bottom=20, right=20),
             bgcolor="surfaceVariant",
             border_radius=16,
             border=ft.border.all(1, ft.colors.with_opacity(0.1, "onSurface")),
        )

        # ── 聚合为主视图 ───────────────────────────────────────────
        self._main_dashboard = ft.Container(
            content=ft.Row(
                [
                    _left_panel_wrapper,
                    _execution_panel_wrapper
                ],
                expand=True,
            ),
            expand=True,
        )

        super().__init__(
            controls=[
                self._activation_banner,
                self._main_dashboard,
            ],
            expand=True,
        )

    # ── 扫描启动 ──────────────────────────────────────────────────────────────

    # ── 扫描启动 ──────────────────────────────────────────────────────────────

    def _start_scan(self, e) -> None:
        """立刻进入扫描态，同时在后台异步核验权限（先上车后补票）。"""
        # 1. 立即清空上次扫描结果
        self.app.scan_nodes.clear()

        # 2. 立即切换 UI 面板 (秒开体验)
        self._idle_execution.visible = False
        self._active_execution.visible = True
        self._progress.visible = True
        self._cancel_btn.visible = True
        self._done_btn.visible = False
        self._status_text.value = "正在展开扫描引擎..."
        self._counter_text.value = "正在连接扫描靶标..."
        self._size_text.value = "可释放空间：计算中..."
        
        self.update()

        # 3. 立即启动 Thread 扫描进程
        # 直接使用线程版的 ScanWorker 并将回调封入 Flet 同步队列中（保证 UI 线程安全）
        self._worker = ScanWorker(
            on_nodes=lambda nodes: self.app.page.run_task(self._handle_scan_nodes_ui, nodes),
            on_done=lambda total, skipped: self.app.page.run_task(self._handle_scan_done_ui, total, skipped),
            on_error=lambda msg: self.app.page.run_task(self._handle_scan_error_ui, msg)
        )
        self._worker.start()

        # 4. 同时拉起后台核验随航逻辑（仅针对当前是 VIP 的用户）
        if self.app.is_activated:
            async def _async_license_follow_check():
                from core.auth import verify_license_online, check_local_auth_status
                from core.logger import logger
                import asyncio

                is_val, payload = check_local_auth_status()
                license_key = payload.get("_local_license_key") if (is_val or (payload and "_local_license_key" in payload)) else None
                
                if not license_key:
                    return

                # 扫描前在线复核权限，支持通知解包
                is_val, msg, note = await asyncio.to_thread(verify_license_online, license_key)
                if note:
                    self.app.process_server_notification(note)
                
                if not is_val and ("[REVOKED]" in msg or ("网络" not in msg and "服务端异常" not in msg)):
                    logger.warning(f"Scan license check failed: license revoked/unbound on backend. {msg}")
                    
                    # 【核心优化】不再熔断中止扫描，而是静默执行 UI 降级并删除本地令牌
                    # 这样后续扫描出的项由于找不到 Token 会自动落回本地规则
                    self.app.set_activated(False)
                    
                    # 弹出降级通知
                    if self.app.page:
                        # 获取明确的拦截原因
                        alert_msg = "检测到授权已失效，正在以标准体验版继续扫描。"
                        if "[REVOKED]" in msg:
                            alert_msg = f"授权失效：{msg.replace('[REVOKED]', '').strip()}，已切换为标准版。"

                        self.app.page.snack_bar = ft.SnackBar(
                            ft.Text(alert_msg),
                            bgcolor=ft.colors.ORANGE_800
                        )
                        self.app.page.snack_bar.open = True
                        self.app.page.update()

            self.app.page.run_task(_async_license_follow_check)

    # ── 取消扫描 ──────────────────────────────────────────────────────────────

    def _cancel_scan(self, e) -> None:
        if self._consumer:
            self._consumer.stop()
        if self._worker and self._worker.is_alive():
            self._worker.terminate()
        self._reset_to_idle()

    def _reset_to_idle(self) -> None:
        self._idle_execution.visible = True
        self._active_execution.visible = False
        self._active_execution.disabled = True # 彻底封锁事件捕获
        self._progress.visible = False
        self._cancel_btn.visible = False
        self._done_btn.visible = False
        self.update()

    # ── QueueConsumer 回调（在消费线程中执行，必须使用异步方式调度到主线程安全执行） ──

    def did_mount(self):
        """视图挂载到页面时，进行初始化工作。"""
        
        # 提取应用级持久标志位：由于 ScanView 每次回到 /scan 都会重新实例化，防抖锁必须挂载在 app 实例上
        is_already_loaded = getattr(self.app, "_is_scan_dashboard_loaded", False)
        self.app._is_scan_dashboard_loaded = True
        
        import os
        
        # ── 0. 消费右键自动拉起扫描的目标 ──
        if getattr(self.app, "auto_scan_path", None):
            auto_path = self.app.auto_scan_path
            self.app.auto_scan_path = None  # 立刻吞掉，防止路由切换时反复触发
            if os.path.exists(auto_path):
                self.app.scan_nodes = [auto_path]
                # Flet 较新版本 run_task 强制要求异步协程，普通函数直接调用即可
                self._start_scan(None)

        cache_path = os.path.join(os.getcwd(), "zenclean_space_cache.json")
        has_cache = os.path.exists(cache_path)
        
        # ── 1. 容量完全体瞬间复原 vs 甜甜圈装载动效 ──
        # 如果不是首次进入，或者本地已经有雷达勘探结果的缓存，我们都直接跳过归零的倒吸动画以防止 UI 回退闪烁。
        if is_already_loaded or has_cache:
            # 跳过倒吸，瞬间渲染终态（稍后会被缓存加载覆写为彩色饼图）
            self._donut_free.value = max(self._target_free_gb, 0.01)
            self._donut_used.value = self._target_used_gb
            self._free_text_control.value = f"{self._target_free_gb:.1f} GB"
            self.update()
        else:
            # 只有完完全全的第一次空白环境启动，才播放吸水动画
            async def _animate():
                import asyncio
                steps = 40
                for i in range(1, steps + 1):
                    progress = i / steps
                    ease = 1 - pow(1 - progress, 3) # easeOutCubic
                    curr_free = self._target_free_gb * ease
                    curr_used = self._target_used_gb + self._target_free_gb * (1 - ease)
                    self._donut_free.value = max(curr_free, 0.01)
                    self._donut_used.value = curr_used
                    self._free_text_control.value = f"{curr_free:.1f} GB"
                    if self.page:
                        self.update()
                    await asyncio.sleep(0.016)
            self.app.page.run_task(_animate)
        
        # 已激活用户异步获取 AI 额度
        if getattr(self.app, "is_activated", False):
            self._quota_label.visible = True
            
            async def _fetch_quota():
                import asyncio
                # 把同步请求交由线程池以免阻塞 UI 渲染
                quota = await asyncio.to_thread(get_quota)
                if quota and getattr(self, "_quota_label", None):
                    used = quota.get('used_today', 0)
                    limit = quota.get('daily_limit', 0)
                    self._quota_label.value = f"{used} / {limit}"
                    self._quota_label.size = 14
                    self._quota_label.font_family = "Consolas"
                    self._quota_label.weight = ft.FontWeight.W_800
                    self._quota_label.color = COLOR_ZEN_PRIMARY
                    if self.page:
                        self.update()
            
            self.app.page.run_task(_fetch_quota)

        # ── 异步启动底层空间探测雷达 (极客大户透视) ──
        async def _fetch_top_folders():
            import asyncio
            import json
            import os
            from core.space_analyzer import stream_top_folders
            from core.logger import logger
            
            cache_path = os.path.join(os.getcwd(), "zenclean_space_cache.json")
            
            def _render_item(item_data, rank):
                # 统一渲染单个卡片的逻辑
                size_gb = item_data['size_bytes'] / (1024**3)
                is_junc = item_data.get('is_junction', False)
                is_sys = item_data.get('is_protected', False)
                path_str = item_data['path']
                name = item_data['name']
                
                palette = ["#E74C3C", "#E67E22", "#F1C40F", "#3498DB", "#9B59B6"]
                color_hex = palette[rank % len(palette)]
                
                link_icon = ft.Icon(ft.icons.LINK, size=14, color=color_hex, visible=is_junc)
                sys_icon = ft.Icon(ft.icons.SHIELD_OUTLINED, size=14, color="error", visible=is_sys)
                
                return ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.FOLDER_OUTLINED, size=18, color=color_hex),
                        ft.Column([
                            ft.Text(name, size=12, weight=ft.FontWeight.W_600, color=COLOR_ZEN_TEXT_MAIN),
                            ft.Text(f"({size_gb:.1f} GB)", size=10, color=COLOR_ZEN_TEXT_DIM),
                        ], expand=True, spacing=2),
                        ft.Row([link_icon, sys_icon, ft.IconButton(ft.icons.FOLDER_OPEN, icon_size=14, icon_color=color_hex, on_click=lambda _, p=path_str: os.startfile(p) if os.path.exists(p) else None)], spacing=0)
                    ], alignment=ft.MainAxisAlignment.START, spacing=10),
                    padding=ft.padding.symmetric(vertical=4, horizontal=12),
                    border_radius=8,
                    bgcolor=ft.colors.with_opacity(0.1, color_hex) if is_junc else ft.colors.with_opacity(0.05, "onSurface"),
                    margin=ft.padding.only(bottom=2),
                    border=ft.border.all(1, color_hex if is_junc else ft.colors.with_opacity(0.1, "onSurfaceVariant"))
                )

            def _update_pie_chart(items):
                # 利用收集到的 Top 文件夹切片更新左侧饼图
                palette = ["#E74C3C", "#E67E22", "#F1C40F", "#3498DB", "#9B59B6"]
                top_size_bytes = 0
                sections = []
                
                for i, t in enumerate(items[:5]):
                    val_gb = t["size_bytes"] / (1024**3)
                    top_size_bytes += t["size_bytes"]
                    sections.append(ft.PieChartSection(value=max(val_gb, 0.05), color=palette[i % len(palette)], radius=16, title=""))
                
                used_bytes = self._target_used_gb * (1024**3)
                other_used_gb = max((used_bytes - top_size_bytes) / (1024**3), 0)
                
                # 注入 "其他已用" 与 "可用空间"
                sections.insert(0, ft.PieChartSection(value=max(other_used_gb, 0.1), color="secondaryContainer", radius=12, title=""))
                sections.append(ft.PieChartSection(value=max(self._target_free_gb, 0.1), color="#2ECC71", radius=12, title=""))
                
                if getattr(self, "_donut_chart", None):
                    self._donut_chart.sections = sections

            try:
                # 一级跳：加载离线快照 (秒开)
                live_items = []
                if os.path.exists(cache_path):
                    with open(cache_path, "r", encoding="utf-8") as f:
                        try:
                            live_items = json.load(f)
                            if live_items:
                                self._top_folders_panel.controls.clear()
                                for i, item in enumerate(live_items[:5]):
                                    self._top_folders_panel.controls.append(_render_item(item, i))
                                _update_pie_chart(live_items)
                                if self.page: self.update()
                        except Exception:
                            live_items = []

                # 二级跳：异步启动实时雷达探测 (后台静默)
                # 如果当前 Session 已经跑过实时扫描，则不再重复高负载扫描
                if is_already_loaded:
                    return

                await asyncio.sleep(0.5) 
                directories = ["C:\\", "%USERPROFILE%", "%LOCALAPPDATA%", "%APPDATA%"]
                # 三级跳：流式更新 (动态排行榜)
                # 使用 to_thread 迭代生成器
                gen = stream_top_folders(directories, 15)
                while True:
                    item = await asyncio.to_thread(next, gen, None)
                    if item is None: break
                    
                    # 增量式/差异式更新：将新发现的项目与已有列表合并，去重并重排
                    existing_paths = {it['path'] for it in live_items}
                    if str(item.path) not in existing_paths:
                        live_items.append({
                            "path": str(item.path),
                            "size_bytes": item.size_bytes,
                            "name": item.name,
                            "is_junction": item.is_junction,
                            "is_protected": item.is_protected
                        })
                    
                    # 动态重排
                    live_items.sort(key=lambda x: x['size_bytes'], reverse=True)
                    top_5 = live_items[:5]
                    
                    # 平滑驱动 UI
                    self._top_folders_panel.controls.clear()
                    for i, t in enumerate(top_5):
                        self._top_folders_panel.controls.append(_render_item(t, i))
                    
                    _update_pie_chart(top_5)
                        
                    if self.page: self.update()
                    # 降低 UI 刷新频率，扫描早期密集时稍微等待
                    await asyncio.sleep(0.1 if len(live_items) < 10 else 0.05)

                # 保存最终快照
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(live_items[:10], f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                logger.error(f"Top folders fetch failed: {e}")
                if getattr(self, "_top_folders_panel", None):
                    self._top_folders_panel.controls.clear()
                    self._top_folders_panel.controls.append(ft.Text("雷达扫描意外中断", color="error", size=11))
                    if self.page: self.update()

        self.app.page.run_task(_fetch_top_folders)

    def will_unmount(self):
        """视图被卸载时进行销毁工作。"""
        pass

    # ── 直接 UI 回调（从后台线程触发，经由 run_task 投递到 UI 事件循环） ──

    async def _handle_scan_nodes_ui(self, nodes: list[dict]) -> None:
        if not getattr(self, "_active_execution", None) or not self._active_execution.visible:
            return 
            
        self.app.scan_nodes.extend(nodes)
        total = len(self.app.scan_nodes)
        freed = sum(
            n["size_bytes"] for n in self.app.scan_nodes
            if n.get("risk_level") in ("LOW", "MEDIUM")
        )
        self._counter_text.value = f"已发现 {total:,} 个文件"
        gb = freed / 1024 ** 3
        if freed >= 1024 ** 3:
            self._size_text.value = f"可释放空间：{gb:.2f} GB"
        elif freed >= 1024 ** 2:
            self._size_text.value = f"可释放空间：{freed / 1024**2:.1f} MB"
        else:
            self._size_text.value = f"可释放空间：{freed / 1024:.0f} KB"
            


        now = time.time()
        # 限制 UI 刷新帧率（约 25FPS对应 0.04s）
        if now - self._last_scan_update_ts > 0.04 or total == 0:
            if self.page: self.update()
            self._last_scan_update_ts = now

    async def _handle_scan_done_ui(self, total: int, skipped: int) -> None:
        import asyncio
        if self.page: self.update()
        
        await asyncio.sleep(0.5) 
        
        self._progress.visible = False
        self._cancel_btn.visible = False
        self._done_btn.visible = True
        self._status_text.value = f"扫描完成，共 {total:,} 个文件，跳过 {skipped:,} 个"
        self._status_text.color = "secondary"

        self.app.has_scanned = True
        self._worker = None
        if self.page: self.update()

        # 自动跳转：停留 1.2 秒让用户看清最终统计结果
        if self.page:
            async def _auto_nav():
                await asyncio.sleep(1.2)
                if self.page:
                    self.app.navigate_to("/result")
            self.app.page.run_task(_auto_nav)

    async def _handle_scan_error_ui(self, error_msg: str) -> None:
        self._progress.visible = False
        self._cancel_btn.visible = False
        self._done_btn.visible = True
        self._status_text.value = f"扫描出错: {error_msg}"
        self._status_text.color = "error"

        self.app.has_scanned = True
        self._worker = None
        if self.page: self.update()

    # ── 高阶功能：系统休眠管控弹窗 ──────────────────────────────────────────────
    def _on_click_hibernation_tile(self, e):
        from core.system_optimizer import is_hibernation_enabled, disable_hibernation, enable_hibernation
        
        is_enabled = is_hibernation_enabled()
        
        def close_dlg(e):
            if hasattr(self, '_hiber_dlg'):
                self._hiber_dlg.open = False
                self.app.page.update()

        def confirm_action(e):
            close_dlg(e)
            
            # 显示一个临时的执行态 Snackbar
            self.app.page.snack_bar = ft.SnackBar(ft.Text("正在执行底层指令并创建回滚快照..."), bgcolor=COLOR_ZEN_PRIMARY)
            self.app.page.snack_bar.open = True
            self.app.page.update()
            
            if is_enabled:
                import threading
                def _do_disable():
                    success, msg = disable_hibernation(auto_backup=True)
                    # 异步回调到主线程更新 UI
                    if self.app.page:
                         async def wrapper(): _finish_hiber_action(success, msg, disable=True)
                         self.app.page.run_task(wrapper)
                threading.Thread(target=_do_disable, daemon=True).start()
            else:
                 success, msg = enable_hibernation()
                 _finish_hiber_action(success, msg, disable=False)
                 
        def _finish_hiber_action(success: bool, msg: str, disable: bool):
            if success:
                self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green")
                if disable:
                    # 假如有条件，这里应该动态增加 16GB 的饼图余量以提升爽感
                    pass
            else:
                self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=ft.colors.RED_800)
            self.app.page.snack_bar.open = True
            self.app.page.update()

        title_text = "确认关闭系统休眠与快速启动？" if is_enabled else "重新开启系统休眠？"
        content_text = (
            "【当前状态】：系统休眠已开启\n\n"
            "关闭休眠能够一次性彻底释放与您物理内存等大（通常 16GB - 32GB）的隐藏空间。\n"
            "代价是：系统将失去「快速启动」功能，开机可能会变慢。\n\n"
            "ZenClean 将会在执行前尝试创建系统还原点保驾护航。"
        ) if is_enabled else (
            "【当前状态】：休眠已关闭\n\n您的 C 盘已减去沉重包袱。重新开启将吃掉大量空间恢复原状。"
        )

        self._hiber_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER, color="#00D4AA" if is_enabled else COLOR_ZEN_TEXT_DIM), ft.Text(title_text)]),
            content=ft.Text(content_text, size=13),
            actions=[
                ft.TextButton("取消", on_click=close_dlg, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
                ft.ElevatedButton("立即执行", on_click=confirm_action, bgcolor=COLOR_ZEN_PRIMARY, color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.dialog = self._hiber_dlg
        self._hiber_dlg.open = True
        self.app.page.update()

    # ── 高阶功能：应用搬家框架 ──────────────────────────────────────────────
    def _on_click_migration_tile(self, e):
        self.app.navigate_to("/app_migration")

    # ── 高阶功能：补丁清理框架 ──────────────────────────────────────────────
    def _on_click_update_clean_tile(self, e):
         from core.system_optimizer import clean_windows_updates
         import threading
         
         def close_dlg(e=None):
             if hasattr(self, '_upd_dlg'):
                self._upd_dlg.open = False
                self.app.page.update()
                
         def confirm_action(e):
             # 切换 UI 状态到进度显示
             btn_execute.visible = False
             btn_cancel.visible = False
             progress_col.visible = True
             content_text.visible = False
             self._upd_dlg.title.controls[1].value = "正在粉碎组件仓库 (请稍候)..."
             self.app.page.update()
             
             def _do_clean():
                 def _progress(val):
                     if self.app.page:
                         async def prog_wrapper(): _update_prog(val)
                         self.app.page.run_task(prog_wrapper)
                 
                 success, msg = clean_windows_updates(on_progress=_progress)
                 
                 if self.app.page:
                     async def fin_wrapper(): _finish(success, msg)
                     self.app.page.run_task(fin_wrapper)
             
             # 挂起一条线程，防止阻塞 Flet 主事件循环
             threading.Thread(target=_do_clean, daemon=True).start()

         def _update_prog(val):
             # 放弃精准进度，因为通过 pipe 重定向后 DISM 会不再输出控制台刷新符
             pass
             
         def _finish(success: bool, msg: str):
             close_dlg()
             color = "green" if success else ft.colors.RED_800
             self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
             self.app.page.snack_bar.open = True
             self.app.page.update()

         progress_bar = ft.ProgressBar(value=None, color="error", bgcolor="outline", expand=True)
         progress_text = ft.Text("引擎运转中", size=12, color="error", font_family="Consolas")
         progress_col = ft.Column([
             ft.Text("正在执行指令集 (视您的磁盘瓶颈，约耗时 1~5 分钟)\n切勿强制关机/重启机器，请耐心等待弹窗自动消失！", color=COLOR_ZEN_TEXT_DIM),
             ft.Container(height=15),
             ft.Row([progress_bar, progress_text])
         ], visible=False)

         content_text = ft.Text(
             "【警告：极客指令】\n\n此操作将强行剥离 Windows 底层的组件存根仓库 (WinSxS 更新备份等)。"
             "这通常能释放 3GB ~ 15GB 的超大深层空间。\n\n"
             "后果：您将彻底失去「卸载或回退近期个别 Windows 补丁」的能力 (但不影响系统运行与未来的新更新)。",
             size=13
         )
         
         body = ft.Stack([
             content_text,
             progress_col
         ])

         btn_cancel = ft.TextButton("取消", on_click=close_dlg, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM))
         btn_execute = ft.ElevatedButton("无惧后果，立即粉碎", on_click=confirm_action, bgcolor="error", color="white")
         
         self._upd_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.icons.SECURITY_UPDATE_WARNING, color="#E74C3C"), ft.Text("粉碎历史补丁", color="#E74C3C")]),
            content=ft.Container(content=body, width=420, height=130),
            actions=[btn_cancel, btn_execute],
            actions_alignment=ft.MainAxisAlignment.END,
        )
         self.app.page.dialog = self._upd_dlg
         self._upd_dlg.open = True
         self.app.page.update()

    # ── 高阶功能：虚拟内存管理框架 ──────────────────────────────────────────────
    def _on_click_virtual_mem_tile(self, e):
         def close_dlg(e):
             if hasattr(self, '_vm_dlg'):
                self._vm_dlg.open = False
                self.app.page.update()
                
         def open_sysdm(e):
             import subprocess
             try:
                 subprocess.Popen("control sysdm.cpl,,3")
             except Exception:
                 pass
             close_dlg(e)
                
         self._vm_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.icons.MEMORY, color="#E67E22"), ft.Text("转移或缩减虚拟内存", color="#E67E22")]),
            content=ft.Text(
                "系统默认会在 C 盘根目录生成巨大的 pagefile.sys (通常占十几GB)。\n\n"
                "ZenClean 将为您直达系统属性。请在弹出的窗口中执行以下操作：\n"
                "1. 点击「设置 (Settings)」\n"
                "2. 切换到顶部的「高级 (Advanced)」选项卡\n"
                "3. 点击虚拟内存下方的「更改 (Change)」按钮", 
                size=13
            ),
            actions=[
                ft.TextButton("取消", on_click=close_dlg, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
                ft.ElevatedButton("直达系统设置", on_click=open_sysdm, bgcolor="tertiary", color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
         self.app.page.dialog = self._vm_dlg
         self._vm_dlg.open = True
         self.app.page.update()

    def _on_hover_tile(self, e):
        # 统管磁贴的悬停视觉逻辑 (机甲亮边特效)
        base_color = e.control.border.top.color # 提取原始边框色
        if e.data == "true": # 移入
             e.control.border = ft.border.all(1, base_color.replace("#33", "#FF").replace("#55", "#FF"))
             e.control.shadow = ft.BoxShadow(blur_radius=15, spread_radius=-5, color=base_color.replace("#33", "#66").replace("#55", "#88"))
             e.control.scale = 1.02
        else: # 移出
             orig_prefix = "#55" if "E74C3C" in base_color else "#33"
             e.control.border = ft.border.all(1, base_color.replace("#FF", orig_prefix))
             e.control.shadow = None
             e.control.scale = 1.0
        e.control.update()

