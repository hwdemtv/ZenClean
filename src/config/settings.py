"""
ZenClean 全局配置
所有模块从此处读取常量，不允许在业务代码中硬编码配置值。
"""
import os
import sys
from pathlib import Path

def _get_downloads_folder() -> str:
    """获取 Windows 系统真实的下载文件夹路径（支持用户修改默认位置）"""
    if sys.platform != "win32":
        return os.path.join(os.path.expandvars("%USERPROFILE%"), "Downloads")
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            val = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
            if val:
                return os.path.expandvars(val)
    except Exception:
        pass
    return os.path.join(os.path.expandvars("%USERPROFILE%"), "Downloads")


# ── 版本 ──────────────────────────────────────────────────────────────────────
APP_NAME = "ZenClean"
APP_VERSION = "0.1.0"          # MVP 首发版
APP_DISPLAY_NAME = "ZenClean (禅清)"

# ── 路径 ──────────────────────────────────────────────────────────────────────
# 用户数据根目录：%AppData%\ZenClean
APP_DATA_DIR = Path(os.environ.get("APPDATA", "~")) / "ZenClean"
LOG_DIR = APP_DATA_DIR / "logs"
AUTH_DAT_PATH = APP_DATA_DIR / "auth.dat"

# 扫描靶向目录清单（仅扫描已知的垃圾/缓存热区，不做全盘遍历）
# 使用 os.path.expandvars 在运行时展开环境变量
_USER_LOCAL = os.path.expandvars(r"%LOCALAPPDATA%")
_USER_ROAMING = os.path.expandvars(r"%APPDATA%")
_USER_TEMP = os.path.expandvars(r"%TEMP%")
_USER_DOWNLOADS = _get_downloads_folder()
USER_DOWNLOADS_DIR = _USER_DOWNLOADS  # 暴露给 file_kb.json 正则替换使用

SCAN_TARGETS: list[Path] = [
    # ── Windows 系统临时文件（最大垃圾源） ──────────────────────────────────
    Path(_USER_TEMP),
    Path(r"C:\Windows\Temp"),

    # ── Windows 更新缓存 ───────────────────────────────────────────────────
    Path(r"C:\Windows\SoftwareDistribution\Download"),
    Path(r"C:\Windows\Logs"),
    Path(r"C:\Windows\Panther"),
    Path(r"C:\Windows\Prefetch"),

    # ── 回收站 ──────────────────────────────────────────────────────────────
    Path(r"C:\$Recycle.Bin"),

    # ── 缩略图缓存 ──────────────────────────────────────────────────────────
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\Explorer")),

    # ── 崩溃转储 ────────────────────────────────────────────────────────────
    Path(os.path.join(_USER_LOCAL, "CrashDumps")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\WER")),

    # ── 浏览器缓存 ──────────────────────────────────────────────────────────
    Path(os.path.join(_USER_LOCAL, r"Google\Chrome\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Google\Chrome\User Data\Default\Code Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Edge\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Edge\User Data\Default\Code Cache")),
    Path(os.path.join(_USER_LOCAL, r"Mozilla\Firefox\Profiles")),
    Path(os.path.join(_USER_LOCAL, r"BraveSoftware\Brave-Browser\User Data\Default\Cache")),

    # ── 社交软件缓存 ────────────────────────────────────────────────────────
    Path(os.path.join(_USER_ROAMING, r"Tencent\WeChat\log")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\QQ\log")),

    # ── 开发工具缓存 ────────────────────────────────────────────────────────
    Path(os.path.join(_USER_LOCAL, r"pip\cache")),
    Path(os.path.join(_USER_ROAMING, "npm-cache")),
    Path(os.path.join(_USER_LOCAL, r"Yarn\Cache")),
    Path(os.path.join(_USER_LOCAL, r"NuGet\Cache")),

    # ── 应用缓存 ────────────────────────────────────────────────────────────
    Path(os.path.join(_USER_LOCAL, r"Adobe\Common")),
    Path(os.path.join(_USER_LOCAL, r"Spotify\Storage")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Office\16.0\OfficeFileCache")),

    # ── 用户下载目录 (高危) ──────────────────────────────────────────────────
    Path(_USER_DOWNLOADS),
]

# 兼容旧引用（部分模块可能仍引用 SCAN_ROOT）
SCAN_ROOT = Path("C:\\")

# 知识库路径（相对本文件的绝对路径解析）
_CONFIG_DIR = Path(__file__).parent
FILE_KB_PATH = _CONFIG_DIR / "file_kb.json"

# ── 扫描行为 ──────────────────────────────────────────────────────────────────
# 扫描子进程每积攒多少条 NodeDict 批量推入 Queue
SCAN_BATCH_SIZE = 50

# Queue 消费侧轮询间隔（秒），影响 UI 实时刷新频率
QUEUE_POLL_INTERVAL = 0.05

# ── 日志 ──────────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"             # 可通过设置页切换为 DEBUG
LOG_RETENTION_DAYS = 7         # 保留最近 N 天的日志文件

# ── 鉴权 ──────────────────────────────────────────────────────────────────────
# 服务端节点列表（带有高可用与降级 Fallback 优先级的配置，首个即可连通则不尝试后续）
LICENSE_SERVER_URLS = [
    "https://km.hwdemtv.com",
    "https://kami.hwdemtv.com",
    "https://hw-license-center.hwdemtv.workers.dev"
]
LICENSE_PRODUCT_ID = "zenclean"                  # 在 hw-license-center 后台注册的产品ID
# 第一阶段公测万能码（默认 fallback，或留空交由用户输入）
BETA_PUBLIC_KEY = ""
# JWT 离线有效期（秒）：服务端默认签 30 天，本地宽容 24 h 后台静默重验
JWT_OFFLINE_TTL = 86400        # 24 小时
# NTP 时间偏差容忍上限（秒），超过则禁用离线 JWT 校验
NTP_MAX_DRIFT_SECONDS = 300
# 联网请求超时（秒）
LICENSE_REQUEST_TIMEOUT = 8

# ── UI 主题 ───────────────────────────────────────────────────────────────────
THEME_BG_COLOR = "#0D0D0D"
THEME_ACCENT_COLOR = "#00D4AA"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 680

# ── 版本更新检查 ───────────────────────────────────────────────────────────────
# 留空则跳过更新检查（CI/离线环境使用）
UPDATE_CHECK_URL = ""  # e.g. "https://api.github.com/repos/owner/zenclean/releases/latest"
