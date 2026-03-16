import json

path = r"D:\软件开发\ZenClean\src\config\file_kb.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

new_rules = [
      {
        "id": "wechat_msg_cache_001",
        "description": "微信消息图片缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\Documents\\\\WeChat Files\\\\[^\\\\]+\\\\FileStorage\\\\MsgAttach\\\\Temp\\\\",
        "risk_level": "LOW",
        "category": "social_cache",
        "ai_advice": "微信消息临时图片缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "wechat_xplugin_001",
        "description": "微信小程序缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Roaming\\\\Tencent\\\\WeChat\\\\XPlugin\\\\",
        "risk_level": "LOW",
        "category": "social_cache",
        "ai_advice": "微信小程序运行缓存，清理后小程序需重新加载。",
        "is_checked_default": True
      },
      {
        "id": "douyin_cache_001",
        "description": "抖音 PC 客户端缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Local\\\\Douyin\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "app_cache",
        "ai_advice": "抖音视频预加载缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "jianying_cache_001",
        "description": "剪映缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Local\\\\JianyingPro\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "app_cache",
        "ai_advice": "剪映草稿缓存与预览文件，清理后需重新生成。",
        "is_checked_default": True
      },
      {
        "id": "wps_cache_001",
        "description": "WPS Office 缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Roaming\\\\Kingsoft\\\\WPS Office\\\\.*\\\\cache\\\\",
        "risk_level": "LOW",
        "category": "app_cache",
        "ai_advice": "WPS 临时文件与备份缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "qqbrowser_cache_001",
        "description": "QQ 浏览器缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Local\\\\Tencent\\\\QQBrowser\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "browser_cache",
        "ai_advice": "QQ 浏览器网页缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "sogou_browser_cache_001",
        "description": "搜狗浏览器缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Roaming\\\\SogouExplorer\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "browser_cache",
        "ai_advice": "搜狗浏览器网页缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "360_browser_cache_001",
        "description": "360 安全浏览器缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Local\\\\360Chrome\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "browser_cache",
        "ai_advice": "360 浏览器网页缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "aliwangwang_cache_001",
        "description": "阿里旺旺缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Roaming\\\\AliWangWang\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "social_cache",
        "ai_advice": "阿里旺旺聊天图片缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "dingtalk_file_cache_001",
        "description": "钉钉文件缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Roaming\\\\DingTalk\\\\.*\\\\FileCache\\\\",
        "risk_level": "LOW",
        "category": "social_cache",
        "ai_advice": "钉钉接收的文件缓存，清理不影响原始文件。",
        "is_checked_default": True
      },
      {
        "id": "steam_cache_001",
        "description": "Steam 网页缓存",
        "pattern": "^[Cc]:\\\\Program Files \\(x86\\)\\\\Steam\\\\appcache\\\\",
        "risk_level": "LOW",
        "category": "app_cache",
        "ai_advice": "Steam 商店页面缓存，可安全清理。",
        "is_checked_default": True
      },
      {
        "id": "wegame_cache_001",
        "description": "WeGame 缓存",
        "pattern": "^[Cc]:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Roaming\\\\Tencent\\\\WeGame\\\\.*\\\\Cache\\\\",
        "risk_level": "LOW",
        "category": "app_cache",
        "ai_advice": "WeGame 游戏平台缓存，可安全清理。",
        "is_checked_default": True
      }
]

existing_ids = {r["id"] for r in data["rules"]}
added = 0
for r in new_rules:
    if r["id"] not in existing_ids:
        data["rules"].append(r)
        added += 1

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Added {added} rules to file_kb.json")
