import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 将 src 目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.cleaner import clean, CleanResult

@pytest.fixture
def mock_whitelist():
    with patch("core.whitelist.is_protected") as mock:
        yield mock

@pytest.fixture
def mock_quarantine():
    with patch("core.cleaner.quarantine") as mock:
        yield mock

@pytest.fixture
def mock_path_exists():
    with patch("pathlib.Path.exists") as mock:
        yield mock

@pytest.fixture
def mock_unlink():
    with patch("pathlib.Path.unlink") as mock:
        yield mock

@pytest.fixture
def mock_rmtree():
    with patch("shutil.rmtree") as mock:
        yield mock

def test_clean_low_risk(mock_whitelist, mock_path_exists, mock_unlink):
    """测试 LOW 风险等级执行物理删除"""
    mock_whitelist.return_value = False
    mock_path_exists.return_value = True
    
    nodes = [
        {"path": r"C:\temp\file1.tmp", "risk_level": "LOW", "size_bytes": 1024}
    ]
    
    result = clean(nodes)
    
    assert result.deleted == 1
    assert result.freed_bytes == 1024
    assert result.total == 1
    mock_unlink.assert_called_once()

def test_clean_medium_risk(mock_whitelist, mock_path_exists, mock_quarantine):
    """测试 MEDIUM 风险等级进入隔离沙箱"""
    mock_whitelist.return_value = False
    mock_path_exists.return_value = True
    mock_quarantine.return_value = True
    
    nodes = [
        {"path": r"C:\temp\app_cache.dat", "risk_level": "MEDIUM", "size_bytes": 2048}
    ]
    
    result = clean(nodes)
    
    assert result.trashed == 1
    assert result.trashed_bytes == 2048
    mock_quarantine.assert_called_once_with(r"C:\temp\app_cache.dat", 2048)

def test_clean_high_risk_no_force(mock_whitelist, mock_path_exists):
    """测试 HIGH 风险等级在没有 force_high 时被跳过"""
    mock_whitelist.return_value = False
    mock_path_exists.return_value = True
    
    nodes = [
        {"path": r"C:\temp\important.bak", "risk_level": "HIGH", "size_bytes": 5000}
    ]
    
    result = clean(nodes, force_high=False)
    
    assert result.skipped == 1
    assert result.trashed == 0

def test_clean_high_risk_with_force(mock_whitelist, mock_path_exists, mock_quarantine):
    """测试 HIGH 风险等级在有 force_high 时进入隔离沙箱"""
    mock_whitelist.return_value = False
    mock_path_exists.return_value = True
    mock_quarantine.return_value = True
    
    nodes = [
        {"path": r"C:\temp\important.bak", "risk_level": "HIGH", "size_bytes": 5000}
    ]
    
    result = clean(nodes, force_high=True)
    
    assert result.trashed == 1
    assert result.trashed_bytes == 5000
    mock_quarantine.assert_called_once()

def test_clean_crisis_blocked(mock_whitelist):
    """测试 CRISIS 风险等级被拦截"""
    mock_whitelist.return_value = False
    
    nodes = [
        {"path": r"C:\Windows\System32\kernel32.dll", "risk_level": "CRISIS", "size_bytes": 0}
    ]
    
    result = clean(nodes)
    
    assert result.skipped == 1
    assert result.deleted == 0
    assert result.trashed == 0

def test_clean_whitelist_protection(mock_whitelist):
    """测试白名单二次核查拦截"""
    mock_whitelist.return_value = True
    
    nodes = [
        {"path": r"C:\Windows\System32\cmd.exe", "risk_level": "LOW", "size_bytes": 100}
    ]
    
    result = clean(nodes)
    
    assert result.skipped == 1
    assert result.deleted == 0

def test_clean_file_not_found(mock_whitelist, mock_path_exists):
    """测试文件不存在时跳过"""
    mock_whitelist.return_value = False
    mock_path_exists.return_value = False
    
    nodes = [
        {"path": r"C:\temp\missing.txt", "risk_level": "LOW", "size_bytes": 100}
    ]
    
    result = clean(nodes)
    
    assert result.skipped == 1
    assert result.deleted == 0

def test_clean_multiple_nodes(mock_whitelist, mock_path_exists, mock_unlink, mock_quarantine):
    """测试混合多个节点的处理"""
    mock_whitelist.return_value = False
    mock_path_exists.return_value = True
    mock_quarantine.return_value = True
    
    nodes = [
        {"path": "f1", "risk_level": "LOW", "size_bytes": 10},
        {"path": "f2", "risk_level": "MEDIUM", "size_bytes": 20},
        {"path": "f3", "risk_level": "CRISIS", "size_bytes": 30},
        {"path": "f4", "risk_level": "UNKNOWN", "size_bytes": 40},
    ]
    
    result = clean(nodes)
    
    assert result.total == 4
    assert result.deleted == 1
    assert result.trashed == 1
    assert result.skipped == 2
    assert result.freed_bytes == 10
    assert result.trashed_bytes == 20
