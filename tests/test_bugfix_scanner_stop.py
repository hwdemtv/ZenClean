"""
测试 ScanWorker.stop() 方法确保回调被触发
修复 Bug: 扫描停止时回调未触发

运行方式（在项目根目录）：
    python -m pytest tests/test_bugfix_scanner_stop.py -v
"""
import sys
from pathlib import Path
import threading
import time
import os

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import MagicMock, patch
from core.scanner import ScanWorker


class TestScannerStopCallback:
    """验证扫描停止时 _on_done 回调被正确触发"""

    def test_stop_triggers_done_callback(self):
        """停止扫描时应触发 _on_done 回调"""
        nodes_result = []
        done_called = threading.Event()
        scanned_count = [0]
        skipped_count = [0]

        def on_nodes(batch):
            nodes_result.extend(batch)

        def on_done(total, skipped):
            scanned_count[0] = total
            skipped_count[0] = skipped
            done_called.set()

        # 使用一个肯定不存在的路径，避免实际扫描
        worker = ScanWorker(
            on_nodes=on_nodes,
            on_done=on_done,
            on_error=lambda e: None,
            targets=[Path("C:/Windows/Temp")]  # 使用实际可能存在的目录
        )

        # 启动扫描
        worker.start()

        # 等待一小段时间让扫描开始
        time.sleep(0.5)

        # 主动停止扫描
        worker.stop()

        # 等待回调被触发
        callback_triggered = done_called.wait(timeout=3)

        assert callback_triggered, "_on_done 回调未被触发，扫描停止后 UI 可能卡住"
        assert scanned_count[0] >= 0, "扫描计数应该被更新"

    def test_scan_completed_triggers_done_callback(self):
        """扫描正常完成时应触发 _on_done 回调"""
        done_called = threading.Event()
        final_total = [0]
        final_skipped = [0]

        def on_done(total, skipped):
            final_total[0] = total
            final_skipped[0] = skipped
            done_called.set()

        # 使用一个肯定不存在的路径来快速测试
        worker = ScanWorker(
            on_nodes=lambda batch: None,
            on_done=on_done,
            on_error=lambda e: None,
            targets=[Path("C:/NonExistentDirectory12345")]
        )

        worker.start()
        worker.join(timeout=30)

        callback_triggered = done_called.wait(timeout=1)
        assert callback_triggered, "正常完成后 _on_done 回调应被触发"

    @patch('core.scanner.os.path.isdir')
    @patch('core.scanner.os.walk')
    def test_stop_during_scan_triggers_callback(self, mock_walk, mock_isdir):
        """模拟扫描过程中主动停止，应触发回调"""
        mock_isdir.return_value = True

        # 模拟 os.walk 产生一些数据后被中断
        def slow_walk(*args, **kwargs):
            for i in range(3):
                yield (f"root_{i}", [f"dir_{i}"], [f"file_{i}.txt"])
                time.sleep(0.2)

        mock_walk.side_effect = slow_walk

        done_called = threading.Event()

        def on_done(total, skipped):
            done_called.set()

        worker = ScanWorker(
            on_nodes=lambda batch: None,
            on_done=on_done,
            on_error=lambda e: None,
            targets=[Path("C:/test")]
        )

        worker.start()
        time.sleep(0.3)  # 让扫描开始
        worker.stop()  # 主动停止

        callback_triggered = done_called.wait(timeout=3)
        assert callback_triggered, "扫描被主动停止后 _on_done 回调应被触发"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
