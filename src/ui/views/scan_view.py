import multiprocessing
import threading
import shutil
import flet as ft

from core.scanner import ScanWorker
from core.queue_consumer import QueueConsumer


# 风险等级 → 徽章颜色
_RISK_COLOR = {
    "LOW":     "#00C853",
    "MEDIUM":  "#FFD600",
    "HIGH":    "#FF6D00",
    "CRISIS":  "#B0BEC5",
    "UNKNOWN": "#546E7A",
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
    状态机：idle → scanning → done（跳转结果页）
    """

    def __init__(self, app):
        self.app = app
        self._worker: ScanWorker | None = None
        self._consumer: QueueConsumer | None = None

        # ── 未激活横幅 ────────────────────────────────────────────────────────
        self._activation_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.INFO_OUTLINE, color=ft.colors.YELLOW_600),
                ft.Text(
                    "当前为标准体验版，仅可手动勾选风险项。成为 VIP 解锁【AI智能引擎】与【一键物理清除】。",
                    expand=True,
                ),
                ft.TextButton("去激活", on_click=lambda _: self.app.navigate_to("/auth")),
            ]),
            bgcolor="#332B00",
            padding=10,
            border_radius=5,
            visible=not app.is_activated,
        )

        # ── 扫描按钮（idle 态） ───────────────────────────────────────────────
        self._scan_btn = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.MANAGE_SEARCH_ROUNDED, size=60, color="white"),
                    ft.Text("点击开始扫描 C 盘", size=20, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=200, height=200,
            border_radius=100,
            bgcolor="#00D4AA",
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="#00D4AA"),
            ink=True,
            on_click=self._start_scan,
        )

        # ── 扫描中状态控件 ────────────────────────────────────────────────────
        self._status_text = ft.Text("正在初始化扫描引擎...", color="#AAAAAA", size=13)
        self._counter_text = ft.Text("已发现 0 个文件", size=28,
                                     weight=ft.FontWeight.BOLD, color="#00D4AA")
        self._size_text = ft.Text("可释放空间：计算中...", color="#AAAAAA", size=14)
        self._progress = ft.ProgressBar(
            width=400, color="#00D4AA", bgcolor="#333333", visible=False
        )
        self._cancel_btn = ft.TextButton(
            "取消扫描", on_click=self._cancel_scan, visible=False
        )

        self._done_btn = ft.ElevatedButton(
            "点击揭晓扫描结果",
            icon=ft.icons.ROCKET_LAUNCH,
            bgcolor="#00D4AA",
            color="white",
            height=50,
            on_click=lambda _: self.app.navigate_to("/result"),
            visible=False
        )

        self._scanning_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.RADAR, size=60, color="#00D4AA"),
                    self._counter_text,
                    self._size_text,
                    ft.Container(height=10),
                    self._progress,
                    self._status_text,
                    self._cancel_btn,
                    self._done_btn,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            alignment=ft.alignment.center,
            expand=True,
            visible=False,
        )


        # 获取 C 盘容量
        total, used, free = shutil.disk_usage("C:\\")
        total_gb = total / (1024**3)
        free_gb = free / (1024**3)
        used_gb = total_gb - free_gb

        # ── 主仪表盘（idle 态外壳） ───────────────────────────────────────────
        self._idle_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("系统深度体检", size=32, weight=ft.FontWeight.W_800),
                    ft.Text(
                        "通过本地 Rule Engine 与双重粉碎法，安全释放您的磁盘空间",
                        color="#AAAAAA",
                    ),
                    ft.Container(
                        content=ft.Text(f"C 盘空间：可用 {free_gb:.1f} GB / 共 {total_gb:.1f} GB", color=ft.colors.CYAN_400),
                        margin=ft.margin.only(top=10, bottom=20),
                        padding=ft.padding.all(10),
                        bgcolor="#1E1E1E",
                        border_radius=8,
                    ),
                    self._scan_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

        super().__init__(
            controls=[
                self._activation_banner,
                self._idle_panel,
                self._scanning_panel,
            ],
            expand=True,
        )

    # ── 扫描启动 ──────────────────────────────────────────────────────────────

    def _start_scan(self, e) -> None:
        """切换到 scanning 态，启动 ScanWorker + QueueConsumer。"""
        # 清空上次扫描结果
        self.app.scan_nodes.clear()
        self.app.page.pubsub.send_all({"type": "scan_nodes", "nodes": []})

        # 切换面板
        self._idle_panel.visible = False
        self._scanning_panel.visible = True
        self._progress.visible = True
        self._cancel_btn.visible = True
        self._done_btn.visible = False
        self._status_text.value = "正在扫描 C 盘..."
        self.update()

        # 启动 IPC
        q: multiprocessing.Queue = multiprocessing.Queue()

        self._consumer = QueueConsumer(
            q,
            on_nodes=self._on_nodes_th,
            on_done=self._on_done_th,
            on_error=self._on_error_th,
        )
        self._worker = ScanWorker(q)
        self._consumer.start()
        self._worker.start()

    # ── 取消扫描 ──────────────────────────────────────────────────────────────

    def _cancel_scan(self, e) -> None:
        if self._consumer:
            self._consumer.stop()
        if self._worker and self._worker.is_alive():
            self._worker.terminate()
        self._reset_to_idle()

    def _reset_to_idle(self) -> None:
        self._idle_panel.visible = True
        self._scanning_panel.visible = False
        self._progress.visible = False
        self._cancel_btn.visible = False
        self._done_btn.visible = False
        self.update()

    # ── QueueConsumer 回调（在消费线程中执行，必须使用异步方式调度到主线程安全执行） ──

    def did_mount(self):
        """视图挂载到页面时，注册 pubsub 事件监听器。"""
        self.app.page.pubsub.subscribe(self._on_pubsub_message)

    def will_unmount(self):
        """视图被卸载时，移除挂载的监听器，防止内存泄漏。"""
        self.app.page.pubsub.unsubscribe()

    def _on_pubsub_message(self, message: dict) -> None:
        """接收来自于消费线程广播的安全 UI 刷新指令。此方法已在主线程上下文中被调度"""
        msg_type = message.get("type", "")

        if msg_type == "scan_nodes":
            nodes = message.get("nodes", [])
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
            self.update()

        elif msg_type == "scan_done":
            total = message.get("total", 0)
            skipped = message.get("skipped", 0)
            self._status_text.value = f"扫描完成，共 {total:,} 个文件，跳过 {skipped:,} 个"
            self._progress.visible = False
            self._cancel_btn.visible = False
            self._done_btn.visible = True
            self.update()
            
            # 使用 Flet 官方标准的 run_task 投递一个纯异步任务，规避生命周期死锁
            async def _delayed_nav():
                import asyncio
                await asyncio.sleep(0.5)
                self.app.navigate_to("/result")
            self.app.page.run_task(_delayed_nav)

        elif msg_type == "scan_error":
            err = message.get("message", "未知错误")
            self._status_text.value = f"扫描出错：{err}"
            self._progress.visible = False
            self._cancel_btn.visible = False
            self._done_btn.visible = True
            self.update()

    # ── 丢弃过时的强同步回调（改用下发的 pubsub 推送方案） ────────────────
    def _on_nodes_th(self, nodes: list[dict]) -> None:
        self.app.page.pubsub.send_all({"type": "scan_nodes", "nodes": nodes})

    def _on_done_th(self, total: int, skipped: int) -> None:
        self.app.page.pubsub.send_all({"type": "scan_done", "total": total, "skipped": skipped})

    def _on_error_th(self, message: str) -> None:
        self.app.page.pubsub.send_all({"type": "scan_error", "message": message})
