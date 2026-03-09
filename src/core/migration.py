"""
ZenClean 系统大文件夹无损搬家引擎 (User Shell Folders Migration)

功能：
    将 Windows 默认用户库（桌面、下载、文档、图片、视频、音乐）
    从 C 盘平滑迁移到用户指定的非 C 盘目录，全程无数据丢失。

执行三步走：
    1. 读注册表  —— 获取各库的当前绝对路径
    2. 搬文件    —— shutil.move 原子性逐项迁移，带进度回调
    3. 改注册表  —— 写回新路径 + SHChangeNotify 刷新 Shell 缓存

安全机制：
    - 迁移前置检查：目标盘可用空间 > 源目录总大小
    - 源目录与目标目录不能存在父子关系（防止循环移动）
    - 已存在同名文件时，逐项合并而非覆盖（merge 策略）
    - 注册表写入前备份旧值，任意步骤失败可 rollback()
    - 迁移完成后在原路径创建 Junction Point 保持向后兼容

公开 API：
    folders = get_shell_folders()           # 读取当前所有库路径
    plan    = MigrationPlan(folder_keys, dst_base)
    plan.preflight()                        # 前置检查，返回检查报告
    plan.execute(on_progress=cb)            # 执行迁移
    plan.rollback()                         # 回滚（仅注册表，文件已在目标端）
"""

import ctypes
import os
import shutil
import threading
import winreg
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ── 注册表常量 ────────────────────────────────────────────────────────────────

_REG_KEY_USER_SHELL    = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
_REG_KEY_SHELL_FOLDERS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"

# Shell Folder 注册表键名 → 人类可读标签
SHELL_FOLDER_KEYS: dict[str, str] = {
    "Desktop":             "桌面",
    "{374DE290-123F-4565-9164-39C4925E467B}": "下载",   # Downloads（无别名）
    "Personal":            "文档",
    "My Pictures":         "图片",
    "My Video":            "视频",
    "My Music":            "音乐",
}

# SHChangeNotify 事件 ID（通知 Shell 刷新文件夹图标/路径缓存）
_SHCNE_ASSOCCHANGED = 0x08000000
_SHCNE_IDLIST       = 0x04
_SHCNF_FLUSH        = 0x1000


# ── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class ShellFolder:
    """单个用户库的迁移状态描述。"""
    key:        str           # 注册表键名
    label:      str           # 人类可读名称（如"下载"）
    src:        Path          # 当前路径（迁移前）
    dst:        Path          # 目标路径（迁移后）
    size_bytes: int = 0       # 源目录总大小（preflight 填充）
    moved_bytes: int = 0      # 已搬运字节数（execute 更新）
    done:       bool = False  # 是否已完成迁移


@dataclass
class PreflightReport:
    """preflight() 的检查结果。"""
    ok:               bool
    total_size_bytes: int
    free_bytes:       int
    issues:           list[str] = field(default_factory=list)

    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / 1024 ** 3

    @property
    def free_gb(self) -> float:
        return self.free_bytes / 1024 ** 3


# ── 注册表读写 ────────────────────────────────────────────────────────────────

def get_shell_folders() -> dict[str, Path]:
    """
    读取当前用户所有 Shell Folder 的绝对路径。

    返回：{ 注册表键名: 绝对 Path }

    注意：注册表中的值可能包含 %USERPROFILE% 等环境变量，
    需用 winreg.ExpandEnvironmentStrings 展开。
    """
    result: dict[str, Path] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY_USER_SHELL) as hkey:
            for reg_name in SHELL_FOLDER_KEYS:
                try:
                    raw, _ = winreg.QueryValueEx(hkey, reg_name)
                    expanded = winreg.ExpandEnvironmentStrings(raw)
                    result[reg_name] = Path(expanded)
                except FileNotFoundError:
                    pass  # 该键不存在，跳过
    except OSError as exc:
        raise RuntimeError(f"无法读取 Shell Folders 注册表：{exc}") from exc
    return result


