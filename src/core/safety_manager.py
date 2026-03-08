import ctypes
from ctypes import wintypes
import time
import threading
from core.logger import logger

# ── Windows API Constants ─────────────────────────────────────────────────────

# srclient.dll
# https://learn.microsoft.com/en-us/windows/win32/api/srrestoreptapi/nf-srrestoreptapi-srsetrestorepointw

# Restore point types
APPLICATION_INSTALL = 0
APPLICATION_UNINSTALL = 1
DESKTOP_SETTING = 2
ACCESSIBILITY_SETTING = 3
OE_SETTING = 4
APPLICATION_RUN = 5
RESTORE = 6
CHECKPOINT = 7
WINDOWS_SHUTDOWN = 8
WINDOWS_BOOT = 9
DEVICE_DRIVER_INSTALL = 10
FIRST_RUN = 11
MODIFY_SETTINGS = 12
CANCELLED_OPERATION = 13
BACKUP_RECOVERY = 14
BACKUP = 15
MANUAL_CHECKPOINT = 16
WINDOWS_UPDATE = 17
CRITICAL_UPDATE = 18

# Event types
BEGIN_SYSTEM_CHANGE = 100
END_SYSTEM_CHANGE = 101

# Status Flags
BEGIN_NESTED_SYSTEM_CHANGE = 102
END_NESTED_SYSTEM_CHANGE = 103

# MAX_DESC_W = 256
MAX_DESC_W = 256

# Return values
ERROR_SUCCESS = 0
ERROR_BAD_ENVIRONMENT = 10
ERROR_DISK_FULL = 112
ERROR_FILE_EXISTS = 80
ERROR_INVALID_DATA = 13
ERROR_SERVICE_DISABLED = 1058
ERROR_TIMEOUT = 1460


class STATEMGRSTATUS(ctypes.Structure):
    _fields_ = [
        ("nStatus", wintypes.DWORD),
        ("llSequenceNumber", ctypes.c_int64),
    ]

class RESTOREPOINTINFOW(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("dwEventType", wintypes.DWORD),
        ("dwRestorePtType", wintypes.DWORD),
        ("llSequenceNumber", ctypes.c_int64),
        ("szDescription", wintypes.WCHAR * MAX_DESC_W),
    ]

# ── 安全引擎实现 ─────────────────────────────────────────────────────────────

def create_system_restore_point(description: str = "ZenClean Deep Mining Checkpoint") -> bool:
    """
    在当前系统中创建一个还原点。如果服务未开启或由于其他原因导致失败，则安全放弃。
    注意：此过程可能会比较耗时，建议在线程中异步执行。
    
    Returns:
        bool: 是否成功创建还原点。
    """
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logger.warning("Create Restore Point requires Administrator privileges. Skipped.")
            return False
            
        srclient = ctypes.WinDLL("srclient.dll")
        SRSetRestorePointW = srclient.SRSetRestorePointW
        SRSetRestorePointW.argtypes = [ctypes.POINTER(RESTOREPOINTINFOW), ctypes.POINTER(STATEMGRSTATUS)]
        SRSetRestorePointW.restype = wintypes.BOOL

        restore_pt_info = RESTOREPOINTINFOW()
        restore_pt_info.dwEventType = BEGIN_SYSTEM_CHANGE
        restore_pt_info.dwRestorePtType = MODIFY_SETTINGS
        restore_pt_info.llSequenceNumber = 0
        restore_pt_info.szDescription = description

        status = STATEMGRSTATUS()

        logger.info(f"Attempting to create a System Restore Point: '{description}'...")
        
        # 阻塞调用系统 API
        result = SRSetRestorePointW(ctypes.byref(restore_pt_info), ctypes.byref(status))

        if result:
            logger.info(f"Restore Point created successfully. SeqNum: {status.llSequenceNumber}")
            
            # 为了严谨，需要立刻再发一个 END_SYSTEM_CHANGE 结束这个 Session，否则有些服务会锁死
            end_info = RESTOREPOINTINFOW()
            end_info.dwEventType = END_SYSTEM_CHANGE
            end_info.llSequenceNumber = status.llSequenceNumber
            SRSetRestorePointW(ctypes.byref(end_info), ctypes.byref(status))
            
            return True
        else:
            error_code = status.nStatus
            if error_code == ERROR_SERVICE_DISABLED:
                logger.warning("System Restore is disabled on this machine.")
            else:
                logger.error(f"Failed to create restore point. Error code: {error_code}")
            return False

    except Exception as e:
        logger.error(f"Exception while creating restore point: {e}")
        return False


def async_create_restore_point(description: str = "ZenClean Routine Checkpoint", timeout_sec: int = 15) -> bool:
    """
    异步带超时的创建还原点。防止因为 Windows API 假死而阻塞 ZenClean 的主要清理流程。
    """
    result = {"success": False}
    
    def _worker():
        result["success"] = create_system_restore_point(description)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    
    if t.is_alive():
        logger.error(f"Creating restore point timed out after {timeout_sec} seconds. Proceeding anyway.")
        # 我们不能真正强杀 Windows 系统线程，只能让 Python 放弃等待它
        return False
        
    return result["success"]

if __name__ == "__main__":
    # 局部测试用例
    print(f"Creating snapshot... Timeout: 15s")
    success = async_create_restore_point("ZenClean Test Snippet", timeout_sec=15)
    print(f"Snapshot Result: {success}")
