"""
ZenClean Queue 消费线程

在主进程（Flet UI 线程）内以独立守护线程运行，
持续从 multiprocessing.Queue 拉取 ScanWorker 推送的批次，
解开批次后逐条触发 UI 回调，并在收到 done/error 哨兵时结束自身。

设计要点：
  - 主线程只需调用 QueueConsumer.start()，所有 Queue 阻塞操作在独立线程内，
    不会卡住 Flet 的事件循环。
  - 回调函数在消费线程内被调用，Flet UI 更新需使用 page.update() 或
    page.run_thread_safe()（调用方责任）。
  - 线程以 daemon=True 运行，主进程退出时自动回收，无需手动 join。

使用方式：
    import multiprocessing
    from core.scanner import ScanWorker
    from core.queue_consumer import QueueConsumer
    from core.logger import logger # 导入 logger

    q = multiprocessing.Queue()

    def on_nodes(nodes):          # 每批结果回调
        for node in nodes:
            logger.info(f"{node['path']}, {node['risk_level']}") # 使用 logger.info

    def on_done(total, skipped):  # 扫描完成回调
        logger.info(f"完成：共 {total} 个文件，跳过 {skipped} 个") # 使用 logger.info

    def on_error(message):        # 错误回调
        logger.error(f"扫描出错：{message}") # 使用 logger.error

    consumer = QueueConsumer(q, on_nodes=on_nodes, on_done=on_done, on_error=on_error)
    worker = ScanWorker(q)

    consumer.start()
    worker.start()
"""

import threading
from typing import Callable

from config.settings import QUEUE_POLL_INTERVAL


class QueueConsumer(threading.Thread):
    """
    主进程侧 Queue 消费线程。

    Args:
        q:         与 ScanWorker 共享的 multiprocessing.Queue。
        on_nodes:  批量结果回调，参数为 list[NodeDict]。
        on_done:   扫描完成回调，参数为 (total: int, skipped: int)。
        on_error:  扫描错误回调，参数为 (message: str)。
    """

    def __init__(
        self,
        q,
        on_nodes: Callable[[list], None],
        on_done: Callable[[int, int], None],
        on_error: Callable[[str], None],
    ):
        super().__init__(daemon=True, name="ZenClean-QueueConsumer")
        self._queue = q
        self._on_nodes = on_nodes
        self._on_done = on_done
        self._on_error = on_error
        self._stop_event = threading.Event()

    # ── 线程入口 ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        """持续轮询 Queue，直到收到哨兵或外部请求停止。"""
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=QUEUE_POLL_INTERVAL)
            except Exception:   # queue.Empty 及其他超时异常
                continue

            # ── 哨兵判断 ──────────────────────────────────────────────────────
            if isinstance(item, dict) and "type" in item:
                if item["type"] == "done":
                    self._on_done(item.get("total", 0), item.get("skipped", 0))
                    break
                elif item["type"] == "error":
                    self._on_error(item.get("message", "未知错误"))
                    break
                # 未知哨兵类型，忽略继续
                continue

            # ── 正常批次（list[NodeDict]）─────────────────────────────────────
            if isinstance(item, list) and item:
                self._on_nodes(item)

    def stop(self) -> None:
        """外部请求提前终止消费循环（如用户手动取消扫描）。"""
        self._stop_event.set()
