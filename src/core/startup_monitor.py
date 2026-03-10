"""
轻量级系统盘爆仓监控与气泡预警脚本
作为独立进程在开机时 (或由主程序拉起) 运行。
仅利用 Windows 原生 PowerShell (无需安装额外 C# 通知库)，避免污染打包体积。
检查完 C 盘后即刻自毁退出，不在后台长期驻留。
"""

import sys
import shutil
import subprocess

# 默认触发阈值（当 C 盘使用率大于该比例时报警，或者是剩余容量绝对值小于 15GB 时双条件触发）
DEFAULT_THRESHOLD_PERCENT = 90
DEFAULT_MIN_FREE_GB = 15.0

def _get_threshold_percent() -> int:
    """尝试读取用户在设置页里保存的阈值配置，降级回默认值。"""
    try:
        from core.disk_watcher import get_threshold
        # 这里可能是在非 Flet 环境下跑（如果独立拉起），但 settings 相关的读取通常只是操作 json。
        return get_threshold()
    except Exception:
        return DEFAULT_THRESHOLD_PERCENT


def show_toast(title: str, message: str) -> None:
    """
    通过 PowerShell 原生的 BurntToast 或者单纯的 Registry/UI 接口弹窗。
    由于部分精简版 Win 不带 BurntToast 模块，我们采用最稳定的
    Reflection 装载 Windows.UI.Notifications
    """
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $APP_ID = "{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe"

    $template = @"
    <toast duration="long">
        <visual>
            <binding template="ToastText02">
                <text id="1">{title}</text>
                <text id="2">{message}</text>
            </binding>
        </visual>
    </toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
    """

    # 使用 no_console 标志后台静默执行
    # DETACHED_PROCESS = 0x00000008
    # CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        creationflags=0x08000000
    )


def run_check() -> None:
    """执行硬盘检查与提醒"""
    try:
        total, used, free = shutil.disk_usage("C:\\")
        
        total_gb = total / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        
        # 对于 0 字节等异常做防除零
        if total_gb <= 0:
            return

        used_percent = (used_gb / total_gb) * 100
        threshold = _get_threshold_percent()

        if used_percent >= threshold or free_gb < DEFAULT_MIN_FREE_GB:
            # 命中气泡条件
            title = "ZenClean 禅清 - 存储空间红色预警"
            msg = f"C 盘仅剩 {free_gb:.1f} GB 空间！\n(已使用 {used_percent:.1f}%)，建议立刻开启极限深层清理。"
            show_toast(title, msg)
        
    except Exception as e:
        # 这个脚本必须是静默的，即便是崩溃也不可以弹出刺眼的 Traceback 窗口
        pass

if __name__ == "__main__":
    run_check()
    sys.exit(0)
