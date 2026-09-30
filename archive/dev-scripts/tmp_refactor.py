import re
import sys

with open(r"d:\软件开发\ZenClean\src\ui\views\scan_view.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 替换 _scanning_panel 和图表定义 (Line 112 -> 212)
# 先移除原来的 _scanning_panel
content = re.sub(
    r"        self\._scanning_panel = ft\.Container\(\n.*?visible=False,\n        \)\n",
    "",
    content,
    flags=re.DOTALL
)

# 找到 # 左侧：数据洞察区 到 super().__init__ 的结束
old_layout_pattern = r"        # 左侧：数据洞察区 \(Analytics Panel\).*?expand=True,\n        \)"

new_layout = """        self._target_free_gb = free_gb
        self._target_used_gb = used_gb

        # 初始化环形图：0 可用空间，后续靠动画涨血
        self._donut_used = ft.PieChartSection(value=total_gb, color="#252A36", radius=25) 
        self._donut_free = ft.PieChartSection(value=0.01, color=COLOR_ZEN_PRIMARY, radius=30)
        
        # 左侧：数据洞察区 (Analytics Panel)
        _donut_chart = ft.PieChart(
            sections=[self._donut_used, self._donut_free],
            sections_space=2,
            center_space_radius=90,
            expand=True,
        )

        self._free_text_control = ft.Text("0.0 GB", size=32, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_PRIMARY, font_family="Consolas")
        
        _analytics_panel = ft.Container(
            content=ft.Stack([
                _donut_chart,
                ft.Container(
                    content=ft.Column([
                        self._free_text_control,
                        ft.Text("可用空间", size=13, color=COLOR_ZEN_TEXT_DIM),
                        ft.Container(height=5),
                        ft.Text(f"总容量 {total_gb:.1f} GB", size=11, color="#6B7280", font_family="Consolas"),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    alignment=ft.alignment.center,
                ),
            ]),
            expand=4, # 占位比重 4
            padding=20,
        )

        # 右侧：引擎执行区 - 闲置态 (Idle)
        self._idle_execution = ft.Container(
            content=ft.Column(
                [
                    ft.Text("系统深度体检", size=32, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Text("通过本地 Rule Engine 与双重粉碎法，安全释放您的磁盘空间", color=COLOR_ZEN_TEXT_DIM, size=13),
                    ft.Container(height=30),
                    self._quota_label,
                    self._scan_btn,
                    ft.Container(height=10),
                    ft.Text("基于本地 Rule Engine · 预计扫查耗时 1.8s", size=11, color="#6B7280"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            expand=True,
        )
        
        # 右侧：引擎执行区 - 扫描态 (Active) SaaS 控制台化布局
        self._active_execution = ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.ProgressRing(width=24, height=24, stroke_width=3, color=COLOR_ZEN_PRIMARY),
                        ft.Text("智能体检引擎运行中...", size=20, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Container(height=20),
                    self._counter_text,
                    self._size_text,
                    ft.Container(height=10),
                    self._progress,
                    ft.Container(
                        content=ft.Column([
                            ft.Text("实时数据流 (Real-time Stream)", color=COLOR_ZEN_TEXT_DIM, size=11, font_family="Consolas"),
                            self._status_text,
                        ], spacing=5),
                        bgcolor="#0F1115", 
                        padding=15,
                        border_radius=8,
                        border=ft.border.all(1, "#11FFFFFF"),
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

        _execution_panel_wrapper = ft.Container(
             content=ft.Stack([self._idle_execution, self._active_execution]),
             expand=6,
             padding=20,
        )

        # ── 聚合为主视图 ───────────────────────────────────────────
        self._main_dashboard = ft.Container(
            content=ft.Row(
                [
                    _analytics_panel,
                    ft.VerticalDivider(width=1, color=COLOR_ZEN_BG),
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
        )"""

content = re.sub(old_layout_pattern, new_layout.replace('\\', '\\\\'), content, flags=re.DOTALL)


# 2. 替换 _start_scan 和 _reset_to_idle 的面板可见性切换逻辑
content = content.replace("self._idle_panel.visible = False", "self._idle_execution.visible = False")
content = content.replace("self._scanning_panel.visible = True", "self._active_execution.visible = True")
content = content.replace("self._idle_panel.visible = True", "self._idle_execution.visible = True")
content = content.replace("self._scanning_panel.visible = False", "self._active_execution.visible = False")


# 3. 往 did_mount 中切入动画逻辑
did_mount_pattern = r"    def did_mount\(self\):\n        \"\"\"视图挂载到页面时，注册 pubsub 事件监听器。\"\"\"\n        self\.app\.page\.pubsub\.subscribe\(self\._on_pubsub_message\)"
did_mount_replacement = """    def did_mount(self):
        \"\"\"视图挂载到页面时，注册 pubsub 事件监听器。\"\"\"
        self.app.page.pubsub.subscribe(self._on_pubsub_message)
        
        # 执行甜甜圈装载动画
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
                
        self.app.page.run_task(_animate)"""

content = content.replace(
    "    def did_mount(self):\n        \"\"\"视图挂载到页面时，注册 pubsub 事件监听器。\"\"\"\n        self.app.page.pubsub.subscribe(self._on_pubsub_message)",
    did_mount_replacement
)

with open(r"d:\软件开发\ZenClean\src\ui\views\scan_view.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Refactor completed")
