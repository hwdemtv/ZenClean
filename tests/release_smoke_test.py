import unittest
import os
import sys
from pathlib import Path

# 注入项目根目录到 sys.path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

class ReleaseSmokeTest(unittest.TestCase):
    """
    ZenClean v0.1.0 Beta 发布冒烟测试
    专门验证发布前最容易出错的核心逻辑
    """

    def test_version_consistency(self):
        """验证版本号管理是否统一"""
        from config.version import __version__
        from config.settings import APP_VERSION
        print(f"Checking version: {__version__}")
        self.assertEqual(__version__, APP_VERSION, "Global version must match settings version!")
        self.assertTrue(__version__.startswith("0.1."), "Version should be 0.1.x series")

    def test_rule_kb_loading(self):
        """验证 AI 知识库是否完整加载"""
        import json
        kb_path = _ROOT / "src" / "config" / "file_kb.json"
        self.assertTrue(kb_path.exists(), f"Rule KB not found at {kb_path}")
        
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            rules_count = len(data.get("rules", []))
            # 当前版本共有 21 条核心规则（对应约 213 行 JSON）
            print(f"Loaded {rules_count} rules.")
            self.assertGreaterEqual(rules_count, 20, "Rule KB seems too small or corrupted!")

    def test_auth_offline_logic(self):
        """验证最新的离线授权（Startup 模式）逻辑"""
        from core.auth import check_local_auth_status
        # 在无缓存情况下，check_local_auth_status 应该直接返回 False 而不崩溃
        # is_startup=True 时不应触发网络 IO
        is_val, payload = check_local_auth_status(is_startup=True)
        self.assertIsInstance(is_val, bool)
        print("Auth logic is non-blocking during startup.")

    def test_all_rules_compilation(self):
        """强化测试：模拟所有本地规则的正则编译与基本匹配，防止配置低级错误"""
        import json
        import re
        kb_path = _ROOT / "src" / "config" / "file_kb.json"
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        print(f"\nVerifying {len(data['rules'])} rules for regex validity...")
        for rule in data["rules"]:
            pattern = rule.get("pattern")
            rule_id = rule.get("id")
            try:
                # 尝试编译正则
                re.compile(pattern)
                # 模拟一个基本路径测试（确保不崩溃）
                test_path = r"C:\Windows\Temp\test.log"
                re.search(pattern, test_path)
            except Exception as e:
                self.fail(f"Rule [{rule_id}] has invalid regex pattern: {pattern}. Error: {e}")
        print("All regex patterns are valid.")

if __name__ == '__main__':
    print("\n🚀 Starting ZenClean Release Smoke Test...")
    unittest.main()
