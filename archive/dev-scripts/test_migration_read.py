import sys
from pathlib import Path

# 将项目 src 目录加入环境变量以支持直接运行测试
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.migration import get_shell_folders, SHELL_FOLDER_KEYS

try:
    folders = get_shell_folders()
    for key, path in folders.items():
        if key in SHELL_FOLDER_KEYS:
            print(f"{SHELL_FOLDER_KEYS[key]}: {path}")
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
