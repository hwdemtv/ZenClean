"""pytest 全局夹具：统一注入 src 到模块搜索路径。

tests/ 下的测试统一以 `core.*` / `ai.*` / `config.*` / `ui.*` 导入项目源码，
此处集中完成 sys.path 注入，避免每个测试文件各自重复（部分旧文件仍保留
自己的注入语句，不影响正确性，将在渐进重构中移除）。
"""
import sys
from pathlib import Path

_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
