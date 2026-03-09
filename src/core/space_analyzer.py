import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from core.logger import logger

@dataclass
class DiskUsage:
    drive: str       # "C:"
    total: int       # bytes
    used: int
    free: int
    
@dataclass
class FolderInfo:
    path: Path
    size_bytes: int
    name: str
    is_junction: bool
    is_protected: bool # 是否系统保护难以删除
    matched_target_id: str | None = None # 命中 APP_TARGETS 时填入，方便联动

def get_disk_usage(drive: str = "C:") -> DiskUsage:
    """获取指定盘符的容量信息"""
    try:
        total, used, free = shutil.disk_usage(f"{drive}\\")
        return DiskUsage(drive, total, used, free)
    except Exception as e:
        logger.error(f"Failed to get disk usage for {drive}: {e}")
        return DiskUsage(drive, 0, 0, 0)

def _is_reparse_point(path_str: str) -> bool:
    try:
        attrs = os.stat(path_str, follow_symlinks=False).st_file_attributes
        return bool(attrs & 0x400) # FILE_ATTRIBUTE_REPARSE_POINT
    except Exception:
        return False

def _fast_dir_size(path_str: str) -> int:
    """
    快速且粗略地计算单层或多层文件夹容量。
    跳过软链接和无权限目录，防止陷入死循环。
    """
    total = 0
    try:
        for entry in os.scandir(path_str):
            try:
                if entry.is_symlink() or _is_reparse_point(entry.path):
                    continue
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _fast_dir_size(entry.path)
            except (OSError, PermissionError):
                pass
    except (OSError, PermissionError):
        pass
    return total

def stream_top_folders(roots: list[str], top_n: int = 20):
    """
    流式扫描关键根目录，发现一个大文件夹即 yield 一个结果。
    """
    scanned_paths = set()
    
    # 优先级排序：首先扫描最短的根目录路径（如 C:\），确保大的分级目录（Users, ProgramData）最先被捕获
    roots.sort(key=lambda r: len(os.path.expandvars(r)))

    for root_str in roots:
        expanded_root = os.path.expandvars(root_str)
        if not os.path.exists(expanded_root):
            continue
            
        try:
            # 使用 scandir 获取流式条目
            with os.scandir(expanded_root) as it:
                for entry in it:
                    if not entry.is_dir():
                        continue
                        
                    path_str = entry.path
                    if path_str in scanned_paths:
                        continue
                        
                    name_lower = entry.name.lower()
                    # 极速跳过：已知低价值且扫描极其耗时的系统目录
                    if name_lower in ("windows", "system volume information", "$recycle.bin", "program files", "program files (x86)"):
                        continue

                    scanned_paths.add(path_str)
                    is_junction = _is_reparse_point(path_str)
                    
                    # 为了首屏爽感，我们先算一层大小，深度递归放在后续
                    size = 0 if is_junction else _fast_dir_size(path_str)
                    
                    if size > 100 * 1024 * 1024 or is_junction: # 只汇报 > 100MB 的或 Junction
                        yield FolderInfo(
                            path=Path(path_str),
                            size_bytes=size,
                            name=entry.name,
                            is_junction=is_junction,
                            is_protected=name_lower in ("appdata", "documents", "desktop")
                        )
                        
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to scan root {expanded_root}: {e}")

def scan_top_folders(roots: list[str], top_n: int = 15) -> list[FolderInfo]:
    """兼容旧接口的包装器"""
    all_results = list(stream_top_folders(roots, top_n))
    all_results.sort(key=lambda x: x.size_bytes, reverse=True)
    return all_results[:top_n]


if __name__ == "__main__":
    usage = get_disk_usage("C:")
    print(f"C Drive: {usage.used/(1024**3):.1f} / {usage.total/(1024**3):.1f} GB")
    
    # 局部测试核心大文件坑位
    test_roots = [
        "C:\\",
        "%USERPROFILE%",
        "%LOCALAPPDATA%"
    ]
    
    print("\nTop Folders:")
    top_items = scan_top_folders(test_roots, top_n=5)
    for t in top_items:
        print(f"[{'JUNCTION' if t.is_junction else 'DIR'}] {t.name}: {t.size_bytes / (1024**3):.2f} GB | Protected: {t.is_protected}")
