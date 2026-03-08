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
    # ── 关键 1: 必须放在所有逻辑的最前面 ────────────────────
    # 否则 PyInstaller 打包后的子进程也会疯狂弹出 UAC 提权
    import multiprocessing
    multiprocessing.freeze_support()

    import ctypes
    import sys

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

