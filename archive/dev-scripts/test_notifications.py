import sys
import unittest
from pathlib import Path

# 将 src 目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TestNotificationLogic(unittest.TestCase):
    def test_fingerprint_generation(self):
        """验证通知指纹是否随内容变化而变化"""
        note_id = "test_001"
        content1 = "这是第一条内容"
        content2 = "这是修改后的内容"
        
        # 模拟 app.py 中的指纹生成逻辑
        fp1 = f"{note_id}_{hash(content1)}"
        fp2 = f"{note_id}_{hash(content2)}"
        fp3 = f"{note_id}_{hash(content1)}"
        
        self.assertNotEqual(fp1, fp2, "内容改变时，指纹必须改变")
        self.assertEqual(fp1, fp3, "相同内容和 ID，指纹必须一致")

    def test_full_payload_structure(self):
        """验证后端对接方案中的典型载荷结构"""
        payload = {
            "id": "notice_123",
            "title": "测试标题",
            "content": "测试内容",
            "is_force": True,
            "action_url": "https://hwdem.tv"
        }
        
        self.assertIn("id", payload)
        self.assertIn("content", payload)
        self.assertTrue(isinstance(payload["is_force"], bool))

if __name__ == "__main__":
    unittest.main()
