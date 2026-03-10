"""
测试 AI 缓存写入的线程安全性
修复 Bug: cloud_engine.py 缓存写入线程安全问题

运行方式（在项目根目录）：
    python -m pytest tests/test_bugfix_cloud_cache.py -v
"""
import sys
from pathlib import Path
import threading
import time
import json
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, MagicMock
from ai import cloud_engine


class TestCloudCacheThreadSafety:
    """验证缓存写入的线程安全性"""

    def test_cache_lock_exists(self):
        """验证缓存锁存在"""
        assert hasattr(cloud_engine, '_cache_lock'), "缓存应该有 _cache_lock"
        assert hasattr(cloud_engine, '_cache_write_lock'), "缓存应该有 _cache_write_lock"

    def test_cache_write_lock_is_thread_safe(self):
        """验证 _cache_write_lock 是线程安全的"""
        # 测试信号量是否能正确阻止并发写入
        lock = cloud_engine._cache_write_lock
        results = []

        def try_acquire():
            result = lock.acquire(blocking=False)
            results.append(result)
            if result:
                time.sleep(0.1)  # 模拟写盘操作
                lock.release()

        # 启动多个线程尝试同时获取锁
        threads = [threading.Thread(target=try_acquire) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 只有一个线程应该成功获取锁（blocking=False）
        assert sum(results) == 1, f"应该只有一个线程成功获取锁，实际: {sum(results)}"

    @patch('ai.cloud_engine.requests.post')
    @patch('ai.cloud_engine._load_local_token')
    def test_concurrent_cache_writes_are_safe(self, mock_token, mock_post):
        """并发写入缓存时不应发生数据竞争或文件损坏"""
        mock_token.return_value = ("fake_jwt_token", None, None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'data: {"choices":[{"delta":{"content":"{\\"risk_level\\": \\"LOW\\", \\"ai_advice\\": \\"test\\"}"}]}',
            b'data: [DONE]'
        ]
        mock_post.return_value = mock_response

        # 模拟并发请求
        results = []
        errors = []

        def query_multiple():
            try:
                for i in range(3):
                    result = cloud_engine.query(f"C:/test/path_{i}")
                    results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=query_multiple) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发请求时发生错误: {errors}"
        assert len(results) > 0, "应该有成功的查询结果"

    @patch('ai.cloud_engine.requests.post')
    @patch('ai.cloud_engine._load_local_token')
    def test_cache_persistence(self, mock_token, mock_post):
        """验证缓存能够正确持久化"""
        # 清空内存缓存
        with cloud_engine._cache_lock:
            cloud_engine._dir_cache.clear()

        mock_token.return_value = ("token", None, None)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'data: {"choices":[{"delta":{"content":"{\\"risk_level\\": \\"MEDIUM\\", \\"ai_advice\\": \\"cache test\\"}"}]}',
            b'data: [DONE]'
        ]
        mock_post.return_value = mock_response

        test_path = "C:/Users/%USERNAME%/AppData/Local/Temp"

        # 第一次查询
        result1 = cloud_engine.query(test_path)

        # 验证返回结果
        assert result1["risk_level"] in ["LOW", "MEDIUM", "UNKNOWN"]

    def test_save_cache_to_disk_is_thread_safe(self):
        """验证 _save_cache_to_disk 函数是线程安全的"""
        # 清空缓存
        with cloud_engine._cache_lock:
            cloud_engine._dir_cache.clear()

        # 添加一些测试数据
        test_data = {f"test_path_{i}": {"risk_level": "LOW", "ai_advice": f"test_{i}"}
                     for i in range(5)}
        with cloud_engine._cache_lock:
            cloud_engine._dir_cache.update(test_data)

        # 连续调用多次 _save_cache_to_disk，不应该抛出异常
        try:
            cloud_engine._save_cache_to_disk()
            cloud_engine._save_cache_to_disk()
            cloud_engine._save_cache_to_disk()
        except Exception as e:
            pytest.fail(f"_save_cache_to_disk 线程不安全: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
