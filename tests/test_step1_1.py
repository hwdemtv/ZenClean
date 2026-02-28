"""
步骤 1.1 验收测试

覆盖白名单守卫（whitelist.py）与本地规则引擎（ai/local_engine.py）的 15 个核心用例。
运行方式（在项目根目录）：
    python -m pytest tests/test_step1_1.py -v
"""

import sys
from pathlib import Path

# 将 src 目录加入模块搜索路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from core import whitelist
from ai import local_engine


# ══════════════════════════════════════════════════════════════════════════════
# Part A：白名单守卫测试（whitelist.is_protected）
# ══════════════════════════════════════════════════════════════════════════════

class TestWhitelistProtected:
    """命中白名单的路径必须返回 True。"""

    def test_system32_file(self):
        """System32 下的核心 DLL 必须被拦截。"""
        assert whitelist.is_protected(r"C:\Windows\System32\kernel32.dll") is True

    def test_system32_subdir(self):
        """System32 子目录必须被拦截。"""
        assert whitelist.is_protected(r"C:\Windows\System32\drivers\etc\hosts") is True

    def test_syswow64(self):
        """SysWOW64 下的任意路径必须被拦截。"""
        assert whitelist.is_protected(r"C:\Windows\SysWOW64\ntdll.dll") is True

    def test_windows_defender(self):
        """Windows Defender 目录必须被拦截。"""
        assert whitelist.is_protected(
            r"C:\Program Files\Windows Defender\MsMpEng.exe"
        ) is True

    def test_pagefile(self):
        """pagefile.sys 必须被拦截（文件名正则层）。"""
        assert whitelist.is_protected(r"C:\pagefile.sys") is True

    def test_hiberfil(self):
        """hiberfil.sys 必须被拦截。"""
        assert whitelist.is_protected(r"C:\hiberfil.sys") is True

    def test_sys_extension(self):
        """任意 .sys 驱动文件必须被拦截。"""
        assert whitelist.is_protected(r"C:\Windows\Temp\somedriver.sys") is True

    def test_junction_documents_and_settings(self):
        """Documents and Settings Junction 必须被拦截。"""
        assert whitelist.is_protected(r"C:\Documents and Settings\Admin") is True

    def test_winsxs(self):
        """WinSxS 组件存储必须被拦截。"""
        assert whitelist.is_protected(r"C:\Windows\WinSxS\x86_microsoft.windows") is True


class TestWhitelistSafe:
    """不在白名单内的路径必须返回 False，让后续规则引擎处理。"""

    def test_user_temp(self):
        assert whitelist.is_protected(
            r"C:\Users\Admin\AppData\Local\Temp\junk.tmp"
        ) is False

    def test_windows_temp(self):
        assert whitelist.is_protected(r"C:\Windows\Temp\cbslog.txt") is False

    def test_wechat_cache(self):
        assert whitelist.is_protected(
            r"C:\Users\Admin\Documents\WeChat Files\wxid_abc\FileStorage\Cache\img.dat"
        ) is False

    def test_chrome_cache(self):
        assert whitelist.is_protected(
            r"C:\Users\Admin\AppData\Local\Google\Chrome\User Data\Default\Cache\f_000001"
        ) is False


# ══════════════════════════════════════════════════════════════════════════════
# Part B：本地规则引擎测试（local_engine.analyze）
# ══════════════════════════════════════════════════════════════════════════════

class TestLocalEngineRiskLevels:

    def test_system32_returns_crisis(self):
        """白名单路径经引擎分析后必须返回 CRISIS。"""
        node = local_engine.analyze(r"C:\Windows\System32\kernel32.dll")
        assert node["risk_level"] == "CRISIS"
        assert node["is_whitelisted"] is True
        assert node["is_checked"] is False

    def test_windows_temp_returns_low(self):
        node = local_engine.analyze(r"C:\Windows\Temp\tmpXXX.tmp")
        assert node["risk_level"] == "LOW"
        assert node["category"] == "system_temp"
        assert node["is_checked"] is True

    def test_user_temp_returns_low(self):
        node = local_engine.analyze(
            r"C:\Users\TestUser\AppData\Local\Temp\somefile.log"
        )
        assert node["risk_level"] == "LOW"
        assert node["category"] == "system_temp"
        assert node["is_checked"] is True

    def test_wechat_cache_returns_low(self):
        node = local_engine.analyze(
            r"C:\Users\Admin\Documents\WeChat Files\wxid_abc123\FileStorage\Cache\abc.dat"
        )
        assert node["risk_level"] == "LOW"
        assert node["category"] == "social_cache"
        assert node["is_checked"] is True

    def test_wechat_image_returns_high(self):
        """微信 Image 目录必须返回 HIGH 且默认不勾选。"""
        node = local_engine.analyze(
            r"C:\Users\Admin\Documents\WeChat Files\wxid_abc123\FileStorage\Image\2024-01\photo.jpg"
        )
        assert node["risk_level"] == "HIGH"
        assert node["category"] == "social_media"
        assert node["is_checked"] is False

    def test_wechat_video_returns_high(self):
        node = local_engine.analyze(
            r"C:\Users\Admin\Documents\WeChat Files\wxid_xyz\FileStorage\Video\clip.mp4"
        )
        assert node["risk_level"] == "HIGH"
        assert node["is_checked"] is False

    def test_windows_update_returns_medium(self):
        node = local_engine.analyze(
            r"C:\Windows\SoftwareDistribution\Download\abc123\update.cab"
        )
        assert node["risk_level"] == "MEDIUM"
        assert node["category"] == "windows_update"
        assert node["is_checked"] is False

    def test_chrome_cache_returns_low(self):
        node = local_engine.analyze(
            r"C:\Users\Admin\AppData\Local\Google\Chrome\User Data\Default\Cache\f_000001"
        )
        assert node["risk_level"] == "LOW"
        assert node["category"] == "browser_cache"

    def test_unknown_path_returns_unknown(self):
        """完全未知路径必须返回 UNKNOWN 且默认不勾选。"""
        node = local_engine.analyze(r"C:\Users\Admin\Desktop\my_project\something.xyz")
        assert node["risk_level"] == "UNKNOWN"
        assert node["is_checked"] is False
        assert node["is_whitelisted"] is False

    def test_nodedict_has_required_fields(self):
        """NodeDict 必须包含所有规定字段。"""
        node = local_engine.analyze(r"C:\Windows\Temp\test.tmp", size_bytes=1024)
        required_fields = {
            "path", "size_bytes", "risk_level", "category",
            "is_checked", "ai_advice", "is_whitelisted", "scan_ts"
        }
        assert required_fields.issubset(node.keys())
        assert node["size_bytes"] == 1024
        assert isinstance(node["scan_ts"], float)

    def test_crisis_is_not_checked(self):
        """CRISIS 级别无论规则如何，is_checked 必须为 False。"""
        node = local_engine.analyze(r"C:\Windows\System32\ntoskrnl.exe")
        assert node["is_checked"] is False

    def test_assert_safe_raises_on_protected(self):
        """assert_safe 对白名单路径必须抛出 PermissionError。"""
        with pytest.raises(PermissionError):
            whitelist.assert_safe(r"C:\Windows\System32\kernel32.dll")

    def test_assert_safe_passes_on_clean(self):
        """assert_safe 对干净路径不抛出异常。"""
        whitelist.assert_safe(r"C:\Users\Admin\AppData\Local\Temp\junk.tmp")  # 不应抛出
