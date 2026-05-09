import sys
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 将 src 目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.space_analyzer import get_disk_usage, scan_top_folders, FolderInfo

@pytest.fixture
def mock_disk_usage():
    with patch("shutil.disk_usage") as mock:
        mock.return_value = (1000, 400, 600) # total, used, free
        yield mock

@pytest.fixture
def mock_scandir():
    with patch("os.scandir") as mock:
        yield mock

def test_get_disk_usage(mock_disk_usage):
    usage = get_disk_usage("C:")
    assert usage.total == 1000
    assert usage.used == 400
    assert usage.free == 600
    assert usage.drive == "C:"

def test_folder_info_dataclass():
    p = Path(r"C:\test")
    fi = FolderInfo(path=p, size_bytes=100, name="test", is_junction=False, is_protected=False)
    assert fi.name == "test"
    assert fi.size_bytes == 100

@patch("core.space_analyzer._fast_dir_size")
@patch("core.space_analyzer._is_reparse_point")
def test_scan_top_folders(mock_reparse, mock_size, mock_scandir):
    """测试大文件夹扫描过滤逻辑"""
    # 模拟两个文件夹：一个大的，一个系统目录（应跳过）
    mock_item1 = MagicMock()
    mock_item1.is_dir.return_value = True
    mock_item1.path = r"C:\Users"
    mock_item1.name = "Users"
    
    mock_item2 = MagicMock()
    mock_item2.is_dir.return_value = True
    mock_item2.path = r"C:\Windows"
    mock_item2.name = "Windows"
    
    # 使用 context manager 模拟 scandir
    mock_scandir.return_value.__enter__.return_value = [mock_item1, mock_item2]
    
    mock_reparse.return_value = False
    mock_size.return_value = 200 * 1024 * 1024 # 200MB
    
    results = scan_top_folders([r"C:\ "])
    
    # Windows 目录应该被过滤掉，只剩下 Users
    assert len(results) == 1
    assert results[0].name == "Users"
    assert results[0].size_bytes == 200 * 1024 * 1024
