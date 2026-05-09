import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 将 src 目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.local_engine import analyze
from core.cleaner import clean

@pytest.fixture
def mock_fs():
    """模拟文件系统操作，防止真实删除"""
    with patch("pathlib.Path.exists") as m_exists, \
         patch("pathlib.Path.unlink") as m_unlink, \
         patch("pathlib.Path.is_dir") as m_is_dir, \
         patch("shutil.rmtree") as m_rmtree, \
         patch("core.cleaner.quarantine") as m_quar:
        
        m_exists.return_value = True
        m_is_dir.return_value = False
        m_quar.return_value = True
        
        yield {
            "exists": m_exists,
            "unlink": m_unlink,
            "is_dir": m_is_dir,
            "rmtree": m_rmtree,
            "quarantine": m_quar
        }

def test_integration_full_flow(mock_fs):
    """集成测试：扫描 -> 分析 -> 清理"""
    
    # 1. 模拟扫描器发现的一组文件
    scanned_files = [
        (r"C:\Windows\Temp\test.tmp", 1024),          # 命中规则: LOW (系统临时文件)
        (r"C:\Users\Admin\AppData\Local\Temp\j.log", 512), # 命中规则: LOW (临时日志)
        (r"C:\Users\Admin\Documents\WeChat Files\wxid\FileStorage\Cache\img.dat", 2048), # 命中规则: LOW (微信缓存)
        (r"C:\Windows\System32\kernel32.dll", 50000), # 命中白名单: CRISIS
        (r"C:\Unknown\Path\file.xyz", 100)            # 未命中规则: UNKNOWN
    ]
    
    # 2. 模拟分析阶段 (调用本地引擎)
    nodes = []
    for path, size in scanned_files:
        node = analyze(path, size)
        nodes.append(node)
    
    # 验证分析结果是否符合预期 (基于 file_kb.json 的默认规则)
    assert nodes[0]["risk_level"] == "LOW"
    assert nodes[1]["risk_level"] == "LOW"
    assert nodes[2]["risk_level"] == "LOW"
    assert nodes[3]["risk_level"] == "CRISIS"
    assert nodes[4]["risk_level"] == "UNKNOWN"
    
    # 3. 执行清理阶段
    result = clean(nodes, force_high=False)
    
    # 4. 验证最终效果
    # LOW 的 3 个应该被 unlink
    assert result.deleted == 3
    assert mock_fs["unlink"].call_count == 3
    
    # MEDIUM 的 0 个应该被 quarantine
    assert result.trashed == 0
    assert mock_fs["quarantine"].call_count == 0
    
    # CRISIS 和 UNKNOWN 的 2 个应该被跳过/拦截
    assert result.skipped == 2
    
    # 验证释放的字节数 (1024 + 512 + 2048 = 3584)
    assert result.freed_bytes == 3584
    # 验证隔离的字节数 (0)
    assert result.trashed_bytes == 0

def test_integration_high_risk_flow(mock_fs):
    """测试集成流程中 HIGH 风险的处理逻辑"""
    # 模拟一个 HIGH 风险节点 (假设匹配到规则)
    # 我们直接构造 NodeDict 模拟引擎输出，或者寻找能命中 HIGH 的规则
    # 这里直接模拟一个可能命中的路径（如果有规则的话，或者手动注入）
    
    high_risk_node = {
        "path": r"C:\Users\Admin\Documents\WeChat Files\wxid\FileStorage\Image\2024\old.jpg",
        "risk_level": "HIGH",
        "size_bytes": 10000
    }
    
    # Case 1: 不强制清理 HIGH
    res1 = clean([high_risk_node], force_high=False)
    assert res1.skipped == 1
    assert res1.trashed == 0
    
    # Case 2: 强制清理 HIGH (用户已确认)
    res2 = clean([high_risk_node], force_high=True)
    assert res2.trashed == 1
    assert res2.trashed_bytes == 10000
    assert mock_fs["quarantine"].call_count == 1
