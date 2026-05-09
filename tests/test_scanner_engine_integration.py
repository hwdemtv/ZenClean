import sys
import os
import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

# 将 src 目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.scanner import ScanWorker

@pytest.fixture
def mock_walk_data():
    """模拟 os.walk 返回的数据结构"""
    # (root, dirs, files)
    return [
        (r"C:\Temp", ["subdir"], ["test.log", "important.dll"]),
        (r"C:\Temp\subdir", [], ["cache.dat"])
    ]

@patch("os.path.isdir")
@patch("os.walk")
@patch("os.stat")
@patch("ai.local_engine.dispatch")
def test_scanner_engine_dispatch(mock_dispatch, mock_stat, mock_walk, mock_isdir, mock_walk_data):
    """验证扫描器是否正确遍历并调用引擎调度"""
    
    # 模拟目录存在
    mock_isdir.return_value = True
    # 模拟 os.walk
    mock_walk.return_value = mock_walk_data
    
    # 模拟 os.stat 返回普通文件属性 (非隐藏, 非系统, 非 reparse)
    mock_attr = MagicMock()
    mock_attr.st_file_attributes = 0
    mock_attr.st_size = 100
    mock_stat.return_value = mock_attr
    
    # 模拟引擎返回 NodeDict
    mock_dispatch.return_value = {"path": "mock", "risk_level": "LOW"}
    
    nodes_received = []
    def on_nodes(batch):
        nodes_received.extend(batch)
        
    done_event = threading.Event()
    def on_done(total, skipped):
        done_event.set()
        
    # 创建扫描任务
    worker = ScanWorker(
        on_nodes=on_nodes,
        on_done=on_done,
        on_error=lambda e: print(f"Error: {e}"),
        targets=[Path(r"C:\Temp")]
    )
    
    worker.start()
    assert done_event.wait(timeout=2)
    
    # 应该扫描到 2 个文件 (test.log, cache.dat)
    # important.dll 因为后缀被白名单拦截，被 scanner 过滤
    assert len(nodes_received) == 2
    assert mock_dispatch.call_count == 2

@patch("os.path.isdir")
@patch("os.walk")
@patch("os.stat")
@patch("core.whitelist.is_protected")
def test_scanner_whitelist_filtering(mock_is_protected, mock_stat, mock_walk, mock_isdir):
    """验证扫描器是否在目录级和文件级正确应用白名单过滤"""
    
    mock_isdir.return_value = True
    # 1个目录包含1个受保护目录和1个受保护文件，以及1个正常文件
    mock_walk.return_value = [
        (r"C:\Targets", ["protected_dir", "normal_dir"], ["protected.exe", "normal.txt"]),
        (r"C:\Targets\normal_dir", [], ["data.tmp"])
    ]
    
    # 模拟属性
    mock_attr = MagicMock()
    mock_attr.st_file_attributes = 0
    mock_attr.st_size = 50
    mock_stat.return_value = mock_attr
    
    # 定义保护逻辑
    def side_effect_protected(path):
        return "protected" in str(path).lower()
    mock_is_protected.side_effect = side_effect_protected
    
    nodes_received = []
    def on_nodes(batch):
        nodes_received.extend(batch)
        
    done_event = threading.Event()
    def on_done(total, skipped):
        done_event.set()
        
    worker = ScanWorker(
        on_nodes=on_nodes,
        on_done=on_done,
        on_error=lambda e: None,
        targets=[Path(r"C:\Targets")]
    )
    
    worker.start()
    done_event.wait(timeout=2)
    
    # 结果分析：
    # 1. protected_dir 被过滤，不会进入。
    # 2. normal_dir 进入。
    # 3. protected.exe 被过滤。
    # 4. normal.txt 保留。
    # 5. data.tmp 保留。
    # 总共应该有 2 个节点。
    assert len(nodes_received) == 2
    for node in nodes_received:
        assert "protected" not in node["path"].lower()
