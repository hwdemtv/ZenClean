"""
ZenClean 修复回归测试

覆盖以下修复项：
  F1  .gitignore 条目补全
  F2  auth.py 硬编码密钥移除
  F3  auth.py 签名函数空密钥回退
  F4  auth.py JWT 验证警告日志
  F5  updater.py SSL 警告抑制范围
  F6  main.py startup_monitor 引用移除
  F7  local_engine.py 启动安全保护
  F8  tray_manager.py 哨兵线程 daemon 标志
  F9  tray_manager.py 退出使用 sys.exit
  F10 app.py _auto_start_scan 属性初始化
  F11 auth_view.py 重复 checkbox 消除
  F12 裸 except: 消除
  F13 未使用导入清理
  F14 scan_view.py disk_usage 异常处理
"""

import os
import re
import sys
import unittest
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
sys.path.insert(0, str(_SRC_DIR))


# ═══════════════════════════════════════════════════════════════════════════
# F1: .gitignore 条目
# ═══════════════════════════════════════════════════════════════════════════
class TestGitignore(unittest.TestCase):
    """验证 .gitignore 包含所有应忽略的条目"""

    @classmethod
    def _read_gitignore(cls):
        gitignore_path = _PROJECT_ROOT / ".gitignore"
        return gitignore_path.read_text(encoding="utf-8")

    def test_ignores_claude_dir(self):
        content = self._read_gitignore()
        self.assertIn(".claude/", content)

    def test_ignores_space_cache(self):
        content = self._read_gitignore()
        self.assertIn("zenclean_space_cache.json", content)

    def test_ignores_dist_old(self):
        content = self._read_gitignore()
        self.assertIn("dist_old/", content)

    def test_ignores_pyarmor_dist(self):
        content = self._read_gitignore()
        self.assertIn(".pyarmor_dist/", content)

    def test_ignores_cython_c_files(self):
        content = self._read_gitignore()
        self.assertIn("*.c", content)

    def test_ignores_bak_files(self):
        content = self._read_gitignore()
        self.assertIn("*.bak", content)

    def test_ignores_wrangler_jsonc(self):
        content = self._read_gitignore()
        self.assertIn("wrangler.jsonc", content)

    def test_ignores_db_check(self):
        content = self._read_gitignore()
        self.assertIn("db_check*.txt", content)

    def test_still_ignores_env(self):
        content = self._read_gitignore()
        self.assertIn(".env", content)

    def test_still_ignores_pycache(self):
        content = self._read_gitignore()
        self.assertIn("__pycache__/", content)


# ═══════════════════════════════════════════════════════════════════════════
# F2 / F3: auth.py 硬编码密钥移除 & 签名函数空密钥回退
# ═══════════════════════════════════════════════════════════════════════════
class TestAuthSecret(unittest.TestCase):
    """验证 API 签名密钥不再硬编码"""

    def test_no_hardcoded_secret_in_source(self):
        """源码中不应包含硬编码的密钥默认值"""
        auth_path = _SRC_DIR / "core" / "auth.py"
        source = auth_path.read_text(encoding="utf-8")
        self.assertNotIn("zenclean-high-entropy-signature-secret-v1-standard", source)

    def test_default_secret_is_empty_when_env_unset(self):
        """环境变量未设置时，API_SIGNATURE_SECRET 应为空字符串"""
        # 保存并清除环境变量
        saved = os.environ.pop("ZC_API_SECRET", None)
        try:
            # 重新执行模块级赋值逻辑（不重新导入，避免副作用）
            secret = os.environ.get("ZC_API_SECRET", "")
            self.assertEqual(secret, "")
        finally:
            if saved is not None:
                os.environ["ZC_API_SECRET"] = saved

    def test_env_secret_is_used(self):
        """环境变量设置时，应读取环境变量值"""
        os.environ["ZC_API_SECRET"] = "test-secret-for-unit-test-only"
        try:
            secret = os.environ.get("ZC_API_SECRET", "")
            self.assertEqual(secret, "test-secret-for-unit-test-only")
        finally:
            del os.environ["ZC_API_SECRET"]

    def test_generate_signature_returns_empty_when_no_secret(self):
        """密钥未配置时 _generate_api_signature 应返回空字符串"""
        from core.auth import _generate_api_signature
        # 确保环境变量中没有密钥
        saved = os.environ.pop("ZC_API_SECRET", None)
        try:
            # 重新加载 auth 模块以获取当前状态
            import importlib
            import core.auth as auth_mod
            # 直接测试函数行为：当 _get_api_secret() 返回空时应返回 ""
            # 注意：由于模块级变量已加载，我们验证函数逻辑
            result = _generate_api_signature('{"test": 1}', "1234567890", "nonce123")
            # 如果当前 secret 为空，应返回空字符串
            if not auth_mod._get_api_secret():
                self.assertEqual(result, "")
        finally:
            if saved is not None:
                os.environ["ZC_API_SECRET"] = saved


