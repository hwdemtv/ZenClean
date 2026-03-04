"""
ZenClean IPC 并发扫描引擎

架构：
    主进程 (Flet UI)
        └── ScanWorker (multiprocessing.Process)   ← 独立子进程，绕开 GIL
                ├── os.walk 遍历目标目录
                ├── whitelist.is_protected() 目录剪枝
                ├── Junction/Symlink 防死锁检测
                ├── 隐藏/系统文件过滤
                ├── local_engine.dispatch() 风险评估
                └── Queue.put(batch)  每 SCAN_BATCH_SIZE 条打包推送

主进程通过 QueueConsumer（见 core/queue_consumer.py）消费结果。

Queue 消息格式：
    正常批次：list[NodeDict]          — 扫描结果批次
    结束哨兵：{"type": "done", "total": int, "skipped": int}
    错误哨兵：{"type": "error", "message": str}

使用方式：
    worker = ScanWorker(queue, root=Path("C:\\"))
    worker.start()
    # 主进程侧开启 QueueConsumer 消费
"""

import multiprocessing
import os
from pathlib import Path

from config.settings import SCAN_BATCH_SIZE, SCAN_TARGETS
from core import whitelist
from ai import local_engine


# Windows 文件属性标志（来自 WinAPI）
_FILE_ATTRIBUTE_HIDDEN = 0x2
_FILE_ATTRIBUTE_SYSTEM = 0x4
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400   # Junction / Symlink / Mount Point


def _is_junction_or_symlink(entry: os.DirEntry) -> bool:
    """
    检测目录项是否为 Junction Point、Symlink 或其他重解析点。
    os.path.islink() 在 Windows 上对 Junction 返回 False，
    必须结合 stat 的 FILE_ATTRIBUTE_REPARSE_POINT 属性判断。
    """
    # 普通 symlink（Python 可识别）
    if entry.is_symlink():
        return True
    # Junction / Mount Point（仅 Windows）
    try:
        attrs = entry.stat(follow_symlinks=False).st_file_attributes
        return bool(attrs & _FILE_ATTRIBUTE_REPARSE_POINT)
    except (OSError, AttributeError):
        return False


def _is_hidden_or_system(entry: os.DirEntry) -> bool:
    """
    检测文件/目录是否带有 HIDDEN 或 SYSTEM 属性。
    跳过此类项可避免扫描到无权限的系统文件并引发异常风暴。
    仅在 Windows 上有效；非 Windows 平台始终返回 False。
    """
    try:
        attrs = entry.stat(follow_symlinks=False).st_file_attributes
        return bool(attrs & (_FILE_ATTRIBUTE_HIDDEN | _FILE_ATTRIBUTE_SYSTEM))
    except (OSError, AttributeError):
        return False


def _get_size(entry: os.DirEntry) -> int:
    """安全获取文件大小，异常时返回 0。"""
    try:
        return entry.stat(follow_symlinks=False).st_size
    except OSError:
        return 0


class ScanWorker(multiprocessing.Process):
    """
    独立子进程扫描引擎（靶向模式）。

    不再全盘遍历 C 盘。只依次对 settings.SCAN_TARGETS 中列出的
    已知垃圾/缓存热区目录进行深度 walk，大幅提升速度与精准度。

    Args:
        queue:      与主进程通信的 multiprocessing.Queue。
        targets:    靶向目录列表，默认为 settings.SCAN_TARGETS。
        skip_hidden: 是否跳过隐藏/系统文件，默认 True。
    """

    def __init__(
        self,
        queue: multiprocessing.Queue,
        targets: list[Path] | None = None,
        skip_hidden: bool = True,
    ):
        super().__init__(daemon=True, name="ZenClean-ScanWorker")
        self._queue = queue
        self._targets = targets or SCAN_TARGETS
        self._skip_hidden = skip_hidden

    # ── 子进程入口 ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """子进程主循环。所有异常都捕获后通过 error 哨兵告知主进程。"""
        try:
            self._scan()
        except Exception as exc:  # noqa: BLE001
            self._queue.put({"type": "error", "message": str(exc)})

    def _scan(self) -> None:
        batch: list[dict] = []
        total = 0
        skipped = 0

        for target in self._targets:
            # 跳过不存在的目录（用户可能未安装 Chrome/Firefox 等）
            target_str = str(target)
            if not os.path.isdir(target_str):
                continue

            for root_str, dirs, files in os.walk(
                target_str, topdown=True, followlinks=False, onerror=None
            ):
                # ── 目录级过滤（就地修改 dirs，阻止 os.walk 递归进入） ──────

                filtered_dirs: list[str] = []
                for d in dirs:
                    # 0. 目录名快速过滤（过滤 WebCache、WebView2 等海量且锁死区）
                    if whitelist.is_ignored_dir_name(d):
                        skipped += 1
                        continue

                    dir_path = os.path.join(root_str, d)

                    # 1. 白名单目录剪枝
                    if whitelist.is_protected(dir_path):
                        skipped += 1
                        continue

                    # 2. Junction / Symlink / Mount Point 防死锁
                    try:
                        entry_stat = os.stat(dir_path, follow_symlinks=False)
                        attrs = getattr(entry_stat, "st_file_attributes", 0)
                        if attrs & _FILE_ATTRIBUTE_REPARSE_POINT:
                            skipped += 1
                            continue
                    except OSError:
                        skipped += 1
                        continue

                    # 3. 隐藏/系统目录跳过
                    if self._skip_hidden:
                        try:
                            attrs = getattr(
                                os.stat(dir_path, follow_symlinks=False),
                                "st_file_attributes", 0
                            )
                            if attrs & (_FILE_ATTRIBUTE_HIDDEN | _FILE_ATTRIBUTE_SYSTEM):
                                skipped += 1
                                continue
                        except OSError:
                            pass

                    filtered_dirs.append(d)

                dirs[:] = filtered_dirs

                # ── 文件级处理 ────────────────────────────────────────────────
                for fname in files:
                    fpath = os.path.join(root_str, fname)

                    # 白名单文件名防线
                    if whitelist.is_protected(fpath):
                        skipped += 1
                        continue

                    # 隐藏/系统文件跳过
                    if self._skip_hidden:
                        try:
                            attrs = getattr(
                                os.stat(fpath, follow_symlinks=False),
                                "st_file_attributes", 0
                            )
                            if attrs & (_FILE_ATTRIBUTE_HIDDEN | _FILE_ATTRIBUTE_SYSTEM):
                                skipped += 1
                                continue
                        except OSError:
                            pass

                    # 获取文件大小
                    try:
                        size = os.stat(fpath, follow_symlinks=False).st_size
                    except OSError:
                        size = 0

                    # AI 引擎评估
                    try:
                        node = local_engine.dispatch(fpath, size_bytes=size)
                    except Exception:  # noqa: BLE001
                        skipped += 1
                        continue

                    batch.append(node)
                    total += 1

                    # 达到批次阈值，推入 Queue
                    if len(batch) >= SCAN_BATCH_SIZE:
                        self._queue.put(batch)
                        batch = []

        # 推送最后一批（不足 SCAN_BATCH_SIZE 的尾部）
        if batch:
            self._queue.put(batch)

        # 推送结束哨兵
        self._queue.put({"type": "done", "total": total, "skipped": skipped})
