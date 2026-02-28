"""
步骤 1.2 验收测试

覆盖：
  - cloud_mock.query() 行为
  - local_engine.sanitize_path() 路径脱敏
  - local_engine.dispatch() 统一调度路由
  - dispatch() 与 analyze() 对旧有步骤 1.1 测试的兼容性

运行方式（在项目根目录）：
    python -m pytest tests/test_step1_2.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from ai import cloud_mock
from ai import local_engine


# ══════════════════════════════════════════════════════════════════════════════
# Part A：cloud_mock 行为测试
# ══════════════════════════════════════════════════════════════════════════════

class TestCloudMock:

    def test_query_returns_unknown(self):
        """第一阶段 cloud_mock 必须始终返回 UNKNOWN。"""
        result = cloud_mock.query(r"C:\Users\%USERNAME%\Desktop\unknown.xyz")
        assert result["risk_level"] == "UNKNOWN"

    def test_query_returns_nonempty_advice(self):
        """返回的 ai_advice 不得为空字符串。"""
        result = cloud_mock.query(r"C:\Users\%USERNAME%\something\unknown.xyz")
        assert isinstance(result["ai_advice"], str)
        assert len(result["ai_advice"]) > 0

    def test_query_has_required_keys(self):
        """CloudResult 必须包含 risk_level 和 ai_advice 字段。"""
        result = cloud_mock.query("any_path")
        assert "risk_level" in result
        assert "ai_advice" in result

    def test_is_mock_returns_true(self):
        """is_mock() 在第一阶段必须返回 True。"""
        assert cloud_mock.is_mock() is True

    def test_query_ignores_path_content(self):
        """mock 对任意路径均返回相同结果（不做任何路径分析）。"""
        r1 = cloud_mock.query("path_a")
        r2 = cloud_mock.query("completely_different_path")
        assert r1["risk_level"] == r2["risk_level"]
        assert r1["ai_advice"] == r2["ai_advice"]


# ══════════════════════════════════════════════════════════════════════════════
# Part B：路径脱敏测试 (sanitize_path)
# ══════════════════════════════════════════════════════════════════════════════

class TestSanitizePath:

    def test_replaces_real_username(self):
        """真实用户名应被替换为 %USERNAME% 占位符。"""
        result = local_engine.sanitize_path(r"C:\Users\张三\AppData\Local\Temp\junk.tmp")
        assert "张三" not in result
        assert "%USERNAME%" in result

    def test_replaces_english_username(self):
        result = local_engine.sanitize_path(r"C:\Users\JohnDoe\Documents\file.txt")
        assert "JohnDoe" not in result
        assert "%USERNAME%" in result

    def test_path_after_username_preserved(self):
        """脱敏后，用户名之后的子路径必须完整保留。"""
        result = local_engine.sanitize_path(
            r"C:\Users\Admin\AppData\Local\Google\Chrome\User Data\Default\Cache\f_001"
        )
        assert r"AppData\Local\Google\Chrome\User Data\Default\Cache\f_001" in result

    def test_non_user_path_unchanged(self):
        """不含用户目录的路径脱敏后应保持不变。"""
        path = r"C:\Windows\Temp\somefile.tmp"
        assert local_engine.sanitize_path(path) == path

    def test_case_insensitive_users(self):
        """Users 大小写变体也应被正确脱敏。"""
        result = local_engine.sanitize_path(r"c:\users\HwDem\Documents\private.pdf")
        assert "HwDem" not in result
        assert "%USERNAME%" in result

    def test_sanitized_path_starts_correctly(self):
        """脱敏后路径必须以 C:\\Users\\%USERNAME%\\ 开头。"""
        result = local_engine.sanitize_path(r"C:\Users\SomeUser\Desktop\file.txt")
        assert result.startswith(r"C:\Users\%USERNAME%")


# ══════════════════════════════════════════════════════════════════════════════
# Part C：dispatch() 统一调度测试
# ══════════════════════════════════════════════════════════════════════════════

class TestDispatch:

    def test_known_low_path_routed_locally(self):
        """本地规则能命中的路径，dispatch 必须返回本地引擎结果（非 UNKNOWN）。"""
        node = local_engine.dispatch(r"C:\Windows\Temp\junk.tmp")
        assert node["risk_level"] == "LOW"
        assert node["is_checked"] is True

    def test_known_high_path_routed_locally(self):
        node = local_engine.dispatch(
            r"C:\Users\Admin\Documents\WeChat Files\wxid_x\FileStorage\Image\photo.jpg"
        )
        assert node["risk_level"] == "HIGH"
        assert node["is_checked"] is False

    def test_crisis_path_routed_locally(self):
        """白名单路径 dispatch 必须返回 CRISIS，不走云端。"""
        node = local_engine.dispatch(r"C:\Windows\System32\kernel32.dll")
        assert node["risk_level"] == "CRISIS"
        assert node["is_whitelisted"] is True

    def test_unknown_path_gets_cloud_advice(self):
        """未被本地规则命中的路径，dispatch 必须调用 cloud_mock 填充 ai_advice。"""
        node = local_engine.dispatch(r"C:\Users\Admin\Desktop\mystery_file.xyz")
        assert node["risk_level"] == "UNKNOWN"
        # cloud_mock 填充的 advice 不得为空
        assert isinstance(node["ai_advice"], str)
        assert len(node["ai_advice"]) > 0

    def test_unknown_path_not_checked(self):
        """UNKNOWN 路径在第一阶段必须默认不勾选（UI 置灰）。"""
        node = local_engine.dispatch(r"C:\Users\Admin\Desktop\unknown.abc")
        assert node["is_checked"] is False

    def test_dispatch_returns_full_nodedict(self):
        """dispatch() 返回的 NodeDict 必须包含所有 8 个规定字段。"""
        node = local_engine.dispatch(r"C:\Windows\Temp\test.tmp", size_bytes=2048)
        required = {"path", "size_bytes", "risk_level", "category",
                    "is_checked", "ai_advice", "is_whitelisted", "scan_ts"}
        assert required.issubset(node.keys())
        assert node["size_bytes"] == 2048

    def test_dispatch_size_bytes_preserved(self):
        """size_bytes 参数必须原样传递到返回结果。"""
        node = local_engine.dispatch(r"C:\Windows\Temp\x.tmp", size_bytes=99999)
        assert node["size_bytes"] == 99999

    def test_dispatch_path_preserved(self):
        """path 字段必须保留原始路径（未脱敏），脱敏仅在内部上报时使用。"""
        original = r"C:\Users\RealName\Desktop\unknown.xyz"
        node = local_engine.dispatch(original)
        assert node["path"] == original
        assert "RealName" in node["path"]  # 原始路径未被脱敏

    def test_reload_rules_does_not_break_dispatch(self):
        """热重载规则后 dispatch() 仍应正常工作。"""
        local_engine.reload_rules()
        node = local_engine.dispatch(r"C:\Windows\Temp\after_reload.tmp")
        assert node["risk_level"] == "LOW"