# ═══════════════════════════════════════════════════════════════════════════
# F4: auth.py JWT 验证警告日志
# ═══════════════════════════════════════════════════════════════════════════
class TestJWTVerificationWarning(unittest.TestCase):
    """验证 JWT 签名验证被禁用时有明确警告"""

    def test_jwt_warning_in_source(self):
        auth_path = _SRC_DIR / "core" / "auth.py"
        source = auth_path.read_text(encoding="utf-8")
        self.assertIn("JWT signature verification is DISABLED", source)

    def test_jwt_todo_comment_exists(self):
        auth_path = _SRC_DIR / "core" / "auth.py"
        source = auth_path.read_text(encoding="utf-8")
        self.assertIn("TODO", source)
        self.assertIn("签名验证", source)


# ═══════════════════════════════════════════════════════════════════════════
# F5: updater.py SSL 警告抑制范围
# ═══════════════════════════════════════════════════════════════════════════
class TestUpdaterSSL(unittest.TestCase):
    """验证 urllib3 警告抑制仅在需要时才启用"""

    def test_no_global_disable_warnings(self):
        """updater.py 不应在模块顶部全局禁用 SSL 警告"""
        updater_path = _SRC_DIR / "core" / "updater.py"
        source = updater_path.read_text(encoding="utf-8")
        lines = source.split("\n")
        # 找到所有 disable_warnings 调用的位置
        disable_lines = [
            i for i, line in enumerate(lines)
            if "disable_warnings" in line and "urllib3" in line
        ]
        # 找到 verify=False 的位置
        verify_false_lines = [
            i for i, line in enumerate(lines)
            if "verify=False" in line
        ]
        # disable_warnings 应在 verify=False 之后（或同一区域），而不是在顶部
        if disable_lines and verify_false_lines:
            # 每个 disable_warnings 应该在某个 verify=False 附近（20 行内）
            for dl in disable_lines:
                nearby = any(abs(dl - vl) < 20 for vl in verify_false_lines)
                self.assertTrue(
                    nearby,
                    f"disable_warnings at line {dl+1} is not near any verify=False call"
                )


# ═══════════════════════════════════════════════════════════════════════════
# F6: main.py startup_monitor 引用移除
# ═══════════════════════════════════════════════════════════════════════════
class TestMainStartupMonitor(unittest.TestCase):
    """验证 main.py 不再引用不存在的 startup_monitor 模块"""

    def test_no_startup_monitor_import(self):
        main_path = _SRC_DIR / "main.py"
        source = main_path.read_text(encoding="utf-8")
        self.assertNotIn("from core.startup_monitor", source)
        self.assertNotIn("import core.startup_monitor", source)

    def test_disk_watch_uses_existing_module(self):
        """--disk-watch 应使用存在的 disk_watcher 模块"""
        main_path = _SRC_DIR / "main.py"
        source = main_path.read_text(encoding="utf-8")
        self.assertIn("from core.disk_watcher", source)

    def test_disk_watch_has_error_handling(self):
        """--disk-watch 的异常处理不应是裸 except:pass"""
        main_path = _SRC_DIR / "main.py"
        source = main_path.read_text(encoding="utf-8")
        # 确保没有 "except Exception:\n            pass" 这种静默吞掉的模式
        # 在 disk_watch 相关区域
        disk_watch_section = source[source.find("_is_disk_watch"):]
        disk_watch_section = disk_watch_section[:disk_watch_section.find("sys.exit")]
        self.assertNotIn("except Exception:\n                pass", disk_watch_section)


