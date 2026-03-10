"""
ZenClean 隔离沙箱引擎 (Quarantine Sandbox)

负责拦截原有的物理删除操作，将高危或 AI 建议清理的文件移入隔离区，
提供 72 小时的反悔期。防范彻底误删导致的客诉。
"""
import os
import sys
import uuid
import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import APP_DATA_DIR
from core.logger import logger

# 隔离沙箱元数据注册表
QUARANTINE_REGISTRY_PATH = APP_DATA_DIR / "quarantine_registry.json"
# 默认隔离阈值（天）
DEFAULT_RETENTION_DAYS = 3


def _get_best_sandbox_dir() -> Path:
    """自动寻找最合适的隔离沙箱存放磁盘（通常是非系统盘，且空间最大）"""
    import psutil
    best_drive = "C:\\"
    max_free = 0
    
    try:
        # 尝试寻找非 C 盘且空间极大的分区作为沙箱
        for part in psutil.disk_partitions(all=False):
            # 过滤不可达或系统保留分区
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                # 优先选非系统盘
                if "C:" not in part.mountpoint and usage.free > max_free:
                    max_free = usage.free
                    best_drive = part.mountpoint
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Failed to find best sandbox drive: {e}")
        
    sandbox_path = Path(best_drive) / ".ZenClean_Sandbox"
    return sandbox_path


def _load_registry() -> dict:
    if QUARANTINE_REGISTRY_PATH.exists():
        try:
            with open(QUARANTINE_REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load quarantine registry: {e}")
    return {}


def _save_registry(registry: dict) -> None:
    try:
        QUARANTINE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QUARANTINE_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save quarantine registry: {e}")


def quarantine(source_path: str, size_bytes: int = 0) -> bool:
    """
    将目标文件/文件夹隔离到沙箱中
    返回是否隔离成功
    """
    src = Path(source_path)
    if not src.exists():
        return False
        
    sandbox_dir = _get_best_sandbox_dir()
    try:
        sandbox_dir.mkdir(parents=True, exist_ok=False) # 隐藏属性通常需要调用 win32api 设置，这里简化
        if os.name == 'nt':
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(sandbox_dir), FILE_ATTRIBUTE_HIDDEN)
    except FileExistsError:
        pass
    except Exception as e:
        logger.warning(f"Failed to create or hide sandbox dir: {e}")
        
    registry = _load_registry()
    
    # 生成唯一标识，防止同名文件冲突
    q_id = str(uuid.uuid4())
    dest_path = sandbox_dir / f"{src.name}_{q_id}"
    
    try:
        # 移动文件/文件夹
        shutil.move(str(src), str(dest_path))
        
        # 登记造册
        registry[q_id] = {
            "original_path": str(src),
            "sandbox_path": str(dest_path),
            "size_bytes": size_bytes,
            "quarantined_at": datetime.now().isoformat(),
            "name": src.name,
            "is_dir": dest_path.is_dir()
        }
        _save_registry(registry)
        logger.info(f"Quarantined: {src} -> {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to quarantine {src}: {e}")
        return False


def restore(q_id: str) -> bool:
    """
    将沙箱中的文件原路恢复
    """
    registry = _load_registry()
    if q_id not in registry:
        logger.warning(f"Restore failed: ID {q_id} not found in registry.")
        return False
        
    item = registry[q_id]
    src = Path(item["sandbox_path"])
    dest = Path(item["original_path"])
    
    if not src.exists():
        logger.warning(f"Restore failed: Sandbox file missing for ID {q_id}.")
        # 元数据虽在但实体已死，清理僵尸记录
        del registry[q_id]
        _save_registry(registry)
        return False
        
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            # 目的地已有同名文件，无法恢复
            logger.error(f"Restore collision: {dest} already exists.")
            return False
            
        shutil.move(str(src), str(dest))
        
        # 恢复成功，移除记录
        del registry[q_id]
        _save_registry(registry)
        logger.info(f"Restored file from sandbox: {dest}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore {q_id}: {e}")
        return False


