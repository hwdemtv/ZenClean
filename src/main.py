import os
import sys
import flet as ft
from config.settings import (
    COLOR_ZEN_BG, COLOR_ZEN_PRIMARY, WINDOW_WIDTH, WINDOW_HEIGHT
)
from ui.app import ZenCleanApp

# 动态获取项目根目录或打包后的临时目录
if getattr(sys, 'frozen', False):
    _ROOT = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
else:
    _ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_ASSETS_DIR = os.path.join(_ROOT, "assets")
_ICON_PATH = os.path.join(_ASSETS_DIR, "icon.ico")


def main(page: ft.Page):
    # ── 0. 瞬间关闭 PyInstaller 启动闪屏 ──────────────────────────────────────
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    # ── 1. 立即设置深色主题与背景（防止白/灰闪的最有效方案） ──────────────
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COLOR_ZEN_BG
    page.theme = ft.Theme(color_scheme_seed=COLOR_ZEN_PRIMARY, use_material3=True)
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

    app = ZenCleanApp(page)
    # 将静态资源根目录存入 client_storage，方便跨视图稳健加载 icon/图片
    page.client_storage.set("assets_dir", _ASSETS_DIR)
    
    page.add(app)
    # ft.Column 不参与 Flet路由系统，直接调用自己的导航方法
    app.navigate_to("/")
    page.update()


if __name__ == "__main__":
    # ── 关键 1: 必须放在所有逻辑(包含 UAC 提权前)的最开头 ────────────────────
    # 否则 PyInstaller 打包后的子进程也会疯狂弹出 UAC 提权
    import multiprocessing
    multiprocessing.freeze_support()

    import ctypes

    # ── VC++ 运行库检测逻辑 ───────────────────────────────────────────────
    def check_vcpp_redist():
        try:
            # 尝试加载关键的 C++ 运行库，缺失会抛出 OSError
            ctypes.WinDLL("vcruntime140.dll")
            ctypes.WinDLL("msvcp140.dll")
            return True
        except OSError:
            return False

    def show_vcpp_error_and_exit():
        msg = (
            "ZenClean 启动失败：系统缺少必要的 Visual C++ 运行库组件。\n\n"
            "是否立即打开浏览器前往微软官网下载安装程序？\n\n"
            "（提示：安装完成后无需重启，即可正常使用。下个版本我们将支持全自动静默修复。）"
        )
        # 0x00000004 = MB_YESNO, 0x00000020 = MB_ICONQUESTION
        result = ctypes.windll.user32.MessageBoxW(0, msg, "ZenClean - 缺少运行库", 0x00000004 | 0x00000020)
        
        if result == 6:  # 6 = IDYES
            import webbrowser
            webbrowser.open("https://aka.ms/vs/17/release/vc_redist.x64.exe")
        
        sys.exit(1)

    if not check_vcpp_redist():
        show_vcpp_error_and_exit()

    # ── UAC 自动提权逻辑 ──────────────────────────────────────────────────
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
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
            if ret > 32:
                # 提权并且拉起成功，退出当前非管理员进程
                sys.exit(0)
            else:
                from core.logger import logger
                logger.warning(f"Failed to elevate privileges. Return code: {ret}")
        except Exception as e:
            from core.logger import logger
            logger.error(f"Error during UAC elevation: {e}")
            # 如果取消了 UAC 或报错，目前选择继续以普通权限运行

    # ── 进程退出清理机制 ───────────────────────────────────────────────────
    import atexit
    def cleanup_on_exit():
        # 释放所有后台扫描子进程
        try:
            from multiprocessing import active_children
            for child in active_children():
                child.terminate()
        except:
            pass
    atexit.register(cleanup_on_exit)

    ft.app(target=main, assets_dir=_ASSETS_DIR)