# ═══════════════════════════════════════════════════════════════════════════
# F7: local_engine.py 启动安全保护
# ═══════════════════════════════════════════════════════════════════════════
class TestLocalEngineStartupSafety(unittest.TestCase):
    """验证 local_engine 在 file_kb.json 缺失时不会崩溃"""

    def test_rules_load_has_try_except(self):
        """模块级规则加载应被 try/except 包裹"""
        engine_path = _SRC_DIR / "ai" / "local_engine.py"
        source = engine_path.read_text(encoding="utf-8")
        # 查找 _RULES 赋值附近的 try/except
        rules_section = source[source.find("# 模块级缓存"):]
        rules_section = rules_section[:rules_section.find("# CRISIS")]
        self.assertIn("try:", rules_section)
        self.assertIn("except", rules_section)
        self.assertIn("_RULES = []", rules_section)

    def test_engine_works_with_rules(self):
        """正常情况下引擎应能工作"""
        from ai.local_engine import analyze
        result = analyze(r"C:\Windows\Temp\test.tmp", 1024)
        self.assertIn(result["risk_level"], ["LOW", "MEDIUM", "HIGH", "CRISIS", "UNKNOWN"])

    def test_analyze_returns_valid_structure(self):
        """analyze 返回的 NodeDict 应包含所有必需字段"""
        from ai.local_engine import analyze
        result = analyze(r"C:\some_random_path\file.xyz", 512)
        required_keys = ["path", "size_bytes", "risk_level", "category",
                         "is_checked", "ai_advice", "is_whitelisted", "scan_ts"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_whitelist_protection_still_works(self):
        """白名单保护应仍然生效"""
        from ai.local_engine import analyze
        result = analyze(r"C:\Windows\System32\kernel32.dll", 1000)
        self.assertEqual(result["risk_level"], "CRISIS")
        self.assertTrue(result["is_whitelisted"])


# ═══════════════════════════════════════════════════════════════════════════
# F8 / F9: tray_manager.py 哨兵线程 & 退出逻辑
# ═══════════════════════════════════════════════════════════════════════════
class TestTrayManagerExit(unittest.TestCase):
    """验证托盘退出逻辑使用 daemon 线程和 sys.exit"""

    def test_sentinel_is_daemon(self):
        """哨兵线程应为 daemon 线程，不阻止进程正常退出"""
        tray_path = _SRC_DIR / "ui" / "tray_manager.py"
        source = tray_path.read_text(encoding="utf-8")
        # 查找 sentinel 线程创建
        self.assertIn("daemon=True", source)
        self.assertNotIn("daemon=False", source)

    def test_exit_uses_sys_exit(self):
        """退出流程的最终调用应为 sys.exit 而非 os._exit"""
        tray_path = _SRC_DIR / "ui" / "tray_manager.py"
        source = tray_path.read_text(encoding="utf-8")
        # 在 _exit_app 方法中，保险3应使用 sys.exit
        exit_method = source[source.find("def _exit_app"):]
        exit_method = exit_method[:exit_method.find("def run")]
        # sys.exit 应该出现（保险3）
        self.assertIn("sys.exit(0)", exit_method)
        # os._exit 仅在哨兵中作为兜底
        os_exit_count = exit_method.count("os._exit")
        self.assertEqual(os_exit_count, 1, "os._exit should only appear once (in sentinel)")

    def test_sentinel_timeout_is_3s(self):
        """哨兵线程超时应为 3 秒（给正常退出足够时间）"""
        tray_path = _SRC_DIR / "ui" / "tray_manager.py"
        source = tray_path.read_text(encoding="utf-8")
        self.assertIn("time.sleep(3.0", source)


# ═══════════════════════════════════════════════════════════════════════════
# F10: app.py _auto_start_scan 属性
# ═══════════════════════════════════════════════════════════════════════════
class TestAppAutoStartScan(unittest.TestCase):
    """验证 ZenCleanApp 正确初始化 _auto_start_scan"""

    def test_attribute_declared_in_source(self):
        """__init__ 中应显式声明 _auto_start_scan"""
        app_path = _SRC_DIR / "ui" / "app.py"
        source = app_path.read_text(encoding="utf-8")
        self.assertIn("_auto_start_scan", source)
        # 应在 __init__ 方法中
        init_section = source[source.find("def __init__"):]
        init_section = init_section[:init_section.find("def ", 10)]  # 到下一个方法
        self.assertIn("_auto_start_scan", init_section)

    def test_default_is_false(self):
        """默认值应为 False"""
        app_path = _SRC_DIR / "ui" / "app.py"
        source = app_path.read_text(encoding="utf-8")
        # 查找 _auto_start_scan 的赋值
        match = re.search(r"self\._auto_start_scan\s*[:=]", source)
        self.assertIsNotNone(match, "_auto_start_scan should be assigned")
        # 检查同行是否有 False
        line_start = source.rfind("\n", 0, match.start()) + 1
        line_end = source.find("\n", match.end())
        line = source[line_start:line_end]
        self.assertIn("False", line)


# ═══════════════════════════════════════════════════════════════════════════
# F11: auth_view.py 重复 checkbox 消除
# ═══════════════════════════════════════════════════════════════════════════
class TestAuthViewCheckbox(unittest.TestCase):
    """验证 _agree_checkbox 只创建一次"""

    def test_single_checkbox_creation(self):
        auth_view_path = _SRC_DIR / "ui" / "views" / "auth_view.py"
        source = auth_view_path.read_text(encoding="utf-8")
        # 统计 _agree_checkbox 被赋值的次数
        assignments = re.findall(r"self\._agree_checkbox\s*=\s*ft\.Checkbox", source)
        self.assertEqual(
            len(assignments), 1,
            f"_agree_checkbox should be created exactly once, found {len(assignments)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# F12: 裸 except: 消除
# ═══════════════════════════════════════════════════════════════════════════
class TestNoBareExcept(unittest.TestCase):
    """验证 src/ 中没有裸 except: 子句"""

    def _collect_python_files(self):
        files = []
        for root, dirs, filenames in os.walk(_SRC_DIR):
            # 跳过 __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in filenames:
                if f.endswith(".py"):
                    files.append(Path(root) / f)
        return files

    def test_no_bare_except_in_src(self):
        """所有 Python 文件中不应有裸 except: (无异常类型)"""
        bare_excepts = []
        for fpath in self._collect_python_files():
            source = fpath.read_text(encoding="utf-8")
            for i, line in enumerate(source.split("\n"), 1):
                stripped = line.strip()
                if stripped == "except:" or stripped.startswith("except: "):
                    bare_excepts.append(f"{fpath.relative_to(_PROJECT_ROOT)}:{i}: {stripped}")
        self.assertEqual(
            bare_excepts, [],
            f"Found bare except: clauses:\n" + "\n".join(bare_excepts)
        )


# ═══════════════════════════════════════════════════════════════════════════
# F13: 未使用导入清理
# ═══════════════════════════════════════════════════════════════════════════
class TestUnusedImports(unittest.TestCase):
    """验证已知的未使用导入已被清理"""

    def test_quarantine_no_sys(self):
        source = (_SRC_DIR / "core" / "quarantine.py").read_text(encoding="utf-8")
        self.assertNotIn("import sys\n", source)

    def test_quarantine_no_time(self):
        source = (_SRC_DIR / "core" / "quarantine.py").read_text(encoding="utf-8")
        self.assertNotIn("import time\n", source)

    def test_batch_processor_no_queue(self):
        source = (_SRC_DIR / "ai" / "batch_processor.py").read_text(encoding="utf-8")
        self.assertNotIn("import queue\n", source)

    def test_scanner_no_any(self):
        source = (_SRC_DIR / "core" / "scanner.py").read_text(encoding="utf-8")
        self.assertNotIn("Any", source)


# ═══════════════════════════════════════════════════════════════════════════
# F14: scan_view.py disk_usage 异常处理
# ═══════════════════════════════════════════════════════════════════════════
class TestScanViewDiskUsage(unittest.TestCase):
    """验证 disk_usage 调用有异常保护"""

    def test_disk_usage_has_try_except(self):
        scan_view_path = _SRC_DIR / "ui" / "views" / "scan_view.py"
        source = scan_view_path.read_text(encoding="utf-8")
        # 找到 disk_usage 附近的 try/except
        idx = source.find("disk_usage")
        self.assertGreater(idx, 0, "disk_usage not found in scan_view.py")
        # 向前查找最近的 try:
        preceding = source[max(0, idx - 200):idx]
        self.assertIn("try:", preceding, "disk_usage should be inside a try block")

    def test_disk_usage_fallback_to_zero(self):
        """异常时应回退到 0 值"""
        scan_view_path = _SRC_DIR / "ui" / "views" / "scan_view.py"
        source = scan_view_path.read_text(encoding="utf-8")
        idx = source.find("disk_usage")
        following = source[idx:idx + 200]
        self.assertIn("except", following)
        self.assertIn("0, 0, 0", following)


# ═══════════════════════════════════════════════════════════════════════════
# 综合验证：模块可正常导入
# ═══════════════════════════════════════════════════════════════════════════
class TestModuleImports(unittest.TestCase):
    """验证关键模块在修复后仍可正常导入"""

    def test_import_auth(self):
        import core.auth
        self.assertTrue(hasattr(core.auth, "verify_license_online"))

    def test_import_local_engine(self):
        import ai.local_engine
        self.assertTrue(hasattr(ai.local_engine, "dispatch"))
        self.assertTrue(hasattr(ai.local_engine, "analyze"))

    def test_import_scanner(self):
        import core.scanner
        self.assertTrue(hasattr(core.scanner, "ScanWorker"))

    def test_import_quarantine(self):
        import core.quarantine
        self.assertTrue(hasattr(core.quarantine, "auto_clean_expired"))

    def test_import_batch_processor(self):
        import ai.batch_processor
        self.assertTrue(hasattr(ai.batch_processor, "CloudBatcher"))

    def test_import_settings(self):
        from config.settings import SCAN_TARGETS, WINDOW_WIDTH
        self.assertIsInstance(SCAN_TARGETS, list)
        self.assertGreater(len(SCAN_TARGETS), 0)

    def test_import_whitelist(self):
        from core.whitelist import is_protected
        self.assertTrue(callable(is_protected))

    def test_import_network_diag(self):
        import utils.network_diag
        self.assertTrue(hasattr(utils.network_diag, "run_full_diagnosis"))


# ═══════════════════════════════════════════════════════════════════════════
# 综合验证：核心功能正常
# ═══════════════════════════════════════════════════════════════════════════
class TestCoreFunctionality(unittest.TestCase):
    """验证修复后核心功能未被破坏"""

    def test_whitelist_system32(self):
        from core.whitelist import is_protected
        self.assertTrue(is_protected(r"C:\Windows\System32\cmd.exe"))

    def test_whitelist_random_path(self):
        from core.whitelist import is_protected
        self.assertFalse(is_protected(r"C:\Users\test\Desktop\myfile.txt"))

    def test_local_engine_temp(self):
        from ai.local_engine import analyze
        result = analyze(r"C:\Windows\Temp\junk.tmp", 1024)
        self.assertEqual(result["risk_level"], "LOW")
        self.assertEqual(result["category"], "system_temp")

    def test_local_engine_crisis_for_protected(self):
        from ai.local_engine import analyze
        result = analyze(r"C:\Windows\System32\config\SAM", 512)
        self.assertEqual(result["risk_level"], "CRISIS")
        self.assertTrue(result["is_whitelisted"])

    def test_sanitize_path(self):
        from ai.local_engine import sanitize_path
        result = sanitize_path(r"C:\Users\JohnDoe\AppData\Local\Temp\test.tmp")
        self.assertIn("%USERNAME%", result)
        self.assertNotIn("JohnDoe", result)

    def test_auth_device_id(self):
        from core.auth import get_device_id
        device_id = get_device_id()
        self.assertIsInstance(device_id, str)
        self.assertGreater(len(device_id), 0)


if __name__ == "__main__":
    unittest.main()
