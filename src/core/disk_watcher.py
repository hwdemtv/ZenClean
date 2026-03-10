"""
ZenClean 磁盘爆仓预警模块

功能：
    1. 检查 C 盘使用率，超过阈值弹出 Windows 原生 Toast 通知
    2. 注册/注销 Windows 任务计划程序定时任务
    3. 作为独立脚本可被任务计划程序直接调用

设计原则：
    - 零常驻进程：由 Windows 任务计划程序按计划唤醒
    - 零管理员权限：创建普通级别定时任务
    - 极轻量依赖：仅用标准库，不依赖 Flet 等重型框架
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────

_TASK_NAME = "ZenClean_DiskWatch"
_DEFAULT_THRESHOLD = 90  # 默认阈值：C 盘使用率超过 90% 触发预警
_CHECK_DRIVE = "C:\\"
_CONFIG_FILE = "zenclean_diskwatch.json"


def _get_config_path() -> Path:
    """获取配置文件路径（存放在用户 AppData 目录）"""
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = Path(app_data) / "ZenClean"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / _CONFIG_FILE


def _load_config() -> dict:
    """加载配置"""
    config_path = _get_config_path()
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"threshold": _DEFAULT_THRESHOLD}


def _save_config(config: dict) -> None:
    """保存配置"""
    config_path = _get_config_path()
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def check_disk(drive: str = _CHECK_DRIVE, threshold: int | None = None) -> tuple[bool, float, float]:
    """
    检查磁盘使用率。
    
    Returns:
        (is_warning, usage_percent, free_gb)
    """
    if threshold is None:
        threshold = _load_config().get("threshold", _DEFAULT_THRESHOLD)
    
    total, used, free = shutil.disk_usage(drive)
    usage_percent = (used / total) * 100
    free_gb = free / (1024 ** 3)
    
    return usage_percent >= threshold, round(usage_percent, 1), round(free_gb, 1)


def _escape_xml(text: str) -> str:
    """
    转义 XML 特殊字符，防止注入攻击。

    Args:
        text: 原始文本

    Returns:
        转义后的安全文本
    """
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


def send_toast(title: str, message: str) -> bool:
    """
    通过 PowerShell 弹出 Windows 原生 Toast 通知。
    不依赖任何第三方库。

    Args:
        title: 通知标题（会被转义以防注入）
        message: 通知内容（会被转义以防注入）

    Returns:
        是否成功发送
    """
    # 安全转义：防止 XML/PowerShell 注入攻击
    safe_title = _escape_xml(str(title))[:100]  # 限制长度
    safe_message = _escape_xml(str(message))[:200]  # 限制长度

    # 使用 PowerShell 的原生 .NET 通知
    # 注意：所有动态内容已通过 XML 实体编码转义
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
            capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        # 降级方案：使用 msg 命令（更简单但不够美观）
        try:
            # msg 命令也需要转义
            safe_msg = f"{safe_title}\n{safe_message}".replace('"', '')
            subprocess.run(
                ["msg", "*", safe_msg],
                capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except Exception:
            return False


def _get_script_command() -> str:
    """获取任务计划程序要执行的命令"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后：直接调用 exe 加 --disk-watch 参数
        return f'"{sys.executable}" --disk-watch'
    else:
        # 源码运行：用 pythonw 避免弹出黑窗
        this_file = os.path.abspath(__file__)
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        return f'"{pythonw}" "{this_file}"'


def register_task(interval_hours: int = 2) -> tuple[bool, str]:
    """
    注册 Windows 定时任务。
    
    Args:
        interval_hours: 检查间隔（小时）
    
    Returns:
        (success, message)
    """
    command = _get_script_command()
    
    try:
        # /F 表示强制覆盖已有同名任务
        result = subprocess.run(
            [
                "schtasks", "/Create",
                "/TN", _TASK_NAME,
                "/TR", command,
                "/SC", "HOURLY",
                "/MO", str(interval_hours),
                "/F"
            ],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            return True, f"磁盘预警任务已注册（每 {interval_hours} 小时检查一次）"
        else:
            return False, f"注册失败: {result.stderr.strip()}"
    except Exception as e:
        return False, f"注册失败: {type(e).__name__}"


def unregister_task() -> tuple[bool, str]:
    """注销定时任务"""
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", _TASK_NAME, "/F"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            return True, "磁盘预警任务已注销"
        else:
            return False, f"注销失败: {result.stderr.strip()}"
    except Exception as e:
        return False, f"注销失败: {type(e).__name__}"


def is_task_registered() -> bool:
    """检测定时任务是否已注册"""
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", _TASK_NAME],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        return False


def set_threshold(value: int) -> None:
    """设置预警阈值（0-100）"""
    config = _load_config()
    config["threshold"] = max(50, min(99, value))
    _save_config(config)


def get_threshold() -> int:
    """获取当前预警阈值"""
    return _load_config().get("threshold", _DEFAULT_THRESHOLD)


# ── 独立运行入口（被任务计划程序调用时执行） ──────────────────────────────

if __name__ == "__main__":
    is_warning, usage, free_gb = check_disk()
    
    if is_warning:
        send_toast(
            "⚠️ ZenClean 磁盘预警",
            f"C 盘使用率已达 {usage}%，仅剩 {free_gb} GB 可用空间。\n建议立即打开 ZenClean 进行清理。"
        )
