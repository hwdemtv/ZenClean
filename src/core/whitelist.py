"""
ZenClean 绝对白名单守卫

优先级最高，任何模块（含 AI 引擎）的判定结果都必须经过本模块复核。
命中白名单的路径返回风险等级 CRISIS，cleaner.py 收到 CRISIS 后硬拒绝执行。

三层防护：
  1. 路径前缀匹配  —— 保护整个目录树
  2. 文件名正则匹配 —— 保护特定扩展名/文件名
  3. 用户数据保护  —— 聊天记录等可迁移但不可清理的目录
"""

import os
import re
from pathlib import Path


# ── 层1：绝对保护路径前缀 ────────────────────────────────────────────────────
# 全部 normalize 为小写，匹配时同样转小写，实现大小写不敏感。
_PROTECTED_PREFIXES_RAW: list[str] = [
    # Windows 核心系统目录
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    r"C:\Windows\WinSxS",
    r"C:\Windows\Boot",
    r"C:\Windows\Fonts",
    r"C:\Windows\servicing",
    r"C:\Windows\SystemApps",

    # Windows Defender（删除会直接导致系统无防护）
    r"C:\Program Files\Windows Defender",
    r"C:\Program Files (x86)\Windows Defender",
    r"C:\ProgramData\Microsoft\Windows Defender",
    r"C:\Users\All Users\Microsoft\Windows Defender",

    # 注册表 Junction / 软链保护区（无限递归陷阱）
    r"C:\Documents and Settings",

    # EFI 引导分区挂载点（删除直接变砖）
    r"C:\EFI",
    r"C:\Boot",

    # 程序文件核心目录（防止误删正在运行的应用）
    r"C:\Program Files\Common Files\microsoft shared",
    r"C:\ProgramData\Microsoft\Windows\Start Menu",
]

# ── 层3：用户数据保护（可迁移但不可清理）────────────────────────────────────
# 这些目录包含重要用户数据，不能被清理，但可以迁移（搬家）
# 使用正则匹配以支持用户目录变化
_USER_DATA_PROTECTION_PATTERNS_RAW: list[str] = [
    # 微信聊天记录目录（仅保护根目录，不含 Cache/log 等缓存子目录）
    r"^[Cc]:\\Users\\[^\\]+\\Documents\\WeChat Files$",
    r"^[Cc]:\\Users\\[^\\]+\\Documents\\微信文件$",
    # QQ聊天记录目录
    r"^[Cc]:\\Users\\[^\\]+\\Documents\\Tencent Files$",
    # 浏览器用户数据根目录（只保护根目录，Cache 子目录可清理）
    r"^[Cc]:\\Users\\[^\\]+\\AppData\\Local\\Google\\Chrome\\User Data\\Default$",
    r"^[Cc]:\\Users\\[^\\]+\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default$",
    r"^[Cc]:\\Users\\[^\\]+\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data\\Default$",
    r"^[Cc]:\\Users\\[^\\]+\\AppData\\Roaming\\Opera Software\\Opera Stable$",
    # AI 工具根目录
    r"^[Cc]:\\Users\\[^\\]+\\AppData\\Roaming\\Cursor$",
    r"^[Cc]:\\Users\\[^\\]+\\AppData\\Roaming\\Code$",
]

_USER_DATA_PROTECTION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _USER_DATA_PROTECTION_PATTERNS_RAW
]

# normalize 为小写 + 统一分隔符
_PROTECTED_PREFIXES: list[str] = [
    os.path.normcase(p) for p in _PROTECTED_PREFIXES_RAW
]


# ── 层2：文件名/扩展名正则黑洞 ───────────────────────────────────────────────
# 匹配的是文件名（basename），不含路径。
_PROTECTED_FILENAME_PATTERNS_RAW: list[str] = [
    r".*\.sys$",          # 内核驱动
    r".*\.dll$",          # 动态链接库
    r".*\.exe$",          # 可执行文件（扫描层不主动推送 exe，此处双保险）
    r".*\.msi$",          # 安装包（系统组件缓存）
    r"ntldr",             # NT 引导加载器（XP 遗留）
    r"bootmgr",           # Vista+ 引导管理器
    r"pagefile\.sys",     # 虚拟内存页面文件
    r"hiberfil\.sys",     # 休眠镜像文件
    r"swapfile\.sys",     # 现代待机交换文件
    r"desktop\.ini",      # Shell 文件夹元数据
    r"thumbs\.db",        # 缩略图缓存（虽可清理，但由 kb 规则管理，白名单不干涉）
]

