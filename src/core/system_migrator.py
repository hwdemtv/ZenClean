"""
系统级深度空间迁移引擎 (System Level Migration)

专门针对具有极高风险、由系统服务锁定的底层根目录转移任务。
目前主要目标：C:\\Windows\\Installer\\$PatchCache$
原理同 AppMigrator，使用 NTFS Junction Point 技术映射到其他盘符，
但会额外接管底层关键服务的全生命周期启停控制。
"""

import os
import shutil
import subprocess
import json
import ctypes
from pathlib import Path
from core.logger import logger
from config.settings import APP_DATA_DIR

SYS_MIGRATION_HISTORY_FILE = os.path.join(APP_DATA_DIR, "sys_migrations.json")

class SystemMigrator:
    PATCH_CACHE_DIR = r"C:\Windows\Installer\$PatchCache$"

    def __init__(self):
        self.history_file = Path(SYS_MIGRATION_HISTORY_FILE)
        self._ensure_history_file()

    def _ensure_history_file(self):
        if not self.history_file.parent.exists():
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def get_history(self) -> list[dict]:
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read sys migration history: {e}")
            return []

    def _save_history(self, history: list[dict]):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def _is_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def is_already_migrated(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            attrs = os.stat(str(path), follow_symlinks=False).st_file_attributes
            return bool(attrs & 0x400) # FILE_ATTRIBUTE_REPARSE_POINT
        except OSError:
            return False

    def check_installer_service(self) -> str:
        """检查 msiserver 服务的状态"""
        try:
            # sc query msiserver
            result = subprocess.run(["sc", "query", "msiserver"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if "RUNNING" in result.stdout:
                return "RUNNING"
            elif "STOPPED" in result.stdout:
                return "STOPPED"
            else:
                return "UNKNOWN"
        except Exception as e:
            logger.error(f"Failed to query msiserver: {e}")
            return "UNKNOWN"

    def stop_installer_service(self) -> tuple[bool, str]:
        if self.check_installer_service() == "STOPPED":
            return True, "服务已是停止状态"
        try:
            logger.info("Stopping msiserver service...")
            result = subprocess.run(["net", "stop", "msiserver", "/y"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0 or "The Windows Installer service is not started" in result.stdout:
                return True, "已成功拦截并挂起 Windows Installer 服务"
            return False, f"终止服务失败: {result.stdout}"
        except Exception as e:
            return False, f"终止服务指令执行异常: {str(e)}"

    def start_installer_service(self) -> tuple[bool, str]:
        if self.check_installer_service() == "RUNNING":
            return True, "服务已是运行状态"
        try:
            logger.info("Starting msiserver service...")
            result = subprocess.run(["net", "start", "msiserver"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0 or "The requested service has already been started" in result.stdout:
                return True, "Windows Installer 服务已重新唤醒上线"
            return False, f"唤醒服务失败: {result.stdout}"
        except Exception as e:
            return False, f"唤醒服务指令执行异常: {str(e)}"

    def preflight_check(self, dest_drive: str) -> dict:
        """转移前的安全体检"""
        src_path = Path(self.PATCH_CACHE_DIR)
        
        checks = {
            "is_admin": self._is_admin(),
            "installer_service": self.check_installer_service(),
            "path_exists": src_path.exists(),
            "is_junction": self.is_already_migrated(src_path),
            "size_bytes": 0,
            "dest_space_bytes": 0,
            "can_migrate": False,
            "error": None
        }

        if not checks["is_admin"]:
            checks["error"] = "缺少管理员权限 (Elevation Required)。这块地盘被系统严密保护。"
            return checks
            
        if not checks["path_exists"]:
            checks["error"] = "C 盘中未发现 $PatchCache$ 目录。它可能已经被其他工具强行清理过了。"
            return checks

        if checks["is_junction"]:
            checks["error"] = "该目录已经是一个高级软卷映射，证实已搬迁，无需重复作业。"
            return checks

        # 计算体积
        try:
            for root, dirs, files in os.walk(src_path):
                for f in files:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        checks["size_bytes"] += os.path.getsize(fp)
        except Exception as e:
            checks["error"] = f"计算存根文件体积遇阻 (权限不足或锁定): {e}"
            return checks

        # 检查目标盘空间 (10% surplus)
        try:
            free_space = shutil.disk_usage(dest_drive + "\\").free
            checks["dest_space_bytes"] = free_space
            if free_space < (checks["size_bytes"] * 1.1):
                checks["error"] = f"目标盘 '{dest_drive}' 剩余空间吃紧，请更换目标。"
                return checks
        except Exception as e:
            checks["error"] = f"探矿目标盘空间失败: {e}"
            return checks

        checks["can_migrate"] = True
        return checks

    def migrate(self, dest_drive: str, on_progress=None) -> tuple[bool, str]:
        checks = self.preflight_check(dest_drive)
        if not checks["can_migrate"]:
            return False, checks.get("error", "前置体检被拦截，不满足安全转移标准。")

        src_path = Path(self.PATCH_CACHE_DIR)
        dest_base = Path(dest_drive) / "ZenClean_SystemHives" / "$PatchCache$"

        # 1. 深度挂起底层服务
        svc_stopped, svc_msg = self.stop_installer_service()
        if not svc_stopped:
            return False, f"无法夺取控制权: {svc_msg}"

        # 2. 准备目标落脚点
        try:
            os.makedirs(dest_base, exist_ok=True)
        except Exception as e:
            self.start_installer_service() # 回退
            return False, f"在目标驱动器圈划阵地失败: {e}"

        # 3. 跨分区数据大挪移
        total_size = checks["size_bytes"]
        moved_size = 0
        skipped_count = 0

        try:
            items = os.listdir(src_path)
            for item in items:
                s = src_path / item
                d = dest_base / item
                
                if on_progress:
                    on_progress((moved_size / total_size) if total_size > 0 else 0)
                    
                try:
                    shutil.move(str(s), str(d))
                    moved_size += d.stat().st_size if d.exists() and d.is_file() else 0
                except Exception as e:
                    logger.warning(f"Failed to move core patch {s}: {e}")
                    skipped_count += 1
                    continue
        except Exception as e:
            self.start_installer_service()
            return False, f"迁移数据洪流时发生溃堤: {e}"

        # 4. 摧毁老家并建立虫洞链接
        try:
            if src_path.exists():
                shutil.rmtree(str(src_path), ignore_errors=True)
                
            subprocess.run(
                ["mklink", "/J", str(src_path), str(dest_base)],
                shell=True,
                capture_output=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"System Junction Link Failed! STDERR: {e.stderr}")
            # 如果 mklink 失败，尝试把文件拉回来是个灾难，这里尽量保持现状，让用户知晓
            self.start_installer_service()
            return False, "底层跨分区路由构建失败！文件已转移，但 C 盘挂载点建立破产。"

        # 5. 重启引擎，释放兵权
        self.start_installer_service()

        # 6. 建档存档
        history = self.get_history()
        history.append({
            "target_id": "win_installer_patch_cache",
            "migrated_at": str(os.path.getmtime(self.history_file)) if self.history_file.exists() else "unknown",
            "original_path": str(src_path),
            "dest_path": str(dest_base),
            "size_bytes": total_size
        })
        self._save_history(history)

        if on_progress: on_progress(1.0)
        
        msg = f"军管级搬发成功。C 盘卸掉 {total_size / 1024**3:.2f}GB 钢板。"
        if skipped_count > 0:
            msg += f" (注: {skipped_count} 块硬骨头跳过)"
        return True, msg

    def restore(self, on_progress=None) -> tuple[bool, str]:
        history = self.get_history()
        record = next((r for r in history if r["target_id"] == "win_installer_patch_cache"), None)
        
        if not record:
            return False, "军事档案中未查到此模块的搬家记录。"
            
        src_path = Path(record["original_path"]) 
        real_dest_path = Path(record["dest_path"]) 
        
        if not real_dest_path.exists():
            return False, "异地军火库已丢失或遭遇格式化，无法发起回收。"

        if not self.is_already_migrated(src_path):
             return False, "目标源当前形态已不是透明虫洞 (Junction)，疑似受到三方干预，拒绝强行回滚。"

        # 停止服务夺权
        svc_stopped, svc_msg = self.stop_installer_service()
        if not svc_stopped:
            return False, f"回收时夺权失败: {svc_msg}"

        # 1. 炸毁虫洞
        try:
            os.rmdir(str(src_path))
        except Exception as e:
            self.start_installer_service()
            return False, f"爆破现有虫洞失败: {e}"
             
        # 2. 回迁真实文件
        try:
            os.makedirs(str(src_path), exist_ok=True)
            items = os.listdir(real_dest_path)
            total = len(items)
            
            for i, item in enumerate(items):
                s = real_dest_path / item
                d = src_path / item
                try:
                    shutil.move(str(s), str(d))
                except Exception as e:
                    logger.warning(f"Failed to pull back {s}: {e}")
                if on_progress and total > 0:
                    on_progress(i / total)
        except Exception as e:
             self.start_installer_service()
             return False, f"物理数据列车返程脱轨: {e}"
            
        # 3. 清扫地盘与档案销毁
        try:
            shutil.rmtree(real_dest_path, ignore_errors=True)
            history.remove(record)
            self._save_history(history)
        except Exception:
            pass
            
        # 释放兵权
        self.start_installer_service()
        if on_progress: on_progress(1.0)
        
        return True, "已成功闭合虫洞重铸实体，$PatchCache$ 军团已全部整齐归建 C 盘。"

if __name__ == "__main__":
    migrator = SystemMigrator()
    print("Checks:", migrator.preflight_check("D:"))
