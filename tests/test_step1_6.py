"""
步骤 1.6 验收测试 —— 双重分诊清理引擎 (core/cleaner.py)

覆盖：
  A. CleanResult 数据结构
  B. LOW  → 物理删除（文件 & 目录树）
  C. MEDIUM → send2trash 移入回收站
  D. HIGH  → force_high=False 跳过 / force_high=True 执行
  E. CRISIS → 白名单兜底硬拒绝（即使节点 risk_level 被伪造）
  F. UNKNOWN → 跳过
  G. 不存在路径 → skipped
  H. on_progress 回调正确触发
  I. 混合批次：100 LOW + 10 MEDIUM 的计数与字节统计
  J. empty_recycle_bin 可调用不崩溃

运行：
    python -m pytest tests/test_step1_6.py -v
"""

import sys
import os
import shutil
import tempfile
import unittest.mock as mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from core.cleaner import clean, empty_recycle_bin, CleanResult, _dir_size


# ── 工具：构造 NodeDict ───────────────────────────────────────────────────────

def _node(path: str, risk: str, size: int = 0) -> dict:
    return {
        "path": path,
        "risk_level": risk,
        "size_bytes": size,
        "category": "test",
        "is_checked": True,
        "ai_advice": "",
        "is_whitelisted": risk == "CRISIS",
        "scan_ts": 0.0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Part A：CleanResult 结构
# ══════════════════════════════════════════════════════════════════════════════

class TestCleanResult:

    def test_total_bytes_property(self):
        r = CleanResult(freed_bytes=1000, trashed_bytes=500)
        assert r.total_bytes == 1500

    def test_defaults_all_zero(self):
        r = CleanResult()
        assert r.total == r.deleted == r.trashed == r.skipped == r.failed == 0
        assert r.freed_bytes == r.trashed_bytes == 0
        assert r.errors == []


# ══════════════════════════════════════════════════════════════════════════════
# Part B：LOW → 物理删除
# ══════════════════════════════════════════════════════════════════════════════

class TestLowPhysicalDelete:

    def test_single_file_deleted(self, tmp_path):
        """LOW 文件必须被物理删除，且不再存在于磁盘。"""
        f = tmp_path / "junk.tmp"
        f.write_bytes(b"x" * 1024)

        result = clean([_node(str(f), "LOW", 1024)])

        assert not f.exists()
        assert result.deleted == 1
        assert result.trashed == 0
        assert result.freed_bytes == 1024

    def test_freed_bytes_reflects_actual_size(self, tmp_path):
        """freed_bytes 应等于文件实际大小（以磁盘 stat 为准）。"""
        content = b"ZenClean" * 500   # 4000 bytes
        f = tmp_path / "data.bin"
        f.write_bytes(content)

        result = clean([_node(str(f), "LOW", 0)])   # 传 size=0，让引擎自己 stat

        assert result.freed_bytes == len(content)

    def test_directory_tree_deleted(self, tmp_path):
        """LOW 目录树必须整体删除。"""
        d = tmp_path / "cache_dir"
        d.mkdir()
        (d / "a.tmp").write_bytes(b"a" * 100)
        (d / "b.tmp").write_bytes(b"b" * 200)
        sub = d / "sub"
        sub.mkdir()
        (sub / "c.tmp").write_bytes(b"c" * 50)

        result = clean([_node(str(d), "LOW")])

        assert not d.exists()
        assert result.deleted == 1
        assert result.freed_bytes == 350

    def test_100_low_files_all_deleted(self, tmp_path):
        """验收标准：100 个 LOW 文件全部物理删除。"""
        files = []
        for i in range(100):
            f = tmp_path / f"file_{i:03d}.tmp"
            f.write_bytes(b"x" * 10)
            files.append(_node(str(f), "LOW", 10))

        result = clean(files)

        assert result.deleted == 100
        assert result.total == 100
        assert result.failed == 0
        assert result.freed_bytes == 1000
        # 确认磁盘上真的没有了
        remaining = list(tmp_path.iterdir())
        assert remaining == []


# ══════════════════════════════════════════════════════════════════════════════
# Part C：MEDIUM → send2trash
# ══════════════════════════════════════════════════════════════════════════════

class TestMediumTrash:

    def test_medium_goes_to_trash(self, tmp_path):
        """MEDIUM 文件必须进回收站（文件消失于原位，trashed+1）。"""
        f = tmp_path / "medium.log"
        f.write_bytes(b"log data" * 50)
        size = f.stat().st_size

        result = clean([_node(str(f), "MEDIUM", size)])

        assert not f.exists()          # 文件已离开原目录
        assert result.trashed == 1
        assert result.deleted == 0
        assert result.trashed_bytes == size

    def test_10_medium_files_all_trashed(self, tmp_path):
        """验收标准：10 个 MEDIUM 文件全部进回收站。"""
        nodes = []
        for i in range(10):
            f = tmp_path / f"medium_{i}.log"
            f.write_bytes(b"y" * 20)
            nodes.append(_node(str(f), "MEDIUM", 20))

        result = clean(nodes)

        assert result.trashed == 10
        assert result.deleted == 0
        assert result.failed == 0
        assert result.trashed_bytes == 200


# ══════════════════════════════════════════════════════════════════════════════
# Part D：HIGH —— force_high 开关
# ══════════════════════════════════════════════════════════════════════════════

class TestHighForce:

    def test_high_skipped_by_default(self, tmp_path):
        """force_high=False（默认）时，HIGH 文件必须被跳过，不删不移。"""
        f = tmp_path / "high_risk.dat"
        f.write_bytes(b"important")

        result = clean([_node(str(f), "HIGH")])

        assert f.exists()              # 文件仍在
        assert result.skipped == 1
        assert result.trashed == 0

    def test_high_trashed_when_forced(self, tmp_path):
        """force_high=True 时，HIGH 文件应进回收站。"""
        f = tmp_path / "high_force.dat"
        f.write_bytes(b"x" * 100)

        result = clean([_node(str(f), "HIGH", 100)], force_high=True)

        assert not f.exists()
        assert result.trashed == 1
        assert result.trashed_bytes == 100


# ══════════════════════════════════════════════════════════════════════════════
# Part E：CRISIS → 白名单硬拒绝
# ══════════════════════════════════════════════════════════════════════════════

class TestCrisisBlocked:

    def test_crisis_node_skipped(self, tmp_path):
        """CRISIS 节点不论文件是否存在，均跳过，不删不移。"""
        f = tmp_path / "crisis.tmp"
        f.write_bytes(b"sensitive")

        result = clean([_node(str(f), "CRISIS")])

        assert f.exists()              # 文件完好
        assert result.skipped == 1
        assert result.deleted == 0

    def test_whitelist_path_blocked_even_if_risk_faked_low(self):
        """
        防御性测试：即使 AI 返回了 LOW，但路径命中白名单，仍必须被拦截。
        这验证了 cleaner.py 内部白名单二次核查的存在。
        """
        # System32 路径不存在于测试机也没关系，白名单在文件存在性检查之前生效
        fake_node = _node(r"C:\Windows\System32\kernel32.dll", "LOW")

        result = clean([fake_node])

        assert result.skipped == 1
        assert result.deleted == 0
        assert result.freed_bytes == 0


# ══════════════════════════════════════════════════════════════════════════════
# Part F：UNKNOWN → 跳过
# ══════════════════════════════════════════════════════════════════════════════

class TestUnknownSkipped:

    def test_unknown_always_skipped(self, tmp_path):
        f = tmp_path / "mystery.xyz"
        f.write_bytes(b"?")

        result = clean([_node(str(f), "UNKNOWN")])

        assert f.exists()
        assert result.skipped == 1
        assert result.deleted == 0


# ══════════════════════════════════════════════════════════════════════════════
# Part G：路径不存在
# ══════════════════════════════════════════════════════════════════════════════

class TestNonExistentPath:

    def test_missing_low_counted_as_skipped(self, tmp_path):
        """不存在的 LOW 路径应计入 skipped，不 crash。"""
        phantom = str(tmp_path / "does_not_exist.tmp")
        result = clean([_node(phantom, "LOW")])

        assert result.skipped == 1
        assert result.failed == 0

    def test_missing_medium_counted_as_skipped(self, tmp_path):
        phantom = str(tmp_path / "ghost.log")
        result = clean([_node(phantom, "MEDIUM")])

        assert result.skipped == 1
        assert result.failed == 0


# ══════════════════════════════════════════════════════════════════════════════
# Part H：on_progress 回调
# ══════════════════════════════════════════════════════════════════════════════

class TestProgressCallback:

    def test_callback_called_for_each_node(self, tmp_path):
        """每个节点处理后必须触发一次 on_progress。"""
        files = []
        for i in range(5):
            f = tmp_path / f"cb_{i}.tmp"
            f.write_bytes(b"a")
            files.append(_node(str(f), "LOW", 1))

        calls = []
        clean(files, on_progress=lambda path, action, freed: calls.append((action, freed)))

        assert len(calls) == 5
        assert all(action == "deleted" for action, _ in calls)

    def test_freed_bytes_accumulates_in_callback(self, tmp_path):
        """on_progress 中 freed_bytes_so_far 应单调递增。"""
        files = []
        for i in range(3):
            f = tmp_path / f"acc_{i}.tmp"
            f.write_bytes(b"x" * 100)
            files.append(_node(str(f), "LOW", 100))

        freed_values = []
        clean(files, on_progress=lambda p, a, freed: freed_values.append(freed))

        assert freed_values == sorted(freed_values)   # 单调不减
        assert freed_values[-1] == 300

    def test_blocked_action_in_callback(self):
        """CRISIS 路径触发的回调 action 必须是 'blocked'。"""
        actions = []
        clean(
            [_node(r"C:\Windows\System32\ntoskrnl.exe", "LOW")],
            on_progress=lambda p, action, freed: actions.append(action),
        )
        assert actions == ["blocked"]


# ══════════════════════════════════════════════════════════════════════════════
# Part I：混合批次
# ══════════════════════════════════════════════════════════════════════════════

class TestMixedBatch:

    def test_100_low_10_medium_5_unknown(self, tmp_path):
        """混合批次：计数与字节数必须精确。"""
        nodes = []

        # 100 LOW
        for i in range(100):
            f = tmp_path / f"low_{i:03d}.tmp"
            f.write_bytes(b"L" * 50)
            nodes.append(_node(str(f), "LOW", 50))

        # 10 MEDIUM
        for i in range(10):
            f = tmp_path / f"med_{i:02d}.log"
            f.write_bytes(b"M" * 80)
            nodes.append(_node(str(f), "MEDIUM", 80))

        # 5 UNKNOWN
        for i in range(5):
            f = tmp_path / f"unk_{i}.xyz"
            f.write_bytes(b"U")
            nodes.append(_node(str(f), "UNKNOWN", 1))

        result = clean(nodes)

        assert result.total == 115
        assert result.deleted == 100
        assert result.trashed == 10
        assert result.skipped == 5
        assert result.failed == 0
        assert result.freed_bytes == 100 * 50
        assert result.trashed_bytes == 10 * 80

    def test_total_bytes_property_correct(self, tmp_path):
        f_low = tmp_path / "l.tmp"
        f_low.write_bytes(b"L" * 200)
        f_med = tmp_path / "m.log"
        f_med.write_bytes(b"M" * 100)

        result = clean([
            _node(str(f_low), "LOW", 200),
            _node(str(f_med), "MEDIUM", 100),
        ])

        assert result.total_bytes == 300


# ══════════════════════════════════════════════════════════════════════════════
# Part J：empty_recycle_bin
# ══════════════════════════════════════════════════════════════════════════════

class TestEmptyRecycleBin:

    def test_empty_recycle_bin_returns_bool(self):
        """empty_recycle_bin() 必须返回 bool，不抛异常。"""
        result = empty_recycle_bin()
        assert isinstance(result, bool)

    def test_empty_recycle_bin_does_not_crash(self):
        """重复调用也不应崩溃（回收站已空时返回 True）。"""
        empty_recycle_bin()
        empty_recycle_bin()