def list_quarantined() -> list[dict]:
    """返回当前处于隔离状态的所有项目列表，按时间倒序"""
    registry = _load_registry()
    items = []
    for q_id, data in registry.items():
        data["id"] = q_id
        items.append(data)
    items.sort(key=lambda x: x["quarantined_at"], reverse=True)
    return items


def auto_clean_expired(days: int = DEFAULT_RETENTION_DAYS) -> int:
    """
    静默销毁过期沙箱文件，返回释放的字节数
    """
    registry = _load_registry()
    expired_ids = []
    freed = 0
    now = datetime.now()
    
    for q_id, item in registry.items():
        try:
            q_time = datetime.fromisoformat(item["quarantined_at"])
            if now - q_time > timedelta(days=days):
                expired_ids.append((q_id, item))
        except Exception:
            # 解析时间失败的直接判定为过期
            expired_ids.append((q_id, item))
            
    for q_id, item in expired_ids:
        src = Path(item["sandbox_path"])
        size = item.get("size_bytes", 0)
        try:
            if src.exists():
                if src.is_dir():
                    shutil.rmtree(str(src), ignore_errors=True)
                else:
                    src.unlink(missing_ok=True)
            freed += size
            del registry[q_id]
            logger.info(f"Auto-cleaned expired sandbox item: {q_id}")
        except Exception as e:
            logger.error(f"Failed to auto-clean sandbox item {q_id}: {e}")
            
    if expired_ids:
        _save_registry(registry)
        
    return freed

def delete_item(q_id: str) -> bool:
    """手动彻底删除沙箱内的某个项目"""
    registry = _load_registry()
    if q_id not in registry:
        return False
    item = registry[q_id]
    src = Path(item["sandbox_path"])
    try:
        if src.exists():
            if src.is_dir():
                shutil.rmtree(str(src), ignore_errors=True)
            else:
                src.unlink(missing_ok=True)
        del registry[q_id]
        _save_registry(registry)
        logger.info(f"Permanently deleted sandbox item: {q_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete {q_id} permanently: {e}")
        return False

def clear_all() -> int:
    """清空所有隔离沙箱内的项目，返回释放的字节数"""
    registry = _load_registry()
    freed = 0
    for q_id, item in list(registry.items()):
        src = Path(item["sandbox_path"])
        size = item.get("size_bytes", 0)
        try:
            if src.exists():
                if src.is_dir():
                    shutil.rmtree(str(src), ignore_errors=True)
                else:
                    src.unlink(missing_ok=True)
            freed += size
            del registry[q_id]
        except Exception as e:
            logger.error(f"Failed to clear sandbox item {q_id}: {e}")
            
    _save_registry(registry)
    return freed

def restore_all() -> tuple[int, int]:
    """批量原路恢复隔离沙箱内的所有项目，返回(成功恢复数量, 失败数量)"""
    registry = _load_registry()
    success_count = 0
    fail_count = 0
    
    # 转换为列表避免在迭代时修改字典报错
    q_ids = list(registry.keys())
    
    for q_id in q_ids:
        item = registry[q_id]
        src = Path(item["sandbox_path"])
        dest = Path(item["original_path"])
        
        if not src.exists():
            logger.warning(f"Batch restore skipping: Sandbox file missing for ID {q_id}.")
            del registry[q_id]
            fail_count += 1
            continue
            
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                logger.error(f"Batch restore collision: {dest} already exists.")
                fail_count += 1
                continue
                
            shutil.move(str(src), str(dest))
            del registry[q_id]
            logger.info(f"Batch restored file from sandbox: {dest}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to batch restore {q_id}: {e}")
            fail_count += 1
            
    # 全量处理完后统一保存一次，避免重复写盘引发 IO 瓶颈和竞态
    if success_count > 0 or fail_count > 0:
        _save_registry(registry)
        
    return success_count, fail_count

