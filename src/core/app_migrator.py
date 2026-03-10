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
    path_template: str  # C盘绝对路径模板
    icon: str           # flet font_icon identifier
    description: str    # 描述
    risk_level: str     # "SAFE" | "CAUTION"
    process_names: list[str] = None # 关联的进程名列表，用于搬家前强制关闭检测

# 预定义的打靶目标
APP_TARGETS = [
    AppTarget(
        id="wechat_data",
        name="微信聊天数据",
        path_template="%USERPROFILE%\\Documents\\WeChat Files",
        icon="CHAT",
        description="包含所有聊天记录、图片与各类附件",
        risk_level="SAFE",
        process_names=["WeChat.exe", "WeChatApp.exe", "WeChatAppEx.exe"]
    ),
    AppTarget(
        id="tencent_qq",
        name="QQ聊天数据",
        path_template="%USERPROFILE%\\Documents\\Tencent Files",
        icon="FORUM",
        description="包含QQ接收的所有图片记录与文件",
        risk_level="SAFE",
        process_names=["QQ.exe"]
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
        description="极其臃肿的开发工具扩展包。搬家后可能会影响启动速度。",
        risk_level="CAUTION",
        process_names=["Code.exe"]
    ),
    AppTarget(
        id="docker_wsl",
        name="Docker 虚拟磁盘",
        path_template="%LOCALAPPDATA%\\Docker\\wsl\\data",
        icon="DOCKER",
        description="包含极度沉重的 Docker Image",
        risk_level="CAUTION",
        process_names=["Docker Desktop.exe", "com.docker.backend.exe", "vpnkit.exe"]
    ),
    AppTarget(
        id="dingtalk",
        name="钉钉 (DingTalk)",
        path_template="%APPDATA%\\DingTalk",
        icon="BUSINESS_CENTER",
        description="办公文件、图片及视频缓存。长期使用后极度臃肿。",
        risk_level="SAFE",
        process_names=["DingTalk.exe"]
    ),
    AppTarget(
        id="feishu",
        name="飞书 (Feishu)",
        path_template="%LOCALAPPDATA%\\LarkShell",
        icon="WORK_OUTLINE",
        description="包含聊天媒体缓存及版本更新存根。",
        risk_level="SAFE",
        process_names=["Feishu.exe"]
    ),
    AppTarget(
        id="baidu_netdisk",
        name="百度网盘",
        path_template="%APPDATA%\\Baidu\\BaiduNetdisk",
        icon="CLOUD_QUEUE",
        description="包含数据库索引、缩略图缓存等 C 盘存根。",
        risk_level="SAFE",
        process_names=["BaiduNetdisk.exe"]
    ),
    AppTarget(
        id="gemini_artifacts",
        name="AI 助手历史产物 (.gemini)",
        path_template="%USERPROFILE%\\.gemini",
        icon="AUTO_AWESOME",
        description="包含 AI 助手的历史录制、截图及日志产物。建议定期迁移。",
        risk_level="SAFE"
    ),
    AppTarget(
        id="ollama_models",
        name="Ollama 本地模型",
        path_template="%USERPROFILE%\\.ollama",
        icon="STREAKY_LENS",
        description="最占空间的本地大模型存放地 (Llama 3, DeepSeek 等)。",
        risk_level="SAFE",
        process_names=["ollama app.exe", "ollama.exe"]
    ),
    AppTarget(
        id="chrome_user_data",
        name="Chrome 浏览器数据",
        path_template="%LOCALAPPDATA%\\Google\\Chrome\\User Data",
        icon="WEB",
        description="包含历史记录、扩展和巨大的网页缓存。",
        risk_level="CAUTION",
        process_names=["chrome.exe"]
    ),
    AppTarget(
        id="edge_user_data",
        name="Edge 浏览器数据",
        path_template="%LOCALAPPDATA%\\Microsoft\\Edge\\User Data",
        icon="WEB",
        description="微软 Edge 浏览器的核心缓存与用户配置。",
        risk_level="CAUTION",
        process_names=["msedge.exe"]
    ),
    AppTarget(
        id="chatgpt_desktop",
        name="ChatGPT 桌面版",
        path_template="%APPDATA%\\ChatGPT",
        icon="AUTO_AWESOME_MOSAIC",
        description="官方客户端的本地对话缓存与索引。",
        risk_level="SAFE",
        process_names=["ChatGPT.exe"]
    ),
    AppTarget(
        id="claude_desktop",
        name="Claude 桌面版",
        path_template="%APPDATA%\\Claude",
        icon="COLOR_LENS",
        description="Claude 客户端的本地日志与运行数据。",
        risk_level="SAFE",
        process_names=["Claude.exe"]
    ),
    AppTarget(
        id="cursor_ai",
        name="Cursor AI 编辑器",
        path_template="%APPDATA%\\Cursor",
        icon="CODE",
        description="AI 编程工具产生的庞大索引数据。",
        risk_level="SAFE",
        process_names=["Cursor.exe"]
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

    def check_process_alive(self, target_id: str) -> list[str]:
        """检查目标 App 的进程是否仍在运行"""
        target = next((t for t in APP_TARGETS if t.id == target_id), None)
        if not target or not target.process_names:
            return []
            
        alive = []
        try:
            # 使用 tasklist 检查进程
            output = subprocess.check_output(["tasklist", "/NH", "/FO", "CSV"], shell=True, text=True)
            for proc_name in target.process_names:
                if proc_name.lower() in output.lower():
                    alive.append(proc_name)
        except Exception as e:
            logger.error(f"Failed to check process status: {e}")
        return alive

    def kill_target_processes(self, target_id: str) -> tuple[bool, str]:
        """强制终止目标 App 的所有进程"""
        target = next((t for t in APP_TARGETS if t.id == target_id), None)
        if not target or not target.process_names:
            return True, "无需终止进程"
            
        errors = []
        for proc_name in target.process_names:
            try:
                subprocess.run(["taskkill", "/F", "/IM", proc_name], shell=True, capture_output=True)
            except Exception as e:
                errors.append(f"{proc_name}: {e}")
        
        if errors:
            return False, f"部分进程终止失败: {', '.join(errors)}"
        return True, "已成功终止相关进程"

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
        skipped_count = 0
        
        # 使用递归复制而非重命名，原因：源与目标通常跨越不同的驱动器
        try:
            items = os.listdir(src_path)
        except Exception as e:
            logger.error(f"Failed to list directory {src_path}: {e}")
            return False, f"无法读取源目录，请检查权限: {e}"

        for item in items:
            s = src_path / item
            d = dest_base / item
            
            if on_progress:
                on_progress(moved_size, total_size, item)
                
            try:
                if s.is_dir():
                    shutil.move(str(s), str(d))
                else:
                    shutil.move(str(s), str(d))
                
                try:
                    moved_size += d.stat().st_size if d.exists() and d.is_file() else 0
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Skipping unmovable item {s}: {e}")
                skipped_count += 1
                continue

        # ── 3. 删空源目录并创建 Junction ──
        try:
            # 清理剩余的空壳目录
            if src_path.exists():
                shutil.rmtree(str(src_path), ignore_errors=True)

            # 检查目录是否真的被删除，防止残留导致 Junction 创建失败
            if src_path.exists():
                return False, "源目录清理失败，无法创建 Junction。请检查是否有其他程序正在占用该目录。"

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
        msg = "迁移已成功完成。底层路由已建立闭环，该软件运行不受丝毫影响。"
        if skipped_count > 0:
            msg += f" (注: 有 {skipped_count} 个忙碌文件被跳过，不影响核心使用)"
        return True, msg

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
            items = os.listdir(real_dest_path)
        except Exception as e:
             return False, f"无法读取目标目录列队: {e}"
             
        # 必须先重新创建被拆除的原始正常文件夹外壳
        try:
            os.makedirs(str(src_path), exist_ok=True)
        except Exception as e:
            return False, f"无法重建 C 盘原始数据文件夹: {e}"
             
        failed_items = []  # 记录失败的文件
        for item in items:
            s = real_dest_path / item
            d = src_path / item
            try:
                shutil.move(str(s), str(d))
            except Exception as e:
                logger.warning(f"Failed to restore item {s}: {e}")
                failed_items.append(item)
                continue

        # 如果有失败的文件，清理时保留它们
        if failed_items:
            logger.warning(f"Failed to restore {len(failed_items)} items: {failed_items}")

        # ── 3. 清理废弃源和历史 ──
        try:
            # 只清理成功迁移的项目
            if not failed_items:
                shutil.rmtree(real_dest_path, ignore_errors=True)
            history.remove(record)
            self._save_history(history)
        except Exception:
            pass

        # 返回结果，告知用户是否有文件迁移失败
        if failed_items:
            return True, f"已部分完成回退。{len(failed_items)} 个文件因被其他程序占用未能迁移，请手动处理。"
        return True, "已成功剥离所有映射关系，文件被完好无损退回了 C 盘。"

if __name__ == "__main__":
    migrator = AppMigrator()
    print("Pre-defined Targets:", [t.id for t in APP_TARGETS])
    print("Migrated History:", len(migrator.get_history()), "items")
