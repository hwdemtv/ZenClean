import re
import os

migrator_path = r"D:\软件开发\ZenClean\src\core\app_migrator.py"
with open(migrator_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update AppTarget dataclass definition
old_dataclass = """@dataclass
class AppTarget:
    \"\"\"定义一个可被 Junction 搬家的软件大户源\"\"\"
    id: str             # "wechat_data"
    name: str           # "微信聊天数据"
    path_template: str  # C盘绝对路径模板
    icon: str           # flet font_icon identifier
    description: str    # 描述
    risk_level: str     # "SAFE" | "CAUTION"
    process_names: list[str] = None # 关联的进程名列表，用于搬家前强制关闭检测
    category: str = "general"  # 分类: general, browser_cache, dev_tools, chat_apps
    parent_id: str = None  # 如果是子目标，指向父目标 ID (用于浏览器 Cache 拆分)"""

new_dataclass = """@dataclass
class AppTarget:
    \"\"\"定义一个可被 Junction 搬家的软件大户源\"\"\"
    id: str             # "wechat_data"
    name: str           # "微信聊天数据"
    path_templates: list[str] = field(default_factory=list) # C盘候选绝对路径模板列表
    icon: str = "APPS"           # flet font_icon identifier
    description: str = ""    # 描述
    risk_level: str = "SAFE"     # "SAFE" | "CAUTION"
    registry_key: str = None  # 注册表查找路径，例如 "Software\\\\Tencent\\\\WeChat|FileSavePath"
    process_names: list[str] = field(default_factory=list) # 关联的进程名列表，用于搬家前强制关闭检测
    category: str = "general"  # 分类: general, browser_cache, dev_tools, chat_apps
    parent_id: str = None  # 如果是子目标，指向父目标 ID (用于浏览器 Cache 拆分)
    path_template: str = None # 保留向下兼容

def resolve_path_from_registry(registry_key: str) -> str | None:
    try:
        import winreg
        if "|" in registry_key:
            key_path, val_name = registry_key.split("|", 1)
        else:
            key_path, val_name = registry_key, ""
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
        value, _ = winreg.QueryValueEx(key, val_name)
        winreg.CloseKey(key)
        if value and os.path.exists(value):
            return value
    except Exception:
        pass
    return None

def resolve_target_path(target: AppTarget) -> str | None:
    if target.registry_key:
        reg_path = resolve_path_from_registry(target.registry_key)
        if reg_path:
            return reg_path
    if target.path_templates:
        for tpl in target.path_templates:
            p = os.path.expandvars(tpl)
            if os.path.exists(p):
                return p
    if target.path_template:
        p = os.path.expandvars(target.path_template)
        if os.path.exists(p):
            return p
    return None
"""

content = content.replace(old_dataclass, new_dataclass)

# 2. Add registry_key to WeChat
content = content.replace(
    'path_template="%USERPROFILE%\\\\Documents\\\\WeChat Files",',
    'path_templates=["%USERPROFILE%\\\\Documents\\\\WeChat Files", "%USERPROFILE%\\\\Documents\\\\微信文件"],\n        registry_key="Software\\\\Tencent\\\\WeChat|FileSavePath",'
)

# 3. Replace all remaining path_template=... with path_templates=[...]
content = re.sub(r'path_template="(.*?)",', r'path_templates=["\1"],', content)

# 4. In `execute_migration`, change `src_path_str = os.path.expandvars(target.path_template)` to `resolve_target_path`
content = content.replace(
    'src_path_str = os.path.expandvars(target.path_template)',
    'src_path_str = resolve_target_path(target)'
)
content = content.replace(
    'src_path = Path(src_path_str)',
    'if not src_path_str:\n            return False, f"[{target.name}] 数据目录不存在，可能该设备尚未安装或运行过该软件。"\n        src_path = Path(src_path_str)'
)
# We already handle not src_path.exists() inside execute_migration.

with open(migrator_path, "w", encoding="utf-8") as f:
    f.write(content)

# Now fix app_migration_view.py
view_path = r"D:\软件开发\ZenClean\src\ui\views\app_migration_view.py"
with open(view_path, "r", encoding="utf-8") as f:
    vcontent = f.read()

vcontent = vcontent.replace(
    'from core.app_migrator import APP_TARGETS, AppMigrator, MigrationPhase',
    'from core.app_migrator import APP_TARGETS, AppMigrator, MigrationPhase, resolve_target_path'
)

get_dir_size_code_old = """    def _get_dir_size(self, path_template):
        \"\"\"计算目录体积\"\"\"
        path = Path(os.path.expandvars(path_template))
        if not path.exists():
            return 0
        total = 0"""

get_dir_size_code_new = """    def _get_dir_size(self, path_template_or_list, target=None):
        \"\"\"计算目录体积\"\"\"
        path_str = resolve_target_path(target) if target else None
        if not path_str:
            return 0
        path = Path(path_str)
        if not path.exists():
            return 0
        total = 0"""

vcontent = vcontent.replace(get_dir_size_code_old, get_dir_size_code_new)

vcontent = vcontent.replace(
    'size = self._get_dir_size(target.path_template)',
    'size = self._get_dir_size(None, target=target)'
)


with open(view_path, "w", encoding="utf-8") as f:
    f.write(vcontent)

print(f"Patch applied successfully.")
