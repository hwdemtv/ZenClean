import multiprocessing
import threading
import shutil
import flet as ft

from core.scanner import ScanWorker
from core.queue_consumer import QueueConsumer
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
        self.app = app
        self._worker: ScanWorker | None = None
        self._consumer: QueueConsumer | None = None

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
            bgcolor="#2A2A2A",
            padding=10,
            border_radius=5,
            visible=not app.is_activated,
        )

        # ── 扫描按钮（idle 态） ───────────────────────────────────────────────
        self._scan_btn = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.MANAGE_SEARCH_ROUNDED, size=60, color="white"),
                    ft.Text("点击开始扫描 C 盘", size=20, weight=ft.FontWeight.BOLD, color="white"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=200, height=200,
            border_radius=100,
            bgcolor=COLOR_ZEN_PRIMARY,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.colors.with_opacity(0.2, COLOR_ZEN_PRIMARY)),
            ink=True,
            on_click=self._start_scan,
        )

        # ── 扫描中状态控件 ────────────────────────────────────────────────────
        self._status_text = ft.Text("正在初始化扫描引擎...", color=COLOR_ZEN_TEXT_DIM, size=13)
        self._counter_text = ft.Text("已发现 0 个文件", size=28,
                                     weight=ft.FontWeight.BOLD, color=COLOR_ZEN_PRIMARY)
        self._size_text = ft.Text("可释放空间：计算中...", color=COLOR_ZEN_TEXT_DIM, size=14)
        self._progress = ft.ProgressBar(
            width=400, color=COLOR_ZEN_PRIMARY, bgcolor="#333333", visible=False
        )
        self._cancel_btn = ft.TextButton(
            "取消扫描", on_click=self._cancel_scan, visible=False, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)
        )

        self._done_btn = ft.ElevatedButton(
            "点击揭晓扫描结果",
            icon=ft.icons.ROCKET_LAUNCH,
            bgcolor=COLOR_ZEN_PRIMARY,
            color="white",
            height=50,
            on_click=lambda _: self.app.navigate_to("/result"),
            visible=False
        )

        self._scanning_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.RADAR, size=60, color=COLOR_ZEN_PRIMARY),
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

        # AI 通道额度展示（闲置态独有）
        self._quota_label = ft.Text("AI 引擎参数初始化...", color=COLOR_ZEN_PRIMARY, size=13, weight=ft.FontWeight.BOLD, visible=False)

        # ── 主仪表盘（idle 态外壳） ───────────────────────────────────────────
        self._idle_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("系统深度体检", size=32, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Text(
                        "通过本地 Rule Engine 与双重粉碎法，安全释放您的磁盘空间",
                        color=COLOR_ZEN_TEXT_DIM,
                    ),
                    ft.Container(
                        content=ft.Text(f"C 盘空间：可用 {free_gb:.1f} GB / 共 {total_gb:.1f} GB", color=COLOR_ZEN_PRIMARY),
                        margin=ft.margin.only(top=10, bottom=5),
                        padding=ft.padding.all(10),
                        bgcolor="#252525",
                        border_radius=8,
                    ),
                    self._quota_label,
                    ft.Container(height=10),
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
                    self._quota_label.value = f"✨ 智能体检引擎在线 · 今日已消耗: {used} / 共 {limit} 次"
                    self._quota_label.color = COLOR_ZEN_PRIMARY
                    if self.page:
                        self.update()
            
            self.app.page.run_task(_fetch_quota)

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

            # 自动跳转：停留 1 秒让用户看清最终统计结果
            if self.page:
                import threading
                import time
                def _auto_nav():
                    time.sleep(1.2)
                    if self.page:
                        self.app.navigate_to("/result")
                threading.Thread(target=_auto_nav, daemon=True).start()

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
