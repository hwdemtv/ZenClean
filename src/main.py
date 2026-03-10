import os
import sys
import flet as ft
from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_PRIMARY, WINDOW_WIDTH, WINDOW_HEIGHT
)
from ui.app import ZenCleanApp
from ui.tray_manager import TrayManager

# 动态获取项目根目录或打包后的临时目录
if getattr(sys, 'frozen', False):
    _ROOT = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
else:
    _ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_ASSETS_DIR = os.path.join(_ROOT, "assets")
_ICON_PATH = os.path.join(_ASSETS_DIR, "icon.ico")

import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--analyze", type=str, help="Auto analyze directory path")
_parser.add_argument("--disk-watch", action="store_true", help="Run background disk check and exit")
_parser.add_argument("--tray-only", action="store_true", help="Start minimized to tray")
_args, _ = _parser.parse_known_args()
_auto_scan_path = _args.analyze
_is_disk_watch = _args.disk_watch
_is_tray_only = _args.tray_only

def main(page: ft.Page):
    # ── 0. 瞬间关闭 PyInstaller 启动闪屏 ──────────────────────────────────────
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    # ── 1. 原生 Flet 亮/暗动态双主题装配 ──────────────────────────────────────
    # 夜间：护眼赛博机甲风
    dark_scheme = ft.ColorScheme(
        background="#13161A",
        surface="#1C2028",
        primary="#00BFA5",
        secondary="#E8C361",
        error="#EF5350",
        outline="#242A35",
        on_surface="#F2F5F9",
        on_surface_variant="#A3AAB8",
        tertiary="#FFB020"
    )
    # 日间：实验舱医疗风
    light_scheme = ft.ColorScheme(
        background="#F5F7FA",
        surface="#FFFFFF",
        primary="#009688",
        secondary="#C49B27",
        error="#D32F2F",
        outline="#E5E8EB",
        on_surface="#1A1F2B",
        on_surface_variant="#6B7280",
        tertiary="#D97706"
    )
    
    # 根据本地缓存设定期望模式，默认为 DARK
    saved_theme = page.client_storage.get("zen_theme_mode") or "dark"
    page.theme_mode = ft.ThemeMode.DARK if saved_theme == "dark" else ft.ThemeMode.LIGHT
    
    page.theme = ft.Theme(color_scheme=light_scheme, use_material3=True)
    page.dark_theme = ft.Theme(color_scheme=dark_scheme, use_material3=True)
    
    page.bgcolor = "background"
    page.padding = 0

    page.title = "禅清 (ZenClean) ：互为螺旋- C盘AI极速清理大师"
    
    # ── 2. 预设窗口沉浸式风格 ───────────────────────────────────────────
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = False 

    # Windows 桌面端需要绝对路径指向 .ico 文件
    if os.path.isfile(_ICON_PATH):
        page.window.icon = _ICON_PATH

    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT + 40 # 增加一点高度给自定义顶栏
    page.window.min_width = 800
    page.window.min_height = 600
    
    # ── 3. 强制居中：对齐 Splash 闪屏的位置，实现视觉无缝过渡 ────────────
    page.window.center()

    # 窗口事件核心监听 (劫持退出按钮)
    def _on_window_event(e: ft.ControlEvent):
        if e.data == "close":
            page.window.visible = False
            page.update()
        
    page.window.prevent_close = True
    # 将静态资源根目录存入 client_storage，方便跨视图稳健加载 icon/图片
    page.client_storage.set("assets_dir", _ASSETS_DIR)

    app = ZenCleanApp(page, auto_scan_path=_auto_scan_path)
    # 初始化并启动托盘服务
    tray = TrayManager(page, app, assets_dir=_ASSETS_DIR)
    tray.run()
    
    # 如果是随系统自启，则默认隐藏窗口直接沉底托盘
    if _is_tray_only:
        page.window.visible = False
        page.update()
    
    # ── 4. IPC 监听守护线程（仅主实例运行） ────────────────────────────────
    _IPC_ADDR = ('127.0.0.1', 19528)
    def _listen_ipc():
        from multiprocessing.connection import Listener
        try:
            with Listener(_IPC_ADDR) as listener:
                while True:
                    try:
                        with listener.accept() as conn:
                            msg = conn.recv()
                            if isinstance(msg, dict) and msg.get('action') == 'analyze':
                                path = msg.get('path')
                                if path and hasattr(app, "trigger_auto_scan"):
                                    app.trigger_auto_scan(path)
                    except Exception:
                        pass
        except Exception:
            pass

    import threading
    ipc_thread = threading.Thread(target=_listen_ipc, daemon=True)
    ipc_thread.start()
    
    # ── 5. 后台静默沙箱清理守护线程 ────────────────────────────────────────
    def _auto_clean_background():
        import time
        from core.quarantine import auto_clean_expired
        from core.logger import logger
        # 延迟 15 秒后执行，避免抢占主程序冷启动期的 CPU 和 I/O 资源
        time.sleep(15)
        try:
            freed = auto_clean_expired()
            if freed > 0:
                logger.info(f"Background quarantine auto-clean completed, freed {freed / (1024*1024):.2f} MB")
        except Exception as e:
            logger.error(f"Background auto-clean failed: {e}")

    clean_thread = threading.Thread(target=_auto_clean_background, daemon=True)
    clean_thread.start()
    
    page.add(app)
    
    # ── 6. EULA 强制免责逻辑 ────────────────────────────────────────────────
    def _start_app_logic():
        # ft.Column 不参与 Flet 路由系统，直接调用自己的导航方法
        app.navigate_to("/")
        page.update()

    # 检查本地是否已接受过 EULA
    if page.client_storage.get("zen_eula_accepted"):
        _start_app_logic()
    else:
        # 首次启动，强制弹出 EULA 对话框
        from ui.components.dialogs import show_eula_dialog
        show_eula_dialog(page, on_accepted=_start_app_logic)
    
    page.update()


