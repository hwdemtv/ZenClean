"""
PyInstaller runtime hook for multiprocessing
解决 --onedir 模式下的 multiprocessing 死循环分叉炸弹问题
"""
import sys
import os

if hasattr(sys, 'frozen'):
    # Windows 平台环境提取
    if sys.platform == 'win32':
        # 在 --onedir 模式下，获取当前 exe 所在目录
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
        sys.path.insert(0, bundle_dir)
    
    # 手动触发多进程冷冻支持
    from multiprocessing import freeze_support
    freeze_support()
