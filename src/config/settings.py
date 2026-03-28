"""
ZenClean 全局配置
所有模块从此处读取常量，不允许在业务代码中硬编码配置值。
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    def _get_project_root() -> Path:
        """
        兼容源码运行与 PyInstaller 打包后的运行目录：
        - 打包后：使用 sys._MEIPASS 指向的临时解包目录
        - 源码运行：回退到 config 模块的上上级目录（项目根）
        """
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(__file__).parent.parent.parent

    _root = _get_project_root()
    load_dotenv(dotenv_path=_root / ".env")
except ImportError:
    # 未安装 python-dotenv 时，静默跳过环境变量文件加载
    pass

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
_USER_PROFILE = os.path.expandvars(r"%USERPROFILE%")
_USER_DOWNLOADS = _get_downloads_folder()
USER_DOWNLOADS_DIR = _USER_DOWNLOADS  # 暴露给 file_kb.json 正则替换使用

SCAN_TARGETS: list[Path] = [
    # ════════════════════════════════════════════════════════════════════════
    # 一、Windows 系统临时文件（最大垃圾源）
    # ════════════════════════════════════════════════════════════════════════
    Path(_USER_TEMP),
    Path(r"C:\Windows\Temp"),
    Path(r"C:\Windows\SoftwareDistribution\Download"),
    Path(r"C:\Windows\Logs"),
    Path(r"C:\Windows\Panther"),
    Path(r"C:\Windows\Prefetch"),
    Path(r"C:\Windows\SoftwareDistribution\OldData"),

    # ════════════════════════════════════════════════════════════════════════
    # 二、Windows 用户级缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(r"C:\$Recycle.Bin"),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\Explorer")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\INetCache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\DeliveryOptimization")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\Notifications")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\GameDVR")),
    Path(os.path.join(_USER_LOCAL, "CrashDumps")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Windows\WER")),

    # ════════════════════════════════════════════════════════════════════════
    # 三、国际浏览器缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Google\Chrome\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Google\Chrome\User Data\Default\Code Cache")),
    Path(os.path.join(_USER_LOCAL, r"Google\Chrome\User Data\Default\GPUCache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Edge\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Edge\User Data\Default\Code Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\Edge\User Data\Default\GPUCache")),
    Path(os.path.join(_USER_LOCAL, r"Mozilla\Firefox\Profiles")),
    Path(os.path.join(_USER_LOCAL, r"BraveSoftware\Brave-Browser\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Opera Software\Opera Stable\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 四、国产浏览器缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"360Chrome\Chrome\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"360ChromeX\Chrome\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QQBrowser\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"SogouExplorer\Webkit\Cache")),
    Path(os.path.join(_USER_ROAMING, r"SogouExplorer\Cache")),
    Path(os.path.join(_USER_LOCAL, r"UCBrowser\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"2345Explorer\User Data\Default\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tendraw\User Data\Default\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 五、腾讯系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    # 微信
    Path(os.path.join(_USER_ROAMING, r"Tencent\WeChat\log")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\WeChat\XPlugin")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\WeChat\All Users")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\WeChat\UserData")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\WeChat\CrashReport")),
    # QQ
    Path(os.path.join(_USER_ROAMING, r"Tencent\QQ\log")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\QQ\Temp")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\QQ\Misc")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QQCache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QQ\Temp")),
    # 腾讯视频
    Path(os.path.join(_USER_LOCAL, r"Tencent\QLive\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QLive\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QLive\Download")),
    # QQ音乐
    Path(os.path.join(_USER_LOCAL, r"Tencent\QQMusic\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QQMusic\Temp")),
    # WeGame
    Path(os.path.join(_USER_ROAMING, r"Tencent\WeGame\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\WeGame\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\WeGame\Download")),
    # 腾讯会议
    Path(os.path.join(_USER_LOCAL, r"Tencent\WeMeet\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\WeMeet\Record")),
    # 腾讯文档
    Path(os.path.join(_USER_LOCAL, r"Tencent\Docs\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 六、字节系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    # 抖音
    Path(os.path.join(_USER_LOCAL, r"Douyin\Cache")),
    Path(os.path.join(_USER_LOCAL, r"DouyinPC\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Douyin\Temp")),
    # 剪映
    Path(os.path.join(_USER_LOCAL, r"JianyingPro\User Data\Cache")),
    Path(os.path.join(_USER_LOCAL, r"JianyingPro\User Data\Proxy")),
    Path(os.path.join(_USER_LOCAL, r"JianyingPro\Log")),
    # 飞书
    Path(os.path.join(_USER_LOCAL, r"Feishu\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Feishu\Logs")),
    Path(os.path.join(_USER_ROAMING, r"LarkShell\Cache")),
    # 西瓜/今日头条
    Path(os.path.join(_USER_LOCAL, r"XiguaVideo\Cache")),
    Path(os.path.join(_USER_LOCAL, r"NewsArticle\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 七、阿里系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    # 钉钉
    Path(os.path.join(_USER_ROAMING, r"DingTalk\Cache")),
    Path(os.path.join(_USER_ROAMING, r"DingTalk\FileCache")),
    Path(os.path.join(_USER_ROAMING, r"DingTalk\Temp")),
    Path(os.path.join(_USER_LOCAL, r"DingTalk\Cache")),
    # 阿里旺旺
    Path(os.path.join(_USER_ROAMING, r"AliWangWang\Cache")),
    Path(os.path.join(_USER_ROAMING, r"AliWangWang\Temp")),
    # 千牛/支付宝/云盘
    Path(os.path.join(_USER_ROAMING, r"AliWorkbench\Cache")),
    Path(os.path.join(_USER_LOCAL, r"AliWorkbench\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Alipay\Cache")),
    Path(os.path.join(_USER_LOCAL, r"aDrive\Cache")),
    Path(os.path.join(_USER_LOCAL, r"aDrive\Logs")),

    # ════════════════════════════════════════════════════════════════════════
    # 八、百度系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"Baidu\BaiduNetdisk\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Baidu\BaiduNetdisk\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Baidu\BaiduNetdisk\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Baidu\BaiduNetdisk\Thumbnail")),
    Path(os.path.join(_USER_ROAMING, r"Baidu\BaiduPinyin\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Baidu\BaiduBrowser\User Data\Default\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 九、网易系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Netease\CloudMusic\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Netease\CloudMusic\Cache\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Netease\CloudMusic\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Netease\YoudaoNote\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Netease\YoudaoNote\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Youdao\YoudaoDict\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Youdao\YoudaoDict\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Netease\Launcher\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十、WPS Office 缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"Kingsoft\WPS Office\cache")),
    Path(os.path.join(_USER_ROAMING, r"Kingsoft\WPS Office\temp")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\WPS Office\cache")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\WPS Office\temp")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\WPS Office\js\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\CloudCache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十一、视频/音乐/直播软件缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"bilibili\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Bilibili\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Bilibili\Temp")),
    Path(os.path.join(_USER_LOCAL, r"iQIYI\Cache")),
    Path(os.path.join(_USER_LOCAL, r"iQIYI\Temp")),
    Path(os.path.join(_USER_LOCAL, r"iQIYI\Download")),
    Path(os.path.join(_USER_LOCAL, r"Youku\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Youku\Temp")),
    Path(os.path.join(_USER_LOCAL, r"MangoTV\Cache")),
    Path(os.path.join(_USER_LOCAL, r"DouyuLive\Cache")),
    Path(os.path.join(_USER_LOCAL, r"HuyaClient\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Kugou\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Kugou\Temp")),
    Path(os.path.join(_USER_LOCAL, r"KuGou\Cache")),
    Path(os.path.join(_USER_LOCAL, r"KuGou\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Ximalaya\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十二、游戏平台缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(r"C:\Program Files (x86)\Steam\appcache"),
    Path(r"C:\Program Files (x86)\Steam\depotcache"),
    Path(os.path.join(_USER_LOCAL, r"Steam\htmlcache")),
    Path(os.path.join(_USER_LOCAL, r"Epic\EpicGamesLauncher\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Epic\EpicGamesLauncher\Manifests")),
    Path(os.path.join(_USER_ROAMING, r"Battle.net\Cache")),
    Path(os.path.join(_USER_LOCAL, r"GOG.com\Galaxy\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Ubisoft\Ubisoft Game Launcher\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Origin\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十三、网盘/云存储缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"CloudDrive\Cache")),
    Path(os.path.join(_USER_LOCAL, r"115\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Quark\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\OneDrive\logs")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\OneDrive\setup\logs")),

    # ════════════════════════════════════════════════════════════════════════
    # 十四、开发IDE/工具缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"pip\cache")),
    Path(os.path.join(_USER_ROAMING, r"npm-cache")),
    Path(os.path.join(_USER_LOCAL, r"Yarn\Cache")),
    Path(os.path.join(_USER_LOCAL, r"NuGet\Cache")),
    Path(os.path.join(_USER_LOCAL, r"pnpm-cache")),
    Path(os.path.join(_USER_PROFILE, r".gradle\caches")),
    Path(os.path.join(_USER_PROFILE, r".m2\repository\_remote.repositories")),
    Path(os.path.join(_USER_PROFILE, r"go\pkg\mod\cache")),
    Path(os.path.join(_USER_PROFILE, r".cargo\registry\cache")),
    Path(os.path.join(_USER_PROFILE, r".cache\huggingface")),
    Path(os.path.join(_USER_PROFILE, r".bun\install\cache")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\IntelliJIdea2024.1\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\PyCharm2024.1\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\CLion2024.1\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\WebStorm2024.1\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\Toolbox\apps")),
    Path(os.path.join(_USER_LOCAL, r"Android\Sdk\temp")),
    Path(os.path.join(_USER_LOCAL, r"Google\AndroidStudio2024.1\caches")),

    # ════════════════════════════════════════════════════════════════════════
    # 十五、AI 工具与Git辅助缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"Cursor\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Cursor\CachedData")),
    Path(os.path.join(_USER_ROAMING, r"Cursor\CachedExtensionVSIXs")),
    Path(os.path.join(_USER_ROAMING, r"Code\CachedData")),
    Path(os.path.join(_USER_ROAMING, r"Code\CachedExtensions")),
    Path(os.path.join(_USER_ROAMING, r"Code\CachedExtensionVSIXs")),
    Path(os.path.join(_USER_LOCAL, r"GitHubDesktop\Cache")),
    Path(os.path.join(_USER_LOCAL, r"GitKraken\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Atlassian\Sourcetree\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十六、输入法缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"SogouInput\Cache")),
    Path(os.path.join(_USER_LOCAL, r"SogouInput\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\QQPinyin\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Microsoft\InputMethod\Chs")),

    # ════════════════════════════════════════════════════════════════════════
    # 十七、设计/办公软件缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Adobe\Common")),
    Path(os.path.join(_USER_ROAMING, r"Adobe\Common\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Adobe\Common\Media Cache")),
    Path(os.path.join(_USER_LOCAL, r"Adobe\Lightroom\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Adobe\Photoshop\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Figma\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Sketch\Cache")),
    Path(os.path.join(_USER_LOCAL, r"XMind\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Lanhu\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Modao\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十八、UWP 应用缓存与Packages目录（重点扫描）
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Packages")),

    # ════════════════════════════════════════════════════════════════════════
    # 十九、用户下载目录（高危，提醒项，需用户确认）
    # ════════════════════════════════════════════════════════════════════════
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
# 服务端节点列表（优先读取环境变量，以逗号分隔；否则使用占位默认值）
# 真实生产环境的授权域名仅通过 `.env` / 系统环境变量配置，不写死在开源仓库中。
DEFAULT_LICENSE_SERVER_URLS: list[str] = [
    "https://your-license-server.com",
]
_env_urls = os.environ.get("LICENSE_SERVER_URLS", "")
if _env_urls:
    LICENSE_SERVER_URLS = [u.strip() for u in _env_urls.split(",") if u.strip()]
else:
    LICENSE_SERVER_URLS = DEFAULT_LICENSE_SERVER_URLS

LICENSE_PRODUCT_ID = os.environ.get("LICENSE_PRODUCT_ID", "zenclean") # 产品ID
# 第一阶段公测万能码
BETA_PUBLIC_KEY = os.environ.get("BETA_PUBLIC_KEY", "")
# JWT 离线有效期（秒）
JWT_OFFLINE_TTL = 86400        # 24 小时
# NTP 时间偏差容忍上限（秒）
NTP_MAX_DRIFT_SECONDS = 300
# 联网请求超时（秒）
LICENSE_REQUEST_TIMEOUT = 8

# ── AI 云端代理网关 ────────────────────────────────────────────────────────────
# 后端网关基地址（通过环境变量载入）
AI_GATEWAY_BASE_URL = os.environ.get("AI_GATEWAY_BASE_URL", "https://your-license-server.com/api/v1/ai")
# SSE 流式分析端点（POST，携带 JWT Authorization）
AI_ANALYZE_URL = f"{AI_GATEWAY_BASE_URL}/chat/completions"
# 额度查询端点（GET，携带 JWT Authorization）
AI_QUOTA_URL = f"{AI_GATEWAY_BASE_URL}/quota"
# 单次请求超时（秒）——SSE 流式传输可能需要稍长的时间
AI_REQUEST_TIMEOUT = 8
# 本地 60 秒内最大请求次数（客户端侧限流，与服务端限流同步）
AI_CLIENT_RATE_LIMIT = 100
AI_CLIENT_RATE_WINDOW = 60  # 秒

# ── UI 主题 (动态主题映射机制) ──────────────────────────────────────────────────
# 此时不再硬编码 Hex 色值，而是使用 Flet 原生 Material 3 Theme 的变量名称。
# 这使得软件可以在 "深色赛博护眼模式" 和 "浅色实验舱模式" 间丝滑切换，而不用动 UI 层代码。
COLOR_ZEN_BG = "background"
COLOR_ZEN_SURFACE = "surface"
COLOR_ZEN_PRIMARY = "primary"
COLOR_ZEN_GOLD = "secondary"
COLOR_ZEN_DANGER = "error"
COLOR_ZEN_DIVIDER = "outline"
COLOR_ZEN_TEXT_MAIN = "onSurface"
COLOR_ZEN_TEXT_DIM = "onSurfaceVariant"
COLOR_ZEN_WARNING = "tertiary"

# 兼容旧代码引用 (渐进式替换)
THEME_BG_COLOR = COLOR_ZEN_BG
THEME_ACCENT_COLOR = COLOR_ZEN_PRIMARY

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 680

# ── 版本更新检查 ───────────────────────────────────────────────────────────────
# 留空则跳过更新检查（CI/离线环境使用）
# 国内可使用镜像加速获取 API: https://api.kkgithub.com/repos/hwdemtv/ZenClean/releases/latest
UPDATE_CHECK_URL = "https://api.kkgithub.com/repos/hwdemtv/ZenClean/releases/latest"

# 默认官方国内下载源（避开 GitHub Releases 的强壁垒）
FALLBACK_DOWNLOAD_URL = "https://pan.quark.cn/s/38bdcc92a943"

# ── 缓存 ───────────────────────────────────────────────────────────────────────
AI_CACHE_FILE = APP_DATA_DIR / "ai_cache.json"
