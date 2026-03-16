"""
ZenClean 后台扫描引擎 (线程版)

架构：
    主进程 (Flet UI)
        └── ScanWorker (threading.Thread)   ← 后台线程，避免 Windows Spawn 阻塞
                ├── os.walk 遍历目标目录
                ├── whitelist.is_protected() 目录剪枝
                ├── Junction/Symlink 防死锁检测
                ├── 隐藏/系统文件过滤
                ├── local_engine.dispatch() 风险评估
                └── callback(batch)  每 SCAN_BATCH_SIZE 条触发分发回调
"""

import os
import time
import threading
from typing import Callable, Any
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


class ScanWorker(threading.Thread):
    """
    独立后台扫描引擎（线程版）。

    不再全盘遍历 C 盘。只依次对 settings.SCAN_TARGETS 中列出的
    已知垃圾/缓存热区目录进行深度 walk，大幅提升速度与精准度。

    Args:
        on_nodes:   每批次扫描结果回调。
        on_done:    扫描完成回调。
        on_error:   发生错误时的回调。
        targets:    靶向目录列表，默认为 settings.SCAN_TARGETS。
        skip_hidden: 是否跳过隐藏/系统文件，默认 True。
    """

    def __init__(
        self,
        on_nodes: Callable[[list[dict]], None],
        on_done: Callable[[int, int], None],
        on_error: Callable[[str], None],
        targets: list[Path] | None = None,
        skip_hidden: bool = True,
    ):
        super().__init__(daemon=True, name="ZenClean-ScanThread")
        self._on_nodes = on_nodes
        self._on_done = on_done
        self._on_error = on_error
        self._targets = targets or SCAN_TARGETS
        self._skip_hidden = skip_hidden
        self._stop_event = threading.Event()

    # ── 线程入口 ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """主循环。所有异常都捕获后通过 error 哨兵告知主进程。"""
        try:
            self._scan()
        except Exception as exc:  # noqa: BLE001
            self._on_error(str(exc))
            
    def stop(self) -> None:
        """请求停止扫描。设置停止标志，但仍会触发 _on_done 回调以更新 UI 状态。"""
        self._stop_event.set()

    def _should_skip_for_hidden(self, path: str) -> bool:
        """条件性跳过隐藏文件，保留特定例外（如回收站和明确指示的缓存）"""
        if not self._skip_hidden:
            return False

        try:
            attrs = os.stat(path, follow_symlinks=False).st_file_attributes
            is_hidden = attrs & _FILE_ATTRIBUTE_HIDDEN
            is_system = attrs & _FILE_ATTRIBUTE_SYSTEM

            if not (is_hidden or is_system):
                return False

            path_lower = path.lower()
            # 例外：回收站内的文件不应跳过
            if r"$recycle.bin" in path_lower:
                return False

            # 例外：Temp 目录下的隐藏文件可能是垃圾
            if r"\temp\\" in path_lower or path_lower.endswith(r"\temp"):
                return False

            # 例外：已知的缓存目录
            cache_indicators = ["cache", "tmp", "cached"]
            if any(ind in path_lower.split(os.sep) for ind in cache_indicators):
                return False

            return True
        except OSError:
            return True

    def _scan(self) -> None:
        batch: list[dict] = []
        total = 0
        skipped = 0

        for target in self._targets:
            # 检查停止标志
            if self._stop_event.is_set():
                break

            # 跳过不存在的目录（用户可能未安装 Chrome/Firefox 等）
            target_str = str(target)
            if not os.path.isdir(target_str):
                continue

            for root_str, dirs, files in os.walk(
                target_str, topdown=True, followlinks=False, onerror=None
            ):
                # 检查停止标志（每个目录层级检查）
                if self._stop_event.is_set():
                    break

                # ── 目录级过滤（就地修改 dirs，阻止 os.walk 递归进入） ──────

                filtered_dirs: list[str] = []
                for d in dirs:
                    dir_path = os.path.join(root_str, d)

                    # 0. 目录名条件化过滤（避免完全封杀浏览器的大数据缓存区）
                    if whitelist.should_skip_dir(dir_path, d):
                        skipped += 1
                        continue

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

                    # 3. 隐藏/系统目录条件化跳过（不过分苛刻）
                    if self._should_skip_for_hidden(dir_path):
                        skipped += 1
                        continue

                    filtered_dirs.append(d)

                dirs[:] = filtered_dirs

                # ── 文件级处理 ────────────────────────────────────────────────
                for fname in files:
                    fpath = os.path.join(root_str, fname)

                    # 白名单文件名防线
                    if whitelist.is_protected(fpath):
                        skipped += 1
                        continue

                    # 隐藏/系统文件条件化跳过（防止误杀大量被设为隐藏格式但本属垃圾的缓存）
                    if self._should_skip_for_hidden(fpath):
                        skipped += 1
                        continue

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

                    # 达到批次阈值，推入回调
                    if len(batch) >= SCAN_BATCH_SIZE:
                        self._on_nodes(batch)
                        batch = []

        # 推送最后一批（不足 SCAN_BATCH_SIZE 的尾部）
        if batch:
            self._on_nodes(batch)

        # 推送结束哨兵（无论扫描是否被主动停止，都需要通知 UI 更新状态）
        self._on_done(total, skipped)
