"""
ZenClean 双重分诊清理引擎

执行逻辑（双重分诊策略）：
    LOW    → pathlib.Path.unlink() 物理删除，即时释放本地空间（仅针对于 100% 确认无害的系统级 tmp，其它全部拦截）
    MEDIUM → quarantine() 移入 ZenClean 物理隔离沙箱，保留 72 小时后悔药
    HIGH   → 仅在调用方明确传入 force=True 时才执行 quarantine()（UI 二次确认后）
    CRISIS → 程序级硬拒绝，写 WARNING 日志，不执行任何操作
    UNKNOWN→ 跳过，写 DEBUG 日志

安全闭环：
    1. 每次清理前再次调用 whitelist.assert_safe()，即使 AI 判断有误也能兜底
    2. 使用隔离沙箱机制，大幅降低三方应用被误判导致的服务瘫痪客诉率
    3. 全程用 structlog 记录每条操作（路径、大小、策略、结果）
    4. 统计实际释放/隔离字节数，供 UI 动画回调使用

公开 API：
    result = clean(nodes, on_progress=cb, force_high=False)
    result = empty_recycle_bin()
"""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core import whitelist
from core.quarantine import quarantine
from core.logger import logger


# ── 返回结构 ──────────────────────────────────────────────────────────────────

@dataclass
class CleanResult:
    """单次 clean() 调用的汇总结果，供 UI 展示与动画驱动使用。"""
    total:          int = 0   # 传入节点总数
    deleted:        int = 0   # 物理删除数量（LOW）
    trashed:        int = 0   # 移入回收站数量（MEDIUM/HIGH）
    skipped:        int = 0   # 跳过数量（CRISIS/UNKNOWN/文件不存在）
    failed:         int = 0   # 操作失败数量（权限不足等 OSError）
    freed_bytes:    int = 0   # 物理删除释放的字节数（LOW 层）
    trashed_bytes:  int = 0   # 移入回收站的字节数（MEDIUM/HIGH 层）
    errors:         list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return self.freed_bytes + self.trashed_bytes


# ── 进度回调类型 ──────────────────────────────────────────────────────────────

# on_progress(path, action, freed_bytes_so_far)
ProgressCallback = Callable[[str, str, int], None]


# ── 核心清理函数 ──────────────────────────────────────────────────────────────

def clean(
    nodes: list[dict],
    on_progress: ProgressCallback | None = None,
    force_high: bool = False,
) -> CleanResult:
    """
    对扫描结果列表执行双重分诊清理。

    Args:
        nodes:       list[NodeDict]，来自 scanner/local_engine 的扫描结果。
        on_progress: 每处理一个节点后回调，参数 (path, action, freed_bytes_so_far)。
                     action 取值："deleted" | "trashed" | "skipped" | "blocked" | "failed"
        force_high:  UI 层二次确认弹窗通过后设为 True，才会处理 HIGH 级别条目。
                     默认 False 时 HIGH 被跳过。

    Returns:
        CleanResult 汇总对象。
    """
    result = CleanResult(total=len(nodes))

    for node in nodes:
        path      = node.get("path", "")
        risk      = node.get("risk_level", "UNKNOWN")
        size      = node.get("size_bytes", 0)

        # ── 最终防线：白名单二次核查 ──────────────────────────────────────────
        if whitelist.is_protected(path):
            logger.warning(f"crisis_blocked: path={path}, risk={risk}")
            result.skipped += 1
            if on_progress:
                on_progress(path, "blocked", result.freed_bytes)
            continue

        # ── 按风险等级分诊 ────────────────────────────────────────────────────
        if risk == "LOW":
            action = _physical_delete(path, size, result)
        elif risk == "MEDIUM":
            action = _trash(path, size, result)
        elif risk == "HIGH":
            if force_high:
                action = _trash(path, size, result)
            else:
                logger.debug(f"high_skipped_no_force: path={path}")
                result.skipped += 1
                action = "skipped"
        elif risk == "CRISIS":
            logger.warning(f"crisis_blocked: path={path}, risk={risk}")
            result.skipped += 1
            action = "blocked"
        else:  # UNKNOWN
            logger.debug(f"unknown_skipped: path={path}")
            result.skipped += 1
            action = "skipped"

        if on_progress:
            on_progress(path, action, result.total_bytes)

    logger.info(
        f"clean_complete: deleted={result.deleted}, trashed={result.trashed}, "
        f"skipped={result.skipped}, failed={result.failed}, "
        f"freed_bytes={result.freed_bytes}, trashed_bytes={result.trashed_bytes}"
    )
    return result


