# ZenClean 系统通知与应用更新模块技术文档

本文档详细介绍了 ZenClean 项目中系统通知模块和应用更新模块的实现方案，供其他 Python Windows 桌面应用参考。

---

## 目录

- [一、系统通知模块](#一系统通知模块)
  - [1.1 Windows 原生 Toast 通知](#11-windows-原生-toast-通知)
  - [1.2 应用内卡片式通知](#12-应用内卡片式通知)
  - [1.3 系统托盘集成](#13-系统托盘集成)
- [二、应用更新模块](#二应用更新模块)
  - [2.1 版本检查核心逻辑](#21-版本检查核心逻辑)
  - [2.2 自动更新检查](#22-自动更新检查)
  - [2.3 手动更新检查](#23-手动更新检查)
- [三、最佳实践总结](#三最佳实践总结)

---

## 一、系统通知模块

ZenClean 实现了三种通知机制，覆盖不同场景：

| 通知类型 | 适用场景 | 实现方式 |
|---------|---------|---------|
| Windows 原生 Toast | 后台预警、系统级通知 | PowerShell + WinRT API |
| 应用内卡片 | 应用内交互、更新提示 | Flet UI 组件 |
| 系统托盘 | 后台驻留、快捷入口 | pystray 库 |

### 1.1 Windows 原生 Toast 通知

#### 设计原则

- **零常驻进程**：由 Windows 任务计划程序按计划唤醒
- **零管理员权限**：创建普通级别定时任务
- **极轻量依赖**：仅用标准库，不依赖第三方 Toast 库

#### 核心实现

**文件**: `src/core/disk_watcher.py`

```python
def send_toast(title: str, message: str) -> bool:
    """
    通过 PowerShell 弹出 Windows 原生 Toast 通知。
    不依赖任何第三方库。
    """
    # 1. 安全转义：防止 XML/PowerShell 注入攻击
    safe_title = _escape_xml(str(title))[:100]
    safe_message = _escape_xml(str(message))[:200]

    # 2. 使用 PowerShell 调用 Windows Runtime API
    ps_script = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

    $template = @"
    <toast>
        <visual>
            <binding template="ToastGeneric">
                <text>{safe_title}</text>
                <text>{safe_message}</text>
            </binding>
        </visual>
    </toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ZenClean").Show($toast)
    '''

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True, timeout=10, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        # 3. 降级方案：使用 msg 命令
        try:
            safe_msg = f"{safe_title}\n{safe_message}".replace('"', '')
            subprocess.run(
                ["msg", "*", safe_msg],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except Exception:
            return False
```

#### XML 转义函数

```python
def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符，防止注入攻击"""
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\n", "&#10;")
        .replace("\r", "&#13;"))
```

#### 任务计划程序集成

```python
def register_task(interval_hours: int = 2) -> tuple[bool, str]:
    """注册 Windows 定时任务"""
    command = _get_script_command()
    
    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", "ZenClean_DiskWatch",  # 任务名称
            "/TR", command,                # 执行命令
            "/SC", "HOURLY",               # 调度类型
            "/MO", str(interval_hours),    # 间隔
            "/F"                           # 强制覆盖
        ],
        capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    return result.returncode == 0, "结果消息"
```

#### 独立运行入口

```python
# 作为独立脚本被任务计划程序调用
if __name__ == "__main__":
    is_warning, usage, free_gb = check_disk()
    
    if is_warning:
        send_toast(
            "⚠️ ZenClean 磁盘预警",
            f"C 盘使用率已达 {usage}%，仅剩 {free_gb} GB 可用空间。"
        )
```

### 1.2 应用内卡片式通知

#### 适用场景

- 应用更新提示
- 服务器广播消息
- 用户操作反馈

#### 核心实现

**文件**: `src/ui/app.py`

```python
def show_notification(self, title: str, content: str, icon: str = ft.icons.INFO, actions: list = None):
    """
    在顶部通知区域挂载一个简洁的交互卡片
    
    :param actions: list of (label, on_click_func, is_primary)
    """
    # 1. 构建操作按钮
    action_buttons = []
    if actions:
        for label, func, is_prim in actions:
            if is_prim:
                action_buttons.append(
                    ft.ElevatedButton(
                        label, 
                        on_click=lambda _, f=func: f(), 
                        bgcolor=COLOR_ZEN_PRIMARY, 
                        color="white"
                    )
                )
            else:
                action_buttons.append(
                    ft.TextButton(label, on_click=lambda _, f=func: f())
                )

    # 2. 构建通知卡片
    notification_card = ft.Container(
        content=ft.Row([
            ft.Icon(icon, color=COLOR_ZEN_PRIMARY, size=24),
            ft.Column([
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD),
                ft.Text(content, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=2, expand=True),
            ft.Row(action_buttons, spacing=10),
            ft.IconButton(ft.icons.CLOSE, on_click=_close_notice)
        ]),
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
        bgcolor=ft.colors.with_opacity(0.1, COLOR_ZEN_PRIMARY),
        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLOR_ZEN_PRIMARY)),
        border_radius=10,
    )

    # 3. 挂载到通知区域
    self._notification_column.controls.insert(0, notification_card)
    self._notification_column.update()
```

#### 使用示例

```python
# 显示更新通知
self.show_notification(
    title="发现新版本 v1.2.0",
    content="修复了若干已知问题，提升扫描速度...",
    icon=ft.icons.SYSTEM_UPDATE,
    actions=[
        ("立即更新", lambda: self.page.launch_url(url), True),   # 主按钮
        ("查看日志", lambda: show_changelog(), False)            # 次按钮
    ]
)
```

#### 服务器广播通知处理

```python
def process_server_notification(self, note: dict):
    """处理来自后端的广播通知，实现去重与强/弱提醒分离"""
    # 1. 生成唯一标识用于去重
    notice_fingerprint = f"{note.get('id')}_{hash(note.get('content', ''))}"
    last_fingerprint = self.page.client_storage.get("last_notice_fingerprint")
    
    if last_fingerprint == notice_fingerprint:
        return  # 已展示过，跳过

    # 2. 区分强制/非强制通知
    if note.get("is_force", False):
        # 强制弹窗
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(note.get("title", "系统消息")),
            content=ft.Markdown(note.get("content", "")),
            actions=[ft.TextButton("我知道了", on_click=close)]
        )
        self.page.overlay.append(dlg)
        dlg.open = True
    else:
        # 非强制卡片通知
        self.show_notification(
            title=note.get("title"),
            content=note.get("content", "")[:50],
            icon=ft.icons.NOTIFICATIONS
        )
    
    # 3. 记录已展示
    self.page.client_storage.set("last_notice_fingerprint", notice_fingerprint)
```

### 1.3 系统托盘集成

#### 核心实现

**文件**: `src/ui/tray_manager.py`

```python
import pystray
from PIL import Image

class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, page: ft.Page, app_instance, icon_path: str):
        self.page = page
        self.app = app_instance
        self.icon_path = icon_path
    
    def _create_menu(self):
        """创建右键菜单"""
        return pystray.Menu(
            pystray.MenuItem("打开主界面", self._show_window, default=True),
            pystray.MenuItem("一键健康扫描", self._quick_scan),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("彻底退出进程", self._exit_app)
        )

    def _show_window(self, icon=None, item=None):
        """显示窗口"""
        async def _action():
            self.page.window.visible = True
            self.page.window.minimized = False
            self.page.window.to_front()
            self.page.update()
        self.page.run_task(_action)

    def _exit_app(self, icon=None, item=None):
        """退出应用（三保险模式）"""
        # 保险 1：哨兵线程确保退出
        def _forced_sentinel():
            time.sleep(1.0)
            os._exit(0)
        threading.Thread(target=_forced_sentinel, daemon=False).start()

        # 保险 2：优雅关闭 Flet 窗口
        self.page.window.prevent_close = False
        self.page.window.close()

        # 保险 3：直接退出
        time.sleep(0.5)
        os._exit(0)

    def run(self):
        """启动托盘线程"""
        image = Image.open(self.icon_path)
        self.icon = pystray.Icon(
            "ZenClean",
            image,
            "禅清 (ZenClean)",
            menu=self._create_menu()
        )
        
        threading.Thread(target=self.icon.run, daemon=True).start()
```

---

## 二、应用更新模块

### 2.1 版本检查核心逻辑

#### 双重检查机制

ZenClean 采用"商业网关优先 + GitHub 镜像降级"的双重检查机制：

```
┌─────────────────────────────────────────────────────────────┐
│                    版本检查流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 商业授权网关 (优先)                                     │
│      ├── 成功：返回版本信息                                  │
│      └── 失败 (超时/错误)：进入降级流程                       │
│                                                             │
│   2. GitHub Releases 镜像 (降级)                            │
│      ├── 镜像 1: api.kkgithub.com                          │
│      ├── 镜像 2: gh-api.99988866.xyz                       │
│      ├── 镜像 3: ghapi.paniy.xyz                           │
│      └── 镜像 4: api.github.com (官方)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 核心实现

**文件**: `src/core/updater.py`

```python
import threading
import requests
from config.settings import LICENSE_SERVER_URLS, FALLBACK_DOWNLOAD_URL
from config.version import __version__ as APP_VERSION

def check_for_updates(on_result, manual=False):
    """
    异步检查是否有新版本。
    
    :param on_result: 回调函数 `def callback(has_new, version, url, msg)`
    :param manual: 是否为用户手动点击（手动点击即使无更新也要反馈）
    """
    def _check():
        try:
            # ===== 第一阶段：商业授权网关 =====
            if LICENSE_SERVER_URLS:
                base_url = LICENSE_SERVER_URLS[0].rstrip("/")
                update_api = f"{base_url}/api/v1/auth/update?product=zenclean&version={APP_VERSION}"
                
                # 重试机制应对瞬时网络抖动
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        res = requests.get(update_api, timeout=3)
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("code") == 200 and data.get("data"):
                                d = data["data"]
                                if d.get("has_update") and d.get("version") != APP_VERSION:
                                    on_result(
                                        True, 
                                        d.get("version"), 
                                        d.get("url") or FALLBACK_DOWNLOAD_URL, 
                                        d.get("desc", "发现新版本！")
                                    )
                                    return
                                elif manual:
                                    on_result(False, APP_VERSION, "", "当前已是最新版本")
                                    return
                            break  # 响应格式不对，不再重试
                        elif 400 <= res.status_code <= 599:
                            break  # 服务端错误，进入降级
                    except (requests.Timeout, requests.ConnectionError):
                        if attempt == max_retries - 1:
                            break

            # ===== 第二阶段：GitHub 镜像降级 =====
            MIRRORS = [
                "https://api.kkgithub.com/repos/OWNER/REPO/releases",
                "https://gh-api.99988866.xyz/repos/OWNER/REPO/releases",
                "https://ghapi.paniy.xyz/repos/OWNER/REPO/releases",
                "https://api.github.com/repos/OWNER/REPO/releases"
            ]
            
            headers = {'User-Agent': f'App-Client/{APP_VERSION}'}
            for mirror_url in MIRRORS:
                try:
                    res = requests.get(mirror_url, timeout=6, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        if data and isinstance(data, list):
                            latest_release = data[0]  # 列表第一个即最新
                            latest_version = latest_release.get("tag_name", "").lstrip("v")
                            current_clean = APP_VERSION.lstrip("v")
                            
                            if latest_version and latest_version != current_clean:
                                on_result(
                                    True,
                                    latest_version,
                                    FALLBACK_DOWNLOAD_URL,
                                    latest_release.get("body", "发现新版本")
                                )
                                return
                            elif manual:
                                on_result(False, APP_VERSION, "", "当前已是最新版本")
                                return
                except Exception:
                    continue

            # 所有检查都失败
            if manual:
                on_result(False, APP_VERSION, "", "版本检测链路波动，请稍后再试")

        except Exception as e:
            if manual:
                on_result(False, APP_VERSION, "", f"检查更新异常: {e}")

    # 异步执行
    threading.Thread(target=_check, daemon=True).start()
```

#### 版本配置

**文件**: `src/config/version.py`

```python
__version__ = "0.1.6-beta"
__app_name__ = "ZenClean"
__display_name__ = "禅清"
__build_date__ = "2026-03-28"
```

**文件**: `src/config/settings.py`

```python
# 更新检查相关
UPDATE_CHECK_URL = "https://api.github.com/repos/OWNER/REPO/releases/latest"
FALLBACK_DOWNLOAD_URL = "https://your-download-page.com"
```

### 2.2 自动更新检查

#### 实现要点

- 启动后延迟 8 秒检查，避免抢占资源
- 非侵入式，不打断用户操作
- 发现新版本显示顶部通知卡片

#### 核心实现

**文件**: `src/ui/app.py`

```python
def _start_silent_update_check(self):
    """启动时静默检查更新"""
    from core.updater import check_for_updates
    
    def _silent_callback(has_new, latest_version, url, msg):
        if has_new:
            def _ui_update():
                # 提取第一行作为摘要
                summary = msg.split('\n')[0][:60]
                if len(msg.split('\n')) > 1 or len(msg) > 60:
                    summary += "..."
                    
                self.show_notification(
                    title=f"发现新版本 v{latest_version}",
                    content=summary,
                    icon=ft.icons.SYSTEM_UPDATE,
                    actions=[
                        ("立即更新", lambda: self.page.launch_url(url), True),
                        ("查看日志", lambda: self._show_markdown_dialog(
                            f"更新日志 v{latest_version}", msg
                        ), False)
                    ]
                )
            
            if self.page:
                self.page.run_task(_ui_update)
    
    def _delayed_check():
        time.sleep(8)  # 避开启动首屏资源高峰
        check_for_updates(_silent_callback, manual=False)
        
    threading.Thread(target=_delayed_check, daemon=True).start()
```

### 2.3 手动更新检查

#### UI 入口实现

```python
def _on_check_update_click(self, e):
    """用户点击检查更新按钮"""
    btn = e.control
    btn.disabled = True
    btn.text = "正在检查..."
    self.update()

    def _update_callback(has_new, latest_version, url, msg):
        def _ui_update():
            btn.disabled = False
            btn.text = "检查更新"
            self.update()
            
            if has_new:
                # 显示更新对话框
                dlg = ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.icons.SYSTEM_UPDATE, color=COLOR_ZEN_PRIMARY),
                        ft.Text("发现新版本")
                    ]),
                    content=ft.Column([
                        ft.Text(f"最新版本：{latest_version}", weight=ft.FontWeight.BOLD),
                        ft.Text(f"当前版本：v{APP_VERSION}"),
                        ft.Text("更新内容：", color=COLOR_ZEN_TEXT_DIM),
                        ft.Text(msg, size=13, selectable=True),
                    ]),
                    actions=[
                        ft.ElevatedButton("去下载", on_click=lambda _: self.page.launch_url(url)),
                        ft.TextButton("稍后再说", on_click=lambda _: close_dialog())
                    ],
                )
                self.page.overlay.append(dlg)
                dlg.open = True
                self.page.update()
            else:
                # 显示 SnackBar 提示
                self.page.snack_bar = ft.SnackBar(ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

        self.page.run_task(_ui_update)

    check_for_updates(_update_callback, manual=True)
```

---

## 三、最佳实践总结

### 系统通知模块

| 实践 | 说明 |
|------|------|
| **安全转义** | 对动态内容进行 XML 转义，防止注入攻击 |
| **降级方案** | Toast 失败时降级到 `msg` 命令 |
| **长度限制** | 标题限制 100 字符，内容限制 200 字符 |
| **去重机制** | 使用指纹标识避免重复展示 |
| **强/弱分离** | 强制通知弹窗，非强制通知卡片 |
| **零依赖** | 使用 PowerShell 调用 WinRT，无需第三方库 |

### 应用更新模块

| 实践 | 说明 |
|------|------|
| **双重检查** | 商业网关优先 + GitHub 镜像降级 |
| **重试机制** | 网络抖动时自动重试 2 次 |
| **超时控制** | 商业网关 3 秒，镜像源 6 秒 |
| **静默检查** | 启动后延迟 8 秒，避免抢占资源 |
| **手动反馈** | 手动检查时即使无更新也要反馈 |
| **异步执行** | 在后台线程执行，不阻塞 UI |

### 文件结构参考

```
src/
├── config/
│   ├── settings.py      # 配置常量
│   └── version.py       # 版本号定义
├── core/
│   ├── disk_watcher.py  # Toast 通知 + 任务计划
│   └── updater.py       # 版本检查核心
└── ui/
    ├── app.py           # 应用内通知 + 自动检查
    └── tray_manager.py  # 系统托盘
```

---

## 附录：关键代码速查

### 发送 Toast 通知

```python
from core.disk_watcher import send_toast

send_toast("标题", "消息内容")
```

### 检查更新

```python
from core.updater import check_for_updates

def on_result(has_new, version, url, msg):
    if has_new:
        print(f"发现新版本: {version}")
        print(f"下载地址: {url}")
    else:
        print(msg)

check_for_updates(on_result, manual=True)
```

### 显示应用内通知

```python
app.show_notification(
    title="标题",
    content="内容",
    icon=ft.icons.INFO,
    actions=[
        ("按钮1", lambda: action1(), True),   # 主按钮
        ("按钮2", lambda: action2(), False),  # 次按钮
    ]
)
```

---

*文档版本: 1.0 | 最后更新: 2026-04-01*