_PROTECTED_FILENAME_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _PROTECTED_FILENAME_PATTERNS_RAW
]


def is_protected(path: str | Path) -> bool:
    """
    判断给定路径是否命中白名单。

    Args:
        path: 待检测的文件或目录路径（绝对路径）。

    Returns:
        True  —— 路径受保护，禁止任何清理操作。
        False —— 路径不在白名单内，可由后续规则引擎评估。
    """
    path_obj = Path(path)
    normalized = os.path.normcase(str(path_obj))

    # 层1：前缀匹配
    for prefix in _PROTECTED_PREFIXES:
        # 使用 startswith 并确保边界（避免 System32xx 误匹配 System32）
        if normalized.startswith(prefix):
            # 边界检查：prefix 之后的字符必须是路径分隔符或字符串结尾
            rest = normalized[len(prefix):]
            if rest == "" or rest.startswith(os.sep) or rest.startswith("/"):
                return True

    # 层2：文件名正则匹配（仅校验 basename）
    basename = path_obj.name
    for pattern in _PROTECTED_FILENAME_PATTERNS:
        if pattern.fullmatch(basename):
            return True

    # 层3：用户数据保护（精确匹配目录本身，不含子目录）
    # 用于保护聊天记录根目录等，但允许清理其下的 Cache/Temp 子目录
    for pattern in _USER_DATA_PROTECTION_PATTERNS:
        if pattern.fullmatch(normalized):
            return True

    return False


def is_migratable(path: str | Path) -> bool:
    """
    判断路径是否可迁移（搬家）但不可清理。

    聊天记录目录属于此类：可以迁移到其他盘，但不能被清理删除。

    Args:
        path: 待检测的文件或目录路径（绝对路径）。

    Returns:
        True  —— 路径可迁移（用于搬家功能）。
        False —— 路径不可迁移。
    """
    path_obj = Path(path)
    normalized = os.path.normcase(str(path_obj))

    for pattern in _USER_DATA_PROTECTION_PATTERNS:
        if pattern.fullmatch(normalized):
            return True

    return False


# ── 层3：目录名黑名单（提升扫描速度，避开巨量文件锁死区） ─────────────────
# 直接匹配目录本身的名字，大幅剪枝。
_IGNORED_DIR_NAMES_RAW = {
    "WinSxS",
    "servicing",
    "assembly",
    "Package Cache",
}
_IGNORED_DIR_NAMES = set(name.lower() for name in _IGNORED_DIR_NAMES_RAW)

def _is_directory_locked(dir_path: str) -> bool:
    """简单探测目录是否被系统进程强力锁死（如 WebCache）"""
    try:
        with os.scandir(dir_path) as it:
            next(it, None)
        return False
    except PermissionError:
        return True
    except OSError:
        return True

def should_skip_dir(dir_path: str, dir_name: str) -> bool:
    """条件性跳过目录，而非全局黑名单"""
    if dir_name.lower() in _IGNORED_DIR_NAMES:
        return True
        
    lock_prone_dirs = {"webview2", "ebwebview", "webcache", "cache_data", "service worker", "indexeddb", "code cache"}
    if dir_name.lower() in lock_prone_dirs:
        if _is_directory_locked(dir_path):
            return True
            
    return False


def assert_safe(path: str | Path) -> None:
    """
    断言路径安全，若命中白名单则直接抛出异常。
    供 cleaner.py 在执行删除前的最后防线调用。

    Raises:
        PermissionError: 路径命中白名单，操作被拒绝。
    """
    if is_protected(path):
        raise PermissionError(
            f"[CRISIS] 操作被白名单守卫拒绝，路径受系统保护：{path}"
        )
