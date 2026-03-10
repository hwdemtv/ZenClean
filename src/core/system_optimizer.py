import subprocess
import os
from pathlib import Path
from core.logger import logger
from core.safety_manager import async_create_restore_point

def is_hibernation_enabled() -> bool:
    """
    检查系统休眠是否已开启。
    通过检查 C:\hiberfil.sys 是否存在来判断。
    (需要管理员权限才能准确判断，普通权限可能因访问限制返回错误)
    """
    hiberfil_path = Path("C:\\hiberfil.sys")
    try:
        # 使用 os.path.exists 对系统隐藏文件更可靠
        return os.path.exists(hiberfil_path)
    except Exception as e:
        logger.warning(f"Failed to check hibernation status: {e}")
        return False
        
def get_hiberfil_size_bytes() -> int:
    """获取休眠文件的大小，如果未开启则返回 0"""
    hiberfil_path = Path("C:\\hiberfil.sys")
    try:
        if os.path.exists(hiberfil_path):
            return os.path.getsize(hiberfil_path)
    except Exception:
        pass
    return 0

def disable_hibernation(auto_backup: bool = True) -> tuple[bool, str]:
    """
    关闭系统休眠 (powercfg -h off)，释放 C 盘空间。
    
    Args:
        auto_backup: 执行前是否自动创建系统还原点
        
    Returns:
        (success, message)
    """
    if not is_hibernation_enabled():
        return True, "休眠功能已经处于关闭状态，无需清理。"
        
    freed_size = get_hiberfil_size_bytes()
    freed_gb = freed_size / (1024**3)
    
    if auto_backup:
        async_create_restore_point("ZenClean: Disable Hibernation Backup")
        
    try:
        logger.info("Executing: powercfg -h off")
        # 必须 shell=True 或传入确切 executable 路径，因为 powercfg 是内置工具
        result = subprocess.run(
            ["powercfg", "-h", "off"], 
            capture_output=True, 
            text=True, 
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW # 隐藏丑陋的黑框
        )
        
        # 二次确认文件是否消失
        if not is_hibernation_enabled():
            msg = f"已成功关闭系统休眠，释放了 {freed_gb:.1f} GB 物理空间。"
            logger.info(msg)
            return True, msg
        else:
            msg = "命令已执行，但 hiberfil.sys 仍存在，可能由于文件被锁定或权限不足。"
            logger.error(f"{msg} STDOUT: {result.stdout}")
            return False, msg
            
    except subprocess.CalledProcessError as e:
        msg = f"关闭休眠失败，返回码: {e.returncode}。可能未以管理员身份运行。"
        logger.error(f"{msg} STDERR: {e.stderr}")
        return False, msg
    except Exception as e:
        msg = f"执行休眠管控指令时发生未知异常: {e}"
        logger.error(msg)
        return False, msg


def enable_hibernation() -> tuple[bool, str]:
    """
    如果用户后悔了，允许重新打开系统休眠 (powercfg -h on)。
    """
    if is_hibernation_enabled():
        return True, "休眠功能已经开启。"
        
    try:
        logger.info("Executing: powercfg -h on")
        result = subprocess.run(
            ["powercfg", "-h", "on"], 
            capture_output=True, 
            text=True, 
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if is_hibernation_enabled():
            return True, "已成功恢复系统休眠功能与快速启动。"
        else:
            return False, "命令已执行，休眠文件未能重新生成，请检查磁盘空间是否充足。"
    except subprocess.CalledProcessError as e:
        msg = f"恢复休眠失败，返回码: {e.returncode}。可能未以管理员身份运行。"
        logger.error(f"{msg} STDERR: {e.stderr}")
        return False, msg

def clean_windows_updates(on_progress=None) -> tuple[bool, str]:
    """
    调用系统级指令 DISM 彻底粉碎 WinSxS 旧更新备份 (无法撤回)。
    
    Args:
        on_progress: 进度回调函数 Callable[[float], None]，传入 0.0 - 1.0 之间的进度。
        
    Returns:
        (success, message)
    """
    import re
    # 匹配 DISM 输出中的进度: [======20.0%      ] 或者 [==========================100.0%==========================]
    progress_pattern = re.compile(r"\[.*?(\d+\.\d+)%.*?\]")
    
    try:
        logger.info("Executing: dism.exe /online /Cleanup-Image /StartComponentCleanup")
        
        # 启动子进程，开启管道读取 stdout
        process = subprocess.Popen(
            ["dism.exe", "/online", "/Cleanup-Image", "/StartComponentCleanup"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if process.stdout:
            # 逐字符/按行读取缓冲 (DISM 经常用 \r 回车不换行来更新进度)
            # 为了兼容 \r 我们需要按定长读取或在读取到 \r 时处理
            buffer = ""
            while True:
                char = process.stdout.read(1)
                if not char:
                    break
                buffer += char
                if char in ('\r', '\n'):
                    match = progress_pattern.search(buffer)
                    if match and on_progress:
                        try:
                            percent = float(match.group(1))
                            on_progress(percent / 100.0)
                        except ValueError:
                            pass
                    buffer = "" # 清空缓冲区
        
        process.wait()
        
        if process.returncode == 0:
            if on_progress: on_progress(1.0)
            msg = "系统级旧补丁组件已彻底粉碎，C 盘获得了新生。"
            logger.info(msg)
            return True, msg
        else:
            msg = f"DISM 清理异常结束，返回码: {process.returncode}。(若返回 740 请检查 UAC 权限)"
            logger.error(msg)
            return False, msg
            
    except Exception as e:
        msg = f"调用 DISM 接口时发生未知异常: {e}"
        logger.error(msg)
        return False, msg

if __name__ == "__main__":
    # 单独测试逻辑
    enabled = is_hibernation_enabled()
    size = get_hiberfil_size_bytes()
    print(f"Hibernation Enabled: {enabled}, Size: {size / (1024**3):.1f} GB")