if __name__ == "__main__":
    # ── 关键 1: 必须放在所有逻辑的最前面 ────────────────────
    # 否则 PyInstaller 打包后的子进程也会疯狂弹出 UAC 提权
    import multiprocessing
    multiprocessing.freeze_support()

    import ctypes
    import sys

    # ── 拦截底权无头监控探测任务 (无需 UI 且无需 UAC) ─────────
    if _is_disk_watch:
        try:
            from core.startup_monitor import run_check
            run_check()
        except Exception:
            pass
        sys.exit(0)

    # ── 单实例锁：防止右键菜单等场景重复启动 ──────────────────────────────
    # 使用 Windows 命名互斥锁（Named Mutex），由内核管理，进程崩溃自动释放
    _MUTEX_NAME = "Global\\ZenClean_SingleInstance_Mutex"
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    _last_error = ctypes.windll.kernel32.GetLastError()
    _ERROR_ALREADY_EXISTS = 183

    if _last_error == _ERROR_ALREADY_EXISTS:
        import sys as _sys
        # 从顶层模块获取 _auto_scan_path（因为这里的代码不在函数内，当前在 __main__ 顶级域运行）
        auto_path = getattr(_sys.modules[__name__], '_auto_scan_path', None)
        if auto_path:
            # 通过 TCP 本地回环发送给主实例
            try:
                from multiprocessing.connection import Client
                with Client(('127.0.0.1', 19528)) as conn:
                    conn.send({'action': 'analyze', 'path': auto_path})
            except Exception:
                pass # 通信失败静默退出
            sys.exit(0)
        else:
            # 已有实例在运行且没有强制分析参数，正常弹出提示后退出
            ctypes.windll.user32.MessageBoxW(
                0,
                "ZenClean 已在运行中。\n\n请切换到已打开的窗口继续操作。",
                "ZenClean - 重复启动",
                0x00000040  # MB_ICONINFORMATION
            )
            sys.exit(0)

    # ── UAC 自动提权逻辑 ──────────────────────────────────────────────────
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

    if not is_admin():
        # ── 关键 2: 区分开发环境 (.py) 和打包后 (.exe) 的路径处理 ────────────
        if getattr(sys, 'frozen', False):
            # 打包后，直接拉起自己
            script = sys.executable
            params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
            target_cmd = script
        else:
            # 开发阶段，利用 sys.executable (如 python.exe) 拉起脚本
            script = sys.argv[0]
            params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
            target_cmd = sys.executable
            params = f'"{script}" {params}'

        try:
            # 以 runas (管理员) 模式重新启动程序
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", target_cmd, params, None, 1
            )
            # return code > 32 意味着提权且进程启动成功
            if int(ret) > 32:
                sys.exit(0)  # 父进程（低权）功成身退
            else:
                # 提权被用户拒绝 (User Cancelled) 或发生错误
                msg = (
                    "ZenClean 未获取管理员权限。\n\n"
                    "您可以继续在普通模式下运行，基础检查不受影响，但【深度系统休眠瘦身】与【C 盘核心系统区扫描】等高阶指令将无法执行。\n\n"
                    "是否继续以受限模式启动？"
                )
                # MB_ICONWARNING (0x30) | MB_YESNO (0x04) = 0x34
                # YES (6), NO (7)
                res = ctypes.windll.user32.MessageBoxW(0, msg, "ZenClean - 降权运行提示", 0x34)
                if res != 6:
                    sys.exit(0) # 用户选择不继续，安静退出
        except Exception as e:
            # 异常情况，同理降级运行
            pass

    # ── 0. 瞬间关闭 PyInstaller 启动闪屏 ──────────────────────────────────────
    # 必须在确定当前进程（无论是刚拉起的高权，还是降级的低权）是主执行进程时才关闭 splash
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    # ── VC++ 运行库检测逻辑 ───────────────────────────────────────────────
    def check_vcpp_redist():
        try:
            ctypes.WinDLL("vcruntime140.dll")
            ctypes.WinDLL("msvcp140.dll")
            return True
        except OSError:
            return False

    if not check_vcpp_redist():
        msg = (
            "ZenClean 启动失败：系统缺少必要的 Visual C++ 运行库组件。\n\n"
            "是否立即打开浏览器前往微软官网下载安装程序？"
        )
        result = ctypes.windll.user32.MessageBoxW(0, msg, "ZenClean - 缺少运行库", 0x00000004 | 0x00000020)
        if result == 6:
            import webbrowser
            webbrowser.open("https://aka.ms/vs/17/release/vc_redist.x64.exe")
        sys.exit(1)

    # ── 进程退出清理机制 ───────────────────────────────────────────────────
    import atexit
    def cleanup_on_exit():
        try:
            from multiprocessing import active_children
            for child in active_children():
                child.terminate()
        except Exception:
            pass
    atexit.register(cleanup_on_exit)

    # 正式拉起应用
    ft.app(target=main, assets_dir=_ASSETS_DIR)

