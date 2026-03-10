"""
Windows 右键菜单集成模块

通过写入 HKEY_CURRENT_USER 注册表实现资源管理器右键菜单扩展。
仅影响当前用户，不需要管理员权限，不触发 UAC。

注册后效果：
    右键任意文件夹 → 出现 "使用 ZenClean 分析" 菜单项
    点击后以该文件夹路径为参数启动 ZenClean
"""

import sys
import os
import winreg
from core.logger import logger

# 注册表路径（当前用户级别，无需提权）
_REG_DIR_SHELL = r"Software\Classes\Directory\shell\ZenClean"
_REG_DIR_CMD   = r"Software\Classes\Directory\shell\ZenClean\command"
# 同时支持文件夹背景空白处右键
_REG_BG_SHELL  = r"Software\Classes\Directory\Background\shell\ZenClean"
_REG_BG_CMD    = r"Software\Classes\Directory\Background\shell\ZenClean\command"


def _get_exe_path() -> str:
    """获取当前可执行文件路径（兼容 PyInstaller 打包与源码运行）"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后
        return sys.executable
    else:
        # 源码运行：用 python.exe + main.py
        main_py = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
        return f'"{sys.executable}" "{main_py}"'


def register() -> tuple[bool, str]:
    """
    注册右键菜单。
    
    Returns:
        (success, message)
    """
    try:
        exe_path = _get_exe_path()
        # 带参数的命令行：%V 是 Windows Shell 传入的目录路径
        if getattr(sys, "frozen", False):
            command = f'"{exe_path}" --analyze "%V"'
        else:
            command = f'{exe_path} --analyze "%V"'

        # ── 文件夹右键菜单 ──
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_DIR_SHELL, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "使用 ZenClean 分析")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path.strip('"'))
        winreg.CloseKey(key)

        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_DIR_CMD, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        # ── 文件夹空白处右键菜单 ──
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_BG_SHELL, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "使用 ZenClean 分析")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path.strip('"'))
        winreg.CloseKey(key)

        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_BG_CMD, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        logger.info("右键菜单注册成功")
        return True, "右键菜单已成功注册"
    except Exception as e:
        logger.error(f"右键菜单注册失败: {type(e).__name__}")
        return False, f"注册失败: {e}"


def unregister() -> tuple[bool, str]:
    """
    注销右键菜单。
    
    Returns:
        (success, message)
    """
    try:
        for reg_path in [_REG_DIR_CMD, _REG_DIR_SHELL, _REG_BG_CMD, _REG_BG_SHELL]:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
            except FileNotFoundError:
                pass  # 键不存在，跳过
        logger.info("右键菜单已注销")
        return True, "右键菜单已注销"
    except Exception as e:
        logger.error(f"右键菜单注销失败: {type(e).__name__}")
        return False, f"注销失败: {e}"


def is_registered() -> bool:
    """检测右键菜单是否已注册"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_DIR_SHELL, 0, winreg.KEY_READ)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
