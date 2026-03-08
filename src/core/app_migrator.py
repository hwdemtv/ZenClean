"""
应用级无损搬家引擎 (Application Level Migration)

不同于原先的 user shell migration (migration.py) 修改注册表，
此引擎使用 Windows NTFS 的 Junction Point 技术 (D 盘实体, C 盘透明映射)。
目标针对：微信、QQ、Docker、VSCode 插件库 等非系统级的特定软件缓存目录大户。

核心原理：
1. 目标文件夹（如 C:\\Users\\...\\WeChat Files）存在。
2. 验证目标盘（如 D 盘）剩余空间。
3. shutil.move 逐文件迁移至 D:\\ZenClean_Migration\\WeChat Files
4. C 盘原位置留空，建立 Junction 软链接指望 D 盘新位置（mklink /J）。
    -> 此时微信照常运行，但物理磁盘占用真正转移到 D 盘。
5. 记录元数据，支持逆向的一键无损还原。
"""

import os
import shutil
import subprocess
import threading
import json
from pathlib import Path
from dataclasses import dataclass
from core.logger import logger
from config.settings import APP_DATA_DIR

MIGRATION_HISTORY_FILE = os.path.join(APP_DATA_DIR, "migrations.json")

@dataclass
class AppTarget:
    """定义一个可被 Junction 搬家的软件大户源"""
    id: str             # "wechat_data"
    name: str           # "微信全局数据"
    path_template: str  # C盘绝对路径模板（支持 %USERPROFILE%, %LOCALAPPDATA% 等变量）
    icon: str           # flet font_icon identifier
    description: str    # "包含所有聊天缓存，体积通常在 10G-100G 之间"
    risk_level: str     # "SAFE" | "CAUTION" (影响 UI 的颜色警告)

# 预定义的打靶目标
APP_TARGETS = [
    AppTarget(
        id="wechat_data",
        name="微信聊天数据",
        path_template="%USERPROFILE%\\Documents\\WeChat Files",
        icon="CHAT",
        description="包含所有聊天记录、图片与各类附件",
        risk_level="SAFE"
    ),
    AppTarget(
        id="tencent_qq",
        name="QQ聊天数据",
        path_template="%USERPROFILE%\\Documents\\Tencent Files",
        icon="FORUM",
        description="包含QQ接收的所有图片记录与文件",
        risk_level="SAFE"
    ),
    AppTarget(
        id="npm_cache",
        name="NPM 全局缓存",
        path_template="%APPDATA%\\npm-cache",
        icon="JAVASCRIPT",
        description="Node.js 历史下载过的前端依赖总仓库",
        risk_level="SAFE"
    ),
    AppTarget(
        id="pip_cache",
        name="PIP 全局缓存",
        path_template="%LOCALAPPDATA%\\pip\\cache",
        icon="CODE",
        description="Python 历史下载过的安装包缓存库",
        risk_level="SAFE"
    ),
    AppTarget(
        id="vscode_ext",
        name="Visual Studio Code 扩展包",
        path_template="%USERPROFILE%\\.vscode\\extensions",
        icon="TERMINAL",
        description="极其臃肿的开发工具扩展包。搬家后可能会因跨盘访问速度轻微影响启动速度，机械硬盘用户慎选。",
        risk_level="CAUTION"
    ),
    AppTarget(
        id="docker_wsl",
        name="Docker 虚拟磁盘",
        path_template="%LOCALAPPDATA%\\Docker\\wsl\\data",
        icon="DOCKER",
        description="包含极度沉重的 Docker Image",
        risk_level="CAUTION"
    )
]


