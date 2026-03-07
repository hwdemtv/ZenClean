import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# 将 src 目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.updater import check_for_updates

class TestUpdaterMirror(unittest.TestCase):
    @patch("requests.get")
    def test_mirror_fallback_logic(self, mock_get):
        """验证当首个镜像失败时，是否能自动切换到下一个镜像"""
        
        # 模拟第一个请求失败（Timeout），第二个请求成功（200 OK）
        resp_fail = MagicMock()
        resp_fail.status_code = 502
        
        resp_success = MagicMock()
        resp_success.status_code = 200
        resp_success.json.return_value = {
            "tag_name": "v9.9.9",
            "body": "Mock Update Content"
        }
        
        # 定义 side_effect：先报错一次，再成功一次
        mock_get.side_effect = [Exception("Network Error"), resp_success]
        
        results = []
        def on_res(has_update, ver, url, body):
            results.append((has_update, ver))

        # 执行检查（这里会启动线程，我们直接测内部逻辑或通过 join 等待）
        # 为了单元测试简单，我们直接 patch threading.Thread 
        with patch("threading.Thread") as mock_thread:
            # 拿到 Thread 的执行函数并手动运行它
            check_for_updates(on_res, manual=True)
            target_func = mock_thread.call_args[1]["target"]
            target_func()
        
        self.assertTrue(len(results) > 0)
        self.assertTrue(results[0][0], "应该检测到更新")
        self.assertEqual(results[0][1], "9.9.9")
        # 验证 requests.get 被调用了至少 2 次（第一个失败，第二个镜像成功）
        self.assertGreaterEqual(mock_get.call_count, 2)

if __name__ == "__main__":
    unittest.main()