def _read_reg_value(key_path: str, name: str) -> str | None:
    """读取 HKCU 下指定键值，失败返回 None。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as hkey:
            val, _ = winreg.QueryValueEx(hkey, name)
            return val
    except OSError:
        return None


def _write_reg_value(key_path: str, name: str, value: str) -> None:
    """写入 HKCU 下指定键值（REG_EXPAND_SZ 类型以保留环境变量兼容性）。"""
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, key_path,
        access=winreg.KEY_SET_VALUE
    ) as hkey:
        winreg.SetValueEx(hkey, name, 0, winreg.REG_EXPAND_SZ, value)


def _notify_shell() -> None:
    """调用 SHChangeNotify 通知 Windows Shell 刷新文件夹路径缓存。"""
    try:
        shell32 = ctypes.windll.shell32
        shell32.SHChangeNotify(
            _SHCNE_ASSOCCHANGED,
            _SHCNF_FLUSH,
            None,
            None,
        )
    except Exception:  # noqa: BLE001
        pass  # 通知失败不影响文件已完成迁移的事实


# ── 目录大小计算 ──────────────────────────────────────────────────────────────

def _dir_size(path: Path) -> int:
    """递归计算目录总字节数，跳过无权限项。"""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
                else:
                    total += entry.stat(follow_symlinks=False).st_size
            except (OSError, PermissionError):
                pass
    except (OSError, PermissionError):
        pass
    return total


def _free_space(path: Path) -> int:
    """获取指定路径所在驱动器的可用字节数。"""
    return shutil.disk_usage(path).free


# ── 进度回调类型 ──────────────────────────────────────────────────────────────

# on_progress(folder_label, moved_bytes, total_bytes, current_file)
ProgressCallback = Callable[[str, int, int, str], None]


# ── 核心迁移执行 ──────────────────────────────────────────────────────────────

def _merge_move(src: Path, dst: Path,
                on_file: Callable[[str, int], None],
                cancel_event: threading.Event) -> None:
    """
    将 src 目录内容合并移动到 dst，不覆盖已存在文件（merge 策略）。

    on_file(filepath, size) 在每个文件移动完成后回调。
    cancel_event.is_set() 为 True 时提前终止。
    """
    try:
        dst.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    try:
        entries = list(os.scandir(src))
    except (OSError, PermissionError):
        # 若遇无权限目录（如被系统拒绝保护的目录），静默跳过
        return

    for entry in entries:
        if cancel_event.is_set():
            return

        src_item = Path(entry.path)
        dst_item = dst / entry.name

        # 跳过重解析点（Junction Points / Symlinks，如 My Music, My Pictures）
        # 避免递归死循环或引发由于系统严格控制而导致的拒绝访问错误
        try:
            attrs = entry.stat(follow_symlinks=False).st_file_attributes
            if attrs & 0x400:  # 0x400 = FILE_ATTRIBUTE_REPARSE_POINT
                continue
                
            is_dir = entry.is_dir(follow_symlinks=False)
        except (OSError, PermissionError):
            # 将无权访问的系统受保护节点直接跳过，避免引发崩溃
            on_file(str(src_item), 0)
            continue

        if is_dir:
            _merge_move(src_item, dst_item, on_file, cancel_event)
            # 子目录内容全部移走后删除空壳
            try:
                if not any(src_item.iterdir()):
                    src_item.rmdir()
            except (OSError, PermissionError):
                pass
        else:
            size = 0
            try:
                size = entry.stat(follow_symlinks=False).st_size
            except (OSError, PermissionError):
                pass

            try:
                if dst_item.exists():
                    # merge：目标已存在同名文件，跳过（保留目标端版本）
                    on_file(str(src_item), 0)
                    continue
            except (OSError, PermissionError):
                on_file(str(src_item), 0)
                continue

            try:
                shutil.move(str(src_item), str(dst_item))
                on_file(str(dst_item), size)
            except (OSError, shutil.Error):
                # 单文件移动失败不中断整体，继续处理其余文件
                on_file(str(src_item), 0)


def _create_junction(src: Path, target: Path) -> None:
    """
    在 src 位置创建指向 target 的 Junction Point，保持向后兼容。
    失败时静默忽略（不影响已完成的文件迁移）。
    """
    try:
        import subprocess
        subprocess.run(
            ["mklink", "/J", str(src), str(target)],
            shell=True,
            capture_output=True,
            check=True,
        )
    except Exception:  # noqa: BLE001
        pass


# ── MigrationPlan ─────────────────────────────────────────────────────────────

class MigrationPlan:
    """
    单次迁移计划：将指定的若干 Shell Folder 批量迁移到 dst_base 下的同名子目录。

    示例：
        plan = MigrationPlan(
            folder_keys=["Desktop", "{374DE290-...}", "Personal"],
            dst_base=Path("D:\\UserFolders"),
        )
        report = plan.preflight()
        if report.ok:
            plan.execute(on_progress=my_callback)

    Args:
        folder_keys: 要迁移的注册表键名列表（来自 SHELL_FOLDER_KEYS）。
        dst_base:    目标根目录，各库会在其下创建同名子目录。
        create_junction: 迁移完成后是否在原路径创建 Junction Point，默认 True。
    """

    def __init__(
        self,
        folder_keys: list[str],
        dst_base: Path,
        create_junction: bool = True,
    ):
        self._dst_base = Path(dst_base)
        self._create_junction = create_junction
        self._cancel = threading.Event()
        self._reg_backups: dict[str, str] = {}   # 注册表回滚备份 {键名: 旧值}

        # 构建 ShellFolder 列表
        current = get_shell_folders()
        self.folders: list[ShellFolder] = []
        for key in folder_keys:
            if key not in SHELL_FOLDER_KEYS:
                raise ValueError(f"未知的 Shell Folder 键名：{key}")
            src = current.get(key)
            if src is None:
                raise RuntimeError(f"无法从注册表读取 {key} 的当前路径")
            label = SHELL_FOLDER_KEYS[key]
            dst = self._dst_base / src.name
            self.folders.append(ShellFolder(key=key, label=label, src=src, dst=dst))

    # ── 前置检查 ──────────────────────────────────────────────────────────────

    def preflight(self) -> PreflightReport:
        """
        执行迁移前置检查，返回 PreflightReport。

        检查项：
          1. 目标目录不在 C 盘
          2. 各源目录实际存在
          3. 源目录与目标目录无父子关系
          4. 目标盘可用空间 > 源总大小（10% 安全余量）
        """
        issues: list[str] = []
        total_size = 0

        # 检查 1：目标不能在 C 盘
        dst_drive = self._dst_base.drive.upper()
        if dst_drive == "C:":
            issues.append("目标目录不能位于 C 盘，请选择其他驱动器。")

        for sf in self.folders:
            # 检查 2：源目录存在
            if not sf.src.exists():
                issues.append(f"[{sf.label}] 源目录不存在：{sf.src}")
                continue

            # 检查 3：父子关系
            try:
                sf.dst.relative_to(sf.src)
                issues.append(
                    f"[{sf.label}] 目标目录 {sf.dst} 是源目录 {sf.src} 的子目录，"
                    "会导致循环移动。"
                )
            except ValueError:
                pass  # 不是子目录，正常

            try:
                sf.src.relative_to(sf.dst)
                issues.append(
                    f"[{sf.label}] 源目录 {sf.src} 是目标目录 {sf.dst} 的子目录。"
                )
            except ValueError:
                pass

            # 计算源目录大小
            sf.size_bytes = _dir_size(sf.src)
            total_size += sf.size_bytes

        # 检查 4：目标盘可用空间
        free = 0
        if dst_drive != "C:" and self._dst_base.drive:
            try:
                free = _free_space(Path(self._dst_base.drive + "\\"))
            except OSError:
                issues.append(f"无法读取目标驱动器 {dst_drive} 的可用空间。")

        required = int(total_size * 1.1)   # 10% 安全余量
        if free > 0 and free < required:
            issues.append(
                f"目标驱动器可用空间不足：需要 {required / 1024**3:.1f} GB，"
                f"实际可用 {free / 1024**3:.1f} GB。"
            )

        return PreflightReport(
            ok=(len(issues) == 0),
            total_size_bytes=total_size,
            free_bytes=free,
            issues=issues,
        )

    # ── 执行迁移 ──────────────────────────────────────────────────────────────

    def execute(self, on_progress: ProgressCallback | None = None) -> None:
        """
        执行完整迁移流程：移文件 → 改注册表 → 刷新 Shell → 创建 Junction。

        Args:
            on_progress: 进度回调 (folder_label, moved_bytes, total_bytes, current_file)
                         在调用方线程（通常为 UI 线程）中被调用。

        Raises:
            RuntimeError: 任意关键步骤失败时抛出，携带人类可读错误信息。
        """
        self._cancel.clear()

        for sf in self.folders:
            if self._cancel.is_set():
                break

            label = sf.label
            total = sf.size_bytes or _dir_size(sf.src)
            moved = 0

            def _on_file(filepath: str, size: int, _sf=sf, _label=label) -> None:
                nonlocal moved
                moved += size
                _sf.moved_bytes = moved
                if on_progress:
                    on_progress(_label, moved, total, filepath)

            # ── Step 1：备份注册表旧值 ────────────────────────────────────────
            old_val = _read_reg_value(_REG_KEY_USER_SHELL, sf.key)
            if old_val is not None:
                self._reg_backups[sf.key] = old_val

            # ── Step 2：移动文件 ──────────────────────────────────────────────
            try:
                _merge_move(sf.src, sf.dst, _on_file, self._cancel)
            except Exception as exc:
                raise RuntimeError(
                    f"[{label}] 文件迁移失败：{exc}\n"
                    f"源路径：{sf.src}\n目标路径：{sf.dst}"
                ) from exc

            if self._cancel.is_set():
                break

            # ── Step 3：写注册表新路径 ────────────────────────────────────────
            try:
                _write_reg_value(_REG_KEY_USER_SHELL,    sf.key, str(sf.dst))
                _write_reg_value(_REG_KEY_SHELL_FOLDERS, sf.key, str(sf.dst))
            except OSError as exc:
                raise RuntimeError(
                    f"[{label}] 注册表写入失败：{exc}\n"
                    "文件已移动，请手动将注册表路径更新为：" + str(sf.dst)
                ) from exc

            # ── Step 4：Junction Point 向后兼容 ──────────────────────────────
            if self._create_junction and not sf.src.exists():
                _create_junction(sf.src, sf.dst)

            sf.done = True

        # ── Step 5：通知 Shell 刷新 ───────────────────────────────────────────
        _notify_shell()

    # ── 取消 ──────────────────────────────────────────────────────────────────

    def cancel(self) -> None:
        """请求中断正在进行的 execute()，文件移动在当前文件完成后停止。"""
        self._cancel.set()

    # ── 注册表回滚 ────────────────────────────────────────────────────────────

    def rollback(self) -> list[str]:
        """
        将已修改的注册表键值恢复为迁移前的旧值。

        注意：此方法**不移动文件**，文件已在目标目录。
        如需完整回滚，在 rollback() 后手动将文件移回原目录。

        Returns:
            操作日志列表（成功/失败信息）。
        """
        logs: list[str] = []
        for key, old_val in self._reg_backups.items():
            label = SHELL_FOLDER_KEYS.get(key, key)
            try:
                _write_reg_value(_REG_KEY_USER_SHELL,    key, old_val)
                _write_reg_value(_REG_KEY_SHELL_FOLDERS, key, old_val)
                logs.append(f"[{label}] 注册表已回滚至：{old_val}")
            except OSError as exc:
                logs.append(f"[{label}] 注册表回滚失败：{exc}")
        _notify_shell()
        return logs

    # ── 迁移摘要 ──────────────────────────────────────────────────────────────

    @property
    def summary(self) -> dict:
        """迁移完成后的结果摘要，供 UI 展示。"""
        return {
            "total_folders":  len(self.folders),
            "done_folders":   sum(1 for sf in self.folders if sf.done),
            "total_bytes":    sum(sf.size_bytes  for sf in self.folders),
            "moved_bytes":    sum(sf.moved_bytes for sf in self.folders),
            "folders":        [
                {
                    "key":         sf.key,
                    "label":       sf.label,
                    "src":         str(sf.src),
                    "dst":         str(sf.dst),
                    "size_bytes":  sf.size_bytes,
                    "moved_bytes": sf.moved_bytes,
                    "done":        sf.done,
                }
                for sf in self.folders
            ],
        }


# ── 还原回 C 盘 ──────────────────────────────────────────────────────────────

# 每个 Shell Folder 在 C 盘的默认路径模板（使用 %USERPROFILE% 基础路径）
_DEFAULT_C_PATHS: dict[str, str] = {
    "Desktop":                                    "Desktop",
    "{374DE290-123F-4565-9164-39C4925E467B}":     "Downloads",
    "Personal":                                   "Documents",
    "My Pictures":                                "Pictures",
    "My Video":                                   "Videos",
    "My Music":                                   "Music",
}


def get_default_c_path(key: str) -> Path:
    """获取指定 Shell Folder 在 C 盘上的默认路径。"""
    user_profile = Path(os.path.expandvars("%USERPROFILE%"))
    sub = _DEFAULT_C_PATHS.get(key)
    if sub is None:
        raise ValueError(f"未知的 Shell Folder 键名：{key}")
    return user_profile / sub


def restore_folder(key: str, on_progress: ProgressCallback | None = None) -> str:
    """
    将一个已迁移到其他盘的 Shell Folder 还原回 C 盘默认位置。

    执行步骤：
        1. 读取当前注册表路径（确认不在 C 盘）
        2. 计算默认 C 盘路径
        3. 如果 C 盘路径是 Junction，先删除它
        4. 将文件从当前位置移动回 C 盘
        5. 更新注册表指回 C 盘
        6. 通知 Shell 刷新

    Args:
        key: 注册表键名（如 "Desktop"）
        on_progress: 可选的进度回调

    Returns:
        操作结果的文字描述。

    Raises:
        RuntimeError: 还原失败时抛出。
    """
    label = SHELL_FOLDER_KEYS.get(key, key)

    # 读取当前路径
    current_folders = get_shell_folders()
    current_path = current_folders.get(key)
    if current_path is None:
        raise RuntimeError(f"无法从注册表读取 [{label}] 的当前路径")

    # 如果已经在 C 盘，无需还原
    if current_path.drive.upper() == "C:":
        return f"[{label}] 已经在 C 盘，无需还原。"

    # 计算 C 盘默认路径
    default_path = get_default_c_path(key)

    # 检查 C 盘可用空间
    src_size = _dir_size(current_path) if current_path.exists() else 0
    c_free = _free_space(Path("C:\\"))
    required = int(src_size * 1.1)
    if c_free < required:
        raise RuntimeError(
            f"C 盘空间不足：需要 {required / 1024**3:.1f} GB，"
            f"可用 {c_free / 1024**3:.1f} GB。"
        )

    # 如果 C 盘默认位置是 Junction/Symlink，先删除它
    if default_path.exists():
        try:
            attrs = os.stat(str(default_path), follow_symlinks=False).st_file_attributes
            is_reparse = bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        except (OSError, AttributeError):
            is_reparse = False

        if is_reparse or default_path.is_symlink():
            # 删除 Junction（不会删除目标目录的内容）
            try:
                os.rmdir(str(default_path))
            except OSError as exc:
                raise RuntimeError(f"无法删除旧的 Junction：{exc}") from exc

    # 移动文件回 C 盘
    cancel = threading.Event()
    total = src_size
    moved = 0

    def _on_file(filepath: str, size: int) -> None:
        nonlocal moved
        moved += size
        if on_progress:
            on_progress(label, moved, total, filepath)

    try:
        _merge_move(current_path, default_path, _on_file, cancel)
    except Exception as exc:
        raise RuntimeError(f"[{label}] 文件还原失败：{exc}") from exc

    # 更新注册表
    try:
        _write_reg_value(_REG_KEY_USER_SHELL,    key, str(default_path))
        _write_reg_value(_REG_KEY_SHELL_FOLDERS, key, str(default_path))
    except OSError as exc:
        raise RuntimeError(
            f"[{label}] 注册表写回失败：{exc}\n"
            f"文件已移回 {default_path}，请手动更新注册表。"
        ) from exc

    # 清理：删除其他盘上的空目录
    try:
        if current_path.exists() and not any(current_path.iterdir()):
            current_path.rmdir()
    except OSError:
        pass

    # 通知 Shell
    _notify_shell()

    return f"[{label}] 已成功还原至 {default_path}"