class AppMigrator:
    def __init__(self):
        self.history_file = Path(MIGRATION_HISTORY_FILE)
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
            logger.error(f"Failed to read migration history: {e}")
            return []

    def _save_history(self, history: list[dict]):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def is_already_migrated(self, path: Path) -> bool:
        """检查一个路径是否已经被转化为 Junction Point (通常代表已经搬过家了)"""
        if not path.exists():
            return False
            
        try:
            # 检查系统文件属性 FILE_ATTRIBUTE_REPARSE_POINT (0x400)
            attrs = os.stat(str(path), follow_symlinks=False).st_file_attributes
            return bool(attrs & 0x400)
        except (OSError, AttributeError):
            return False

    def execute_migration(self, target_id: str, dest_drive: str, on_progress=None) -> tuple[bool, str]:
        """
        开始给特定的第三方 App 数据搬家
        Args:
           target_id:  来自 APP_TARGETS 的 id
           dest_drive: 形如 "D:"
        """
        target = next((t for t in APP_TARGETS if t.id == target_id), None)
        if not target:
            return False, f"未识别的目标 App ID: {target_id}"
            
        src_path_str = os.path.expandvars(target.path_template)
        src_path = Path(src_path_str)
        
        if not src_path.exists():
            return False, f"[{target.name}] 数据目录不存在: {src_path.name}，可能该设备尚未安装或运行过该软件。"
            
        if self.is_already_migrated(src_path):
            return False, f"[{target.name}] 已经是一个连接点 (Junction)，疑似已经被搬家过了。"
            
        if src_path.drive.upper() == dest_drive.upper():
            return False, "源路径已经在目标盘符下，无法执行同盘映射。"

        dest_base = Path(dest_drive) / "ZenClean_AppSpace" / target.name
        
        # ── 1. 容量预检 ──
        total_size = 0
        try:
            for root, dirs, files in os.walk(src_path):
                for f in files:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception as e:
            logger.error(f"Failed to calculate dir size for migration preflight: {e}")
            return False, "未能成功取得文件夹总容量（权限受限或有文件被高度占用）。建议关闭对应软件后再试。"

        try:
            free = shutil.disk_usage(dest_drive + "\\").free
            if free < (total_size * 1.1):  # 留出 10% 余量
                return False, f"目标盘 '{dest_drive}' 空间不足 (需要 {total_size / 1024**3:.2f}GB)。"
        except Exception as e:
            return False, f"无法读取目标盘空间状态: {e}"

        # ── 2. 开始逐一迁移文件 ──
        try:
            os.makedirs(dest_base, exist_ok=True)
        except Exception as e:
            return False, f"目标盘创建基准文件夹失败: {e}"

        moved_size = 0
        
        # 使用递归复制而非重命名，原因：源与目标通常跨越不同的驱动器
        # shutil.move 本身在跨盘时会 fallback 成 copy2 + rmtree
        try:
            # TODO: 加入 Cancellation_token 的支持
            for item in os.listdir(src_path):
                s = src_path / item
                d = dest_base / item
                
                # 通知 UI 当前进展
                if on_progress:
                    on_progress(moved_size, total_size, item)
                    
                if s.is_dir():
                    shutil.move(str(s), str(d))
                else:
                    shutil.move(str(s), str(d))
                    
                # 简单累加估算，提高性能不深算
                moved_size += s.stat().st_size if s.exists() and s.is_file() else 0
                
        except Exception as e:
            logger.error(f"Migration file movement failed: {e}")
            # [致命断崖点预防]: 如果发生崩溃，不要立即摧毁源目录，原位留存剩余，目标目录残留拷贝件
            return False, f"文件搬迁非预期中止，可能软件尚未完全退出占用: {e}"

        # ── 3. 删空源目录并创建 Junction ──
        try:
            # 清理剩余的空壳目录
            if src_path.exists():
                shutil.rmtree(str(src_path), ignore_errors=True)
                
            subprocess.run(
                ["mklink", "/J", str(src_path), str(dest_base)],
                shell=True,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Junction Link Creation Failed! STDERR: {e.stderr}")
            return False, "底层跨盘隐式映射(Junction)构建失败，请确保您以管理员权限启动。"

        # ── 4. 收尾日志写入 ──
        history = self.get_history()
        history.append({
            "target_id": target.id,
            "target_name": target.name,
            "migrated_at": str(os.path.getmtime(self.history_file)) if self.history_file.exists() else "unknown",
            "original_path": str(src_path),
            "dest_path": str(dest_base),
            "size_bytes": total_size
        })
        self._save_history(history)
        
        logger.info(f"App Migration SUCCESS: {target.name} mapped to {dest_base}")
        return True, "迁移已成功完成。底层路由已建立闭环，该软件运行不受丝毫影响。"

    def restore_migration(self, target_id: str, on_progress=None) -> tuple[bool, str]:
        """
        撤销 Junction 软连接，并将真实的物理文件从异源盘移回 C 盘
        """
        history = self.get_history()
        record = next((r for r in history if r["target_id"] == target_id), None)
        
        if not record:
            return False, "未能找到该软件的搬家历史纪录。"
            
        src_path = Path(record["original_path"]) # 原来的软连接位置，现在应该是个软连
        real_dest_path = Path(record["dest_path"]) # 在其他盘里真实存在的数据
        
        if not real_dest_path.exists():
            return False, "映射在 D 盘的真实数据文件已被意外删除或改变位置！"

        if not self.is_already_migrated(src_path):
             return False, "源路径目前并非一个软链接，可能已经被用户手动修改过结构！强行还原存在覆写风险。"

        # ── 1. 拆除软链接壳 ──
        try:
            os.rmdir(str(src_path))
        except Exception as e:
             return False, f"移除 C 盘现有软链接外壳失败：{e}"
             
        # ── 2. 回迁真实文件 ──
        try:
            for item in os.listdir(real_dest_path):
                s = real_dest_path / item
                d = src_path / item
                shutil.move(str(s), str(d))
        except Exception as e:
            return False, f"数据回迁 C 盘时遇到故障: {e}"
            
        # ── 3. 清理废弃源和历史 ──
        try:
            shutil.rmtree(real_dest_path, ignore_errors=True)
            history.remove(record)
            self._save_history(history)
        except Exception:
            pass
            
        return True, "已成功剥离所有映射关系，文件被完好无损退回了 C 盘。"

if __name__ == "__main__":
    migrator = AppMigrator()
    print("Pre-defined Targets:", [t.id for t in APP_TARGETS])
    print("Migrated History:", len(migrator.get_history()), "items")