# ── 物理删除（LOW） ───────────────────────────────────────────────────────────

def _physical_delete(path: str, size: int, result: CleanResult) -> str:
    """
    对 LOW 级别路径执行物理删除。
    支持删除单个文件或整个目录树（递归）。
    """
    p = Path(path)
    if not p.exists():
        logger.debug(f"not_found_skip: path={path}")
        result.skipped += 1
        return "skipped"

    try:
        if p.is_dir():
            actual_size = _dir_size(p)
            shutil.rmtree(p, ignore_errors=False)
        else:
            actual_size = size or _safe_size(p)
            p.unlink()

        result.deleted += 1
        result.freed_bytes += actual_size
        logger.info(f"deleted: path={path}, bytes={actual_size}")
        return "deleted"

    except OSError as exc:
        result.failed += 1
        result.errors.append(f"DELETE {path}: {exc}")
        logger.error(f"delete_failed: path={path}, error={exc}")
        return "failed"


# ── 移入隔离沙箱（MEDIUM / HIGH force） ────────────────────────────────────────

def _trash(path: str, size: int, result: CleanResult) -> str:
    """
    对 MEDIUM/HIGH(force) 级别路径调用 quarantine 移入禅清隔离沙箱。
    提供 72 小时的反悔和容灾能力。
    """
    p = Path(path)
    if not p.exists():
        logger.debug(f"not_found_skip: path={path}")
        result.skipped += 1
        return "skipped"

    try:
        actual_size = (_dir_size(p) if p.is_dir() else size or _safe_size(p))
        success = quarantine(str(p), actual_size)
        if success:
            result.trashed += 1
            result.trashed_bytes += actual_size
            logger.info(f"quarantined: path={path}, bytes={actual_size}")
            return "trashed"
        else:
            result.failed += 1
            result.errors.append(f"QUARANTINE_FAILED {path}")
            return "failed"

    except Exception as exc:
        result.failed += 1
        result.errors.append(f"QUARANTINE_EXCEPTION {path}: {exc}")
        logger.error(f"quarantine_failed: path={path}, error={exc}")
        return "failed"


# ── 清空回收站 ────────────────────────────────────────────────────────────────

def empty_recycle_bin() -> bool:
    """
    调用 Windows Shell API 彻底清空回收站。
    对应 UI 中的"彻底清空回收站争议项"红色按钮。

    Returns:
        True 表示成功，False 表示失败（已记录日志）。
    """
    try:
        import ctypes
        # SHEmptyRecycleBinW(hwnd=NULL, pszRootPath=NULL, dwFlags=SHERB_NOCONFIRMATION|SHERB_NOPROGRESSUI)
        ret = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x00000001 | 0x00000002)
        if ret == 0 or ret == -2147418113:  # S_OK 或 E_UNEXPECTED（已空）
            logger.info("recycle_bin_emptied")
            return True
        logger.warning(f"recycle_bin_empty_ret: ret={ret}")
        return False
    except Exception as exc:
        logger.error(f"recycle_bin_empty_failed: error={exc}")
        return False


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _safe_size(p: Path) -> int:
    """安全获取文件大小，异常返回 0。"""
    try:
        return p.stat().st_size
    except OSError:
        return 0


def _dir_size(p: Path) -> int:
    """递归计算目录总字节数，跳过无权限项。"""
    total = 0
    try:
        for entry in os.scandir(p):
            try:
                if entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
                else:
                    total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                pass
    except OSError:
        pass
    return total
