import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.whitelist import is_protected
from ai.local_engine import dispatch

class TestZenCleanEngine(unittest.TestCase):
    def test_whitelist_protection(self):
        # 绝对不可达拦截测试
        self.assertTrue(is_protected(r"C:\Windows\System32\kernel32.dll"))
        self.assertTrue(is_protected(r"C:\Windows\SysWOW64\Config"))
        self.assertTrue(is_protected(r"C:\pagefile.sys"))
        self.assertTrue(is_protected(r"C:\Windows\WinSxS\some_temp"))
        self.assertTrue(is_protected(r"C:\Program Files\Windows Defender\MpCmdRun.exe"))
        
        # 不受保护的文件测试
        self.assertFalse(is_protected(r"C:\some_random_folder\test.txt"))
        self.assertFalse(is_protected(r"C:\Windows\Temp\test.tmp"))

    def test_local_engine_rules(self):
        # 验证 1.1 验收标准中列出的匹配用例
        res1 = dispatch(r"C:\Windows\System32\cmd.exe")
        self.assertEqual(res1["risk_level"], "CRISIS")
        self.assertTrue(res1["is_whitelisted"])

        res2 = dispatch(r"C:\Windows\Temp\some.tmp")
        self.assertEqual(res2["risk_level"], "LOW")
        
        res3 = dispatch(r"C:\Users\Admin\AppData\Local\Temp\junk.txt")
        self.assertEqual(res3["risk_level"], "LOW")
        
        res4 = dispatch(r"C:\Users\Admin\Documents\WeChat Files\wxid_123\FileStorage\Cache\image.dat")
        self.assertEqual(res4["risk_level"], "LOW")
        self.assertEqual(res4["category"], "social_cache")
        
        res5 = dispatch(r"C:\Users\Admin\Documents\WeChat Files\wxid_123\FileStorage\Image\2024\1.jpg")
        self.assertEqual(res5["risk_level"], "HIGH")
        
        res6 = dispatch(r"C:\Windows\SoftwareDistribution\Download\update.cab")
        self.assertEqual(res6["risk_level"], "MEDIUM")
        
    def test_unknown_fallback(self):
        # 验证未知文件 (未命中任何规则且不在白名单) 
        # 注意：在第二阶段及以后，dispatch 会尝试云端提权，如果命中缓存可能返回 MEDIUM
        res = dispatch(r"C:\Users\Admin\Desktop\MyContract.pdf")
        self.assertIn(res["risk_level"], ["UNKNOWN", "MEDIUM"]) # 兼容云端提权后的结果


if __name__ == '__main__':
    unittest.main()
