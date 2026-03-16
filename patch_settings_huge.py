import os

# 1. 扩充 SCAN_TARGETS
settings_path = r"D:\软件开发\ZenClean\src\config\settings.py"
with open(settings_path, "r", encoding="utf-8") as f:
    settings_content = f.read()

# 替换整个 SCAN_TARGETS 块
import re

new_targets = """_USER_PROFILE = os.path.expandvars(r"%USERPROFILE%")

# 扩展后的完整 SCAN_TARGETS
SCAN_TARGETS: list[Path] = [
    # ════════════════════════════════════════════════════════════════════════
    # 一、Windows 系统临时文件（最大垃圾源）
    # ════════════════════════════════════════════════════════════════════════
    Path(_USER_TEMP),
    Path(r"C:\\Windows\\Temp"),
    Path(r"C:\\Windows\\SoftwareDistribution\\Download"),
    Path(r"C:\\Windows\\Logs"),
    Path(r"C:\\Windows\\Panther"),
    Path(r"C:\\Windows\\Prefetch"),
    Path(r"C:\\Windows\\SoftwareDistribution\\OldData"),

    # ════════════════════════════════════════════════════════════════════════
    # 二、Windows 用户级缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(r"C:\\$Recycle.Bin"),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Windows\\Explorer")),      # 缩略图
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Windows\\INetCache")),     # IE缓存
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Windows\\DeliveryOptimization")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Windows\\Notifications")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Windows\\GameDVR")),
    Path(os.path.join(_USER_LOCAL, "CrashDumps")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Windows\\WER")),

    # ════════════════════════════════════════════════════════════════════════
    # 三、国际浏览器缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Google\\Chrome\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Google\\Chrome\\User Data\\Default\\Code Cache")),
    Path(os.path.join(_USER_LOCAL, r"Google\\Chrome\\User Data\\Default\\GPUCache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Edge\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Edge\\User Data\\Default\\Code Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\Edge\\User Data\\Default\\GPUCache")),
    Path(os.path.join(_USER_LOCAL, r"Mozilla\\Firefox\\Profiles")),
    Path(os.path.join(_USER_LOCAL, r"BraveSoftware\\Brave-Browser\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Opera Software\\Opera Stable\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 四、国产浏览器缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"360Chrome\\Chrome\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"360ChromeX\\Chrome\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QQBrowser\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"SogouExplorer\\Webkit\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"SogouExplorer\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"UCBrowser\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"2345Explorer\\User Data\\Default\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tendraw\\User Data\\Default\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 五、腾讯系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    # 微信
    Path(os.path.join(_USER_ROAMING, r"Tencent\\WeChat\\log")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\\WeChat\\XPlugin")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\\WeChat\\All Users")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\WeChat\\UserData")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\WeChat\\CrashReport")),
    # QQ
    Path(os.path.join(_USER_ROAMING, r"Tencent\\QQ\\log")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\\QQ\\Temp")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\\QQ\\Misc")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QQCache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QQ\\Temp")),
    # 腾讯视频
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QLive\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QLive\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QLive\\Download")),
    # QQ音乐
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QQMusic\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QQMusic\\Temp")),
    # WeGame
    Path(os.path.join(_USER_ROAMING, r"Tencent\\WeGame\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\WeGame\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Tencent\\WeGame\\Download")),
    # 腾讯会议
    Path(os.path.join(_USER_LOCAL, r"Tencent\\WeMeet\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\WeMeet\\Record")),

    # ════════════════════════════════════════════════════════════════════════
    # 六、字节系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    # 抖音
    Path(os.path.join(_USER_LOCAL, r"Douyin\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"DouyinPC\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Douyin\\Temp")),
    # 剪映
    Path(os.path.join(_USER_LOCAL, r"JianyingPro\\User Data\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"JianyingPro\\User Data\\Proxy")),
    Path(os.path.join(_USER_LOCAL, r"JianyingPro\\Log")),
    # 飞书
    Path(os.path.join(_USER_LOCAL, r"Feishu\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Feishu\\Logs")),
    Path(os.path.join(_USER_ROAMING, r"LarkShell\\Cache")),
    # 西瓜/今日头条
    Path(os.path.join(_USER_LOCAL, r"XiguaVideo\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"NewsArticle\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 七、阿里系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    # 钉钉
    Path(os.path.join(_USER_ROAMING, r"DingTalk\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"DingTalk\\FileCache")),
    Path(os.path.join(_USER_ROAMING, r"DingTalk\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"DingTalk\\Cache")),
    # 阿里旺旺
    Path(os.path.join(_USER_ROAMING, r"AliWangWang\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"AliWangWang\\Temp")),
    # 千牛/支付宝/云盘
    Path(os.path.join(_USER_ROAMING, r"AliWorkbench\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"AliWorkbench\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Alipay\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"aDrive\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 八、百度系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"Baidu\\BaiduNetdisk\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Baidu\\BaiduNetdisk\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Baidu\\BaiduNetdisk\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Baidu\\BaiduNetdisk\\Thumbnail")),
    Path(os.path.join(_USER_ROAMING, r"Baidu\\BaiduPinyin\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Baidu\\BaiduBrowser\\User Data\\Default\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 九、网易系应用缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Netease\\CloudMusic\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Netease\\CloudMusic\\Cache\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Netease\\CloudMusic\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Netease\\YoudaoNote\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Netease\\YoudaoNote\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Youdao\\YoudaoDict\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Youdao\\YoudaoDict\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Netease\\Launcher\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十、WPS Office 缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"Kingsoft\\WPS Office\\cache")),
    Path(os.path.join(_USER_ROAMING, r"Kingsoft\\WPS Office\\temp")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\\WPS Office\\cache")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\\WPS Office\\temp")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\\WPS Office\\js\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Kingsoft\\CloudCache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十一、视频/音乐/直播软件缓存
    # ════════════════════════════════════════════════════════════════════════
    # 哔哩哔哩
    Path(os.path.join(_USER_ROAMING, r"bilibili\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Bilibili\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Bilibili\\Temp")),
    # 爱奇艺
    Path(os.path.join(_USER_LOCAL, r"iQIYI\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"iQIYI\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"iQIYI\\Download")),
    # 优酷
    Path(os.path.join(_USER_LOCAL, r"Youku\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Youku\\Temp")),
    # 芒果TV
    Path(os.path.join(_USER_LOCAL, r"MangoTV\\Cache")),
    # 斗鱼/虎牙
    Path(os.path.join(_USER_LOCAL, r"DouyuLive\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"HuyaClient\\Cache")),
    # 酷狗/酷我
    Path(os.path.join(_USER_LOCAL, r"Kugou\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Kugou\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"KuGou\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"KuGou\\Temp")),
    # 喜马拉雅
    Path(os.path.join(_USER_LOCAL, r"Ximalaya\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十二、游戏平台缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(r"C:\\Program Files (x86)\\Steam\\appcache"),
    Path(r"C:\\Program Files (x86)\\Steam\\depotcache"),
    Path(os.path.join(_USER_LOCAL, r"Steam\\htmlcache")),
    Path(os.path.join(_USER_LOCAL, r"Epic\\EpicGamesLauncher\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Epic\\EpicGamesLauncher\\Manifests")),
    Path(os.path.join(_USER_ROAMING, r"Battle.net\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"GOG.com\\Galaxy\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Ubisoft\\Ubisoft Game Launcher\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Origin\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十三、网盘/云存储缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"CloudDrive\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"115\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Quark\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\OneDrive\\logs")),
    Path(os.path.join(_USER_LOCAL, r"Microsoft\\OneDrive\\setup\\logs")),

    # ════════════════════════════════════════════════════════════════════════
    # 十四、开发IDE/工具缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"pip\\cache")),
    Path(os.path.join(_USER_ROAMING, r"npm-cache")),
    Path(os.path.join(_USER_LOCAL, r"Yarn\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"NuGet\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"pnpm-cache")),
    Path(os.path.join(_USER_PROFILE, r".gradle\\caches")),
    Path(os.path.join(_USER_PROFILE, r".m2\\repository\\_remote.repositories")),
    Path(os.path.join(_USER_PROFILE, r"go\\pkg\\mod\\cache")),
    Path(os.path.join(_USER_PROFILE, r".cargo\\registry\\cache")),
    Path(os.path.join(_USER_PROFILE, r".cache\\huggingface")),
    Path(os.path.join(_USER_PROFILE, r".bun\\install\\cache")),
    # JetBrains
    Path(os.path.join(_USER_LOCAL, r"JetBrains\\IntelliJIdea2024.1\\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\\PyCharm2024.1\\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\\CLion2024.1\\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\\WebStorm2024.1\\caches")),
    Path(os.path.join(_USER_LOCAL, r"JetBrains\\Toolbox\\apps")),
    # Android Studio
    Path(os.path.join(_USER_LOCAL, r"Android\\Sdk\\temp")),
    Path(os.path.join(_USER_LOCAL, r"Google\\AndroidStudio2024.1\\caches")),

    # ════════════════════════════════════════════════════════════════════════
    # 十五、AI 工具与Git辅助缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_ROAMING, r"Cursor\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Cursor\\CachedData")),
    Path(os.path.join(_USER_ROAMING, r"Cursor\\CachedExtensionVSIXs")),
    Path(os.path.join(_USER_ROAMING, r"Code\\CachedData")),
    Path(os.path.join(_USER_ROAMING, r"Code\\CachedExtensions")),
    Path(os.path.join(_USER_ROAMING, r"Code\\CachedExtensionVSIXs")),
    Path(os.path.join(_USER_LOCAL, r"GitHubDesktop\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"GitKraken\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Atlassian\\Sourcetree\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十六、输入法缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"SogouInput\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"SogouInput\\Temp")),
    Path(os.path.join(_USER_LOCAL, r"Tencent\\QQPinyin\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Microsoft\\InputMethod\\Chs")),

    # ════════════════════════════════════════════════════════════════════════
    # 十七、设计/办公软件缓存
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Adobe\\Common")),
    Path(os.path.join(_USER_ROAMING, r"Adobe\\Common\\Cache")),
    Path(os.path.join(_USER_ROAMING, r"Adobe\\Common\\Media Cache")),
    Path(os.path.join(_USER_LOCAL, r"Adobe\\Lightroom\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Adobe\\Photoshop\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Figma\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Sketch\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"XMind\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Lanhu\\Cache")),
    Path(os.path.join(_USER_LOCAL, r"Modao\\Cache")),

    # ════════════════════════════════════════════════════════════════════════
    # 十八、UWP 应用缓存与Packages目录（重点扫描）
    # ════════════════════════════════════════════════════════════════════════
    Path(os.path.join(_USER_LOCAL, r"Packages")),

    # ════════════════════════════════════════════════════════════════════════
    # 十九、用户下载目录（高危，提醒项，需用户确认）
    # ════════════════════════════════════════════════════════════════════════
    Path(_USER_DOWNLOADS),
]"""

# 替换掉从 SCAN_TARGETS: list[Path] = [ 到 user downloads结束]
pattern = r"SCAN_TARGETS:\s*list\[Path\]\s*=\s*\[(.*?)Path\(_USER_DOWNLOADS\),\s*\]"

new_content = re.sub(pattern, new_targets, settings_content, flags=re.DOTALL)

with open(settings_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("settings.py SCAN_TARGETS updated.")
