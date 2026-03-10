import os
import sys
import winreg
from core.logger import logger

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "ZenClean"

def _get_executable_path() -> str:
    """获取程序真正的入口可执行路径"""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        # 开发模式下，拉起 Python 和入口脚本
        script_path = os.path.abspath(sys.argv[0])
        return f'"{sys.executable}" "{script_path}"'

def is_registered() -> bool:
    """检查是否已经注册了开机自启动"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return value == _get_executable_path()
    except OSError:
        return False

def register() -> tuple[bool, str]:
    """注册开机自启动"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _get_executable_path())
        winreg.CloseKey(key)
        logger.info("[Autorun] Successfully registered startup item.")
        return True, "已成功开启开机自动驻留守护"
    except Exception as e:
        logger.error(f"[Autorun] Failed to register: {e}")
        return False, f"开启开机自启失败: {e}"

def unregister() -> tuple[bool, str]:
    """取消开机自启动"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
        logger.info("[Autorun] Successfully unregistered startup item.")
        return True, "已关闭开机自动驻留守护"
    except FileNotFoundError:
        return True, "已关闭开机自动驻留守护"  # 本来就不存在，也算成功
    except Exception as e:
        logger.error(f"[Autorun] Failed to unregister: {e}")
        return False, f"关闭开机自启失败: {e}"
