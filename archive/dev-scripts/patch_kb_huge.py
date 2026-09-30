import json
import re

kb_path = r"D:\软件开发\ZenClean\src\config\file_kb.json"

with open(kb_path, "r", encoding="utf-8") as f:
    data = json.load(f)

existing_patterns = [r["pattern"] for r in data["rules"]]

# 为上面扩展的目录建立分类映射和描述
new_rules_def = [
    # Windows
    (r"Windows\\SoftwareDistribution\\Download", "Windows 更新下载缓存", "system_cache"),
    (r"Windows\\Logs", "Windows 系统日志", "system_cache"),
    (r"Windows\\Panther", "Windows 安装日志缓存", "system_cache"),
    (r"Windows\\Prefetch", "Windows 预读取缓存", "system_cache"),
    (r"Windows\\SoftwareDistribution\\OldData", "Windows 旧更新数据", "system_cache"),
    (r"Microsoft\\Windows\\Explorer", "Windows 缩略图缓存", "system_cache"),
    (r"Microsoft\\Windows\\INetCache", "Windows IE/通用网络缓存", "system_cache"),
    (r"Microsoft\\Windows\\DeliveryOptimization", "Windows 传递优化缓存", "system_cache"),
    (r"Microsoft\\Windows\\Notifications", "Windows 通知数据库缓存", "system_cache"),
    (r"Microsoft\\Windows\\GameDVR", "Windows 游戏录制缓存", "system_cache"),
    (r"CrashDumps", "系统崩溃转储文件", "system_cache"),
    (r"Microsoft\\Windows\\WER", "Windows 错误报告缓存", "system_cache"),
    
    # 国际浏览器
    (r"Google\\Chrome\\User Data\\Default\\Cache", "Chrome 浏览器缓存", "browser_cache"),
    (r"Google\\Chrome\\User Data\\Default\\Code Cache", "Chrome 浏览器代码缓存", "browser_cache"),
    (r"Google\\Chrome\\User Data\\Default\\GPUCache", "Chrome 浏览器 GPU 缓存", "browser_cache"),
    (r"Microsoft\\Edge\\User Data\\Default\\Cache", "Edge 浏览器缓存", "browser_cache"),
    (r"Microsoft\\Edge\\User Data\\Default\\Code Cache", "Edge 浏览器代码缓存", "browser_cache"),
    (r"Microsoft\\Edge\\User Data\\Default\\GPUCache", "Edge 浏览器 GPU 缓存", "browser_cache"),
    (r"Mozilla\\Firefox\\Profiles.*\\cache2", "Firefox 浏览器缓存", "browser_cache"),
    (r"BraveSoftware\\Brave-Browser.*\\Cache", "Brave 浏览器缓存", "browser_cache"),
    (r"Opera Software\\Opera Stable\\Cache", "Opera 浏览器缓存", "browser_cache"),
    
    # 国产浏览器 (补充)
    (r"360ChromeX\\Chrome.*\\Cache", "360 极速浏览器缓存", "browser_cache"),
    (r"UCBrowser.*\\Cache", "UC 浏览器 PC 版缓存", "browser_cache"),
    (r"2345Explorer.*\\Cache", "2345 浏览器缓存", "browser_cache"),
    (r"Tendraw.*\\Cache", "星愿浏览器缓存", "browser_cache"),

    # 腾讯系
    (r"Tencent\\QQ\\log", "QQ 运行日志", "social_cache"),
    (r"Tencent\\QQ\\Temp", "QQ 临时文件", "social_cache"),
    (r"Tencent\\QQ\\Misc", "QQ 杂项缓存", "social_cache"),
    (r"Tencent\\QQCache", "QQ 本地缓存大容量区", "social_cache"),
    (r"Tencent\\QQMusic\\Cache", "QQ音乐播放缓存", "av_cache"),
    (r"Tencent\\QQMusic\\Temp", "QQ音乐临时文件", "av_cache"),
    (r"Tencent\\QLive\\Cache", "腾讯视频播放缓存", "av_cache"),
    (r"Tencent\\QLive\\Temp", "腾讯视频临时文件", "av_cache"),
    (r"Tencent\\WeMeet\\Cache", "腾讯会议临时缓存", "social_cache"),
    (r"Tencent\\WeGame\\Download", "WeGame 游戏下载安装包残留", "game_cache"),
    (r"Tencent\\Docs\\Cache", "腾讯文档本地缓存", "office_cache"),

    # 字节系
    (r"DouyinPC\\Cache", "抖音 PC 版缓存", "av_cache"),
    (r"Douyin\\Temp", "抖音 PC 版临时文件", "av_cache"),
    (r"JianyingPro\\User Data\\Proxy", "剪映代理文件缓存", "av_cache"),
    (r"JianyingPro\\Log", "剪映运行日志", "av_cache"),
    (r"Feishu\\Cache", "飞书本地缓存", "social_cache"),
    (r"Feishu\\Logs", "飞书运行日志", "social_cache"),
    (r"LarkShell\\Cache", "飞书漫游缓存", "social_cache"),
    (r"XiguaVideo\\Cache", "西瓜视频 PC 缓存", "av_cache"),
    (r"NewsArticle\\Cache", "今日头条 PC 缓存", "av_cache"),

    # 阿里系
    (r"DingTalk\\Cache", "钉钉本地缓存", "social_cache"),
    (r"DingTalk\\Temp", "钉钉临时文件", "social_cache"),
    (r"AliWangWang\\Temp", "阿里旺旺临时文件", "social_cache"),
    (r"AliWorkbench\\Cache", "千牛工作台缓存", "social_cache"),
    (r"Alipay\\Cache", "支付宝 PC 版缓存", "social_cache"),
    (r"aDrive\\Cache", "阿里云盘缓存", "cloud_cache"),
    (r"aDrive\\Logs", "阿里云盘日志", "cloud_cache"),

    # 百度系
    (r"Baidu\\BaiduNetdisk\\Cache", "百度网盘缓存", "cloud_cache"),
    (r"Baidu\\BaiduNetdisk\\Temp", "百度网盘临时文件", "cloud_cache"),
    (r"Baidu\\BaiduNetdisk\\Thumbnail", "百度网盘缩略图", "cloud_cache"),
    (r"Baidu\\BaiduPinyin\\Cache", "百度输入法缓存", "system_cache"),
    (r"Baidu\\BaiduBrowser.*\\Cache", "百度浏览器缓存", "browser_cache"),

    # 网易系
    (r"Netease\\CloudMusic.*\\Cache", "网易云音乐缓存", "av_cache"),
    (r"Netease\\CloudMusic\\Temp", "网易云音乐临时文件", "av_cache"),
    (r"Netease\\YoudaoNote\\Cache", "有道云笔记缓存", "office_cache"),
    (r"Youdao\\YoudaoDict\\Cache", "有道词典缓存", "office_cache"),
    (r"Netease\\Launcher\\Cache", "网易游戏平台缓存", "game_cache"),

    # WPS
    (r"Kingsoft\\WPS Office\\temp", "WPS Office 临时文件", "office_cache"),
    (r"Kingsoft\\WPS Office\\js\\Cache", "WPS 内置组件缓存", "office_cache"),
    (r"Kingsoft\\CloudCache", "WPS 云文档本地缓存", "office_cache"),

    # 视频/音乐/直播
    (r"bilibili\\Cache", "哔哩哔哩 PC 版缓存", "av_cache"),
    (r"Bilibili\\Temp", "哔哩哔哩 PC 临时文件", "av_cache"),
    (r"iQIYI\\Cache", "爱奇艺 PC 版缓存", "av_cache"),
    (r"iQIYI\\Temp", "爱奇艺 PC 临时缓存", "av_cache"),
    (r"Youku\\Cache", "优酷 PC 版缓存", "av_cache"),
    (r"MangoTV\\Cache", "芒果TV PC 缓存", "av_cache"),
    (r"DouyuLive\\Cache", "斗鱼直播 PC 缓存", "av_cache"),
    (r"HuyaClient\\Cache", "虎牙直播 PC 缓存", "av_cache"),
    (r"Kugou\\Cache", "酷狗音乐缓存", "av_cache"),
    (r"KuGou\\Cache", "酷我音乐缓存", "av_cache"),
    (r"Ximalaya\\Cache", "喜马拉雅 PC 缓存", "av_cache"),

    # 游戏平台
    (r"Steam\\depotcache", "Steam 预载数据与分发缓存", "game_cache"),
    (r"Epic\\EpicGamesLauncher\\Manifests", "Epic 平台清单缓存", "game_cache"),
    (r"Battle\.net\\Cache", "暴雪战网平台缓存", "game_cache"),
    (r"GOG\.com\\Galaxy\\Cache", "GOG Galaxy 平台缓存", "game_cache"),
    (r"Ubisoft\\Ubisoft Game Launcher\\Cache", "Ubisoft Connect 缓存", "game_cache"),
    (r"Origin\\Cache", "EA Origin 平台缓存", "game_cache"),

    # 网盘
    (r"CloudDrive\\Cache", "天翼云盘等泛云盘缓存", "cloud_cache"),
    (r"115\\Cache", "115网盘 PC 缓存", "cloud_cache"),
    (r"Quark\\Cache", "夸克网盘 PC 缓存", "cloud_cache"),
    (r"Microsoft\\OneDrive.*\\logs", "OneDrive 日志数据", "cloud_cache"),

    # 开发环境/IDE
    (r"pip\\cache", "Python Pip 依赖包安装缓存", "dev_cache"),
    (r"npm-cache", "Node.js Npm 缓存", "dev_cache"),
    (r"Yarn\\Cache", "Node.js Yarn 缓存", "dev_cache"),
    (r"NuGet\\Cache", ".NET NuGet 包缓存", "dev_cache"),
    (r"pnpm-cache", "Node.js Pnpm 缓存", "dev_cache"),
    (r"\.gradle\\caches", "Gradle 构建缓存", "dev_cache"),
    (r"\.m2\\repository\\_remote\.repositories", "Maven 远程元数据缓存", "dev_cache"),
    (r"go\\pkg\\mod\\cache", "Golang Mod 模块缓存", "dev_cache"),
    (r"\.cargo\\registry\\cache", "Rust Cargo 依赖库缓存", "dev_cache"),
    (r"\.cache\\huggingface", "HuggingFace AI 模型缓存", "dev_cache"),
    (r"\.bun\\install\\cache", "Bun 包管理器缓存", "dev_cache"),
    (r"JetBrains.*\\caches", "JetBrains IDE (IntelliJ/PyCharm/WebStorm) 缓存", "dev_cache"),
    (r"JetBrains\\Toolbox\\apps", "JetBrains Toolbox 包管理缓存", "dev_cache"),
    (r"AndroidStudio.*\\caches", "Android Studio IDE 缓存", "dev_cache"),
    (r"Android\\Sdk\\temp", "Android SDK 临时缓存", "dev_cache"),

    # AI / Git
    (r"Cursor\\Cache", "Cursor AI 编辑器缓存", "dev_cache"),
    (r"Code\\Cached", "VS Code 扩展代码缓存", "dev_cache"),
    (r"GitHubDesktop\\Cache", "GitHub Desktop 客户端缓存", "dev_cache"),
    (r"GitKraken\\Cache", "GitKraken 客户端缓存", "dev_cache"),
    (r"Atlassian\\Sourcetree\\Cache", "Sourcetree 客户端缓存", "dev_cache"),

    # 输入法
    (r"SogouInput\\Cache", "搜狗输入法缓存", "system_cache"),
    (r"Tencent\\QQPinyin\\Cache", "QQ 拼音输入法缓存", "system_cache"),
    (r"Microsoft\\InputMethod\\Chs", "微软拼音输入法缓存", "system_cache"),

    # 设计办公
    (r"Adobe\\Common\\Cache", "Adobe 媒体公共缓存", "office_cache"),
    (r"Adobe\\Common\\Media Cache", "Adobe 媒体缓存核心文件", "office_cache"),
    (r"Adobe\\.*\\Cache", "Adobe (PS/LR 等) 独立缓存", "office_cache"),
    (r"Figma\\Cache", "Figma PC 客户端缓存", "office_cache"),
    (r"Sketch\\Cache", "Sketch PC 客户端缓存", "office_cache"),
    (r"XMind\\Cache", "XMind 思维导图缓存", "office_cache"),
    (r"Lanhu\\Cache", "蓝湖 PC 客户端缓存", "office_cache"),
    (r"Modao\\Cache", "墨刀 PC 客户端缓存", "office_cache"),

    # UWP
    (r"Packages\\[^\\]+\\(LocalCache|AC|TempState)", "UWP 应用临时与沙盒缓存", "app_cache"),
    (r"Packages\\[^\\]+\\LocalState\\Cache", "UWP 应用本地状态缓存", "app_cache"),
]

added = 0
for pat_str, desc, cat in new_rules_def:
    # 转换为标准的正则格式
    safe_pat = pat_str.replace("\\", "\\\\")
    full_pattern = f"^[Cc]:\\\\(Users\\\\[^\\\\]+\\\\|Windows\\\\|ProgramData\\\\|Program Files( \\(x86\\))?\\\\)?.*{safe_pat}"
    
    # 检查是否重复
    is_dup = False
    for ex_pat in existing_patterns:
        if safe_pat in ex_pat and ex_pat != full_pattern:
            is_dup = True
            break
        if ex_pat == full_pattern:
            is_dup = True
            break
            
    if not is_dup:
        rule = {
            "id": f"auto_ext_{added:03d}",
            "description": desc,
            "pattern": full_pattern,
            "risk_level": "LOW",
            "category": cat,
            "ai_advice": f"自动识别的 {desc} 数据，确认无误可安全清理以释放空间。",
            "is_checked_default": True
        }
        data["rules"].append(rule)
        existing_patterns.append(full_pattern)
        added += 1

with open(kb_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Added {added} extensive rules into file_kb.json!")
