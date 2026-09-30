"""
AI 批处理聚合器集成测试（无网络版本）

原版本直接调用云端 query()，无 Token 时仅在网络层报错且不做断言（恒通过）。
现改为注入 mock batch handler，验证 CloudBatcher 的核心契约：
  - 离散 submit_async 请求被聚合为 ≤ max_batch_size 的批次
  - 每个路径的异步回调均被触发且携带正确结果
  - post_batch 全局回调收到归一化后的结果映射
"""
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.batch_processor import batch_processor


def test_batch_aggregation_and_callbacks():
    # 保存原 handler（cloud_engine 在 import 时注册了真实云端处理器），测试后恢复
    original_handler = batch_processor._batch_handler
    post_batches = []
    original_post_cb = batch_processor._post_batch_cb

    try:
        # 清空历史遗留的待处理队列（其他测试可能残留 pending 项）
        with batch_processor._lock:
            batch_processor._pending_queue.clear()
            batch_processor._events.clear()
            batch_processor._callbacks.clear()

        observed_batches: list[list[str]] = []

        def mock_handler(paths):
            observed_batches.append(list(paths))
            return [{"path": p, "risk_level": "LOW", "ai_advice": "mock"} for p in paths]

        batch_processor.set_batch_handler(mock_handler)
        batch_processor.set_post_batch_callback(lambda m: post_batches.append(dict(m)))

        results: dict[str, dict] = {}
        results_lock = threading.Lock()

        def make_cb(p):
            def cb(res):
                with results_lock:
                    results[p] = res
            return cb

        # 模拟 10 个并发请求（超过 max_batch_size=8，应触发 8+2 两批）
        test_paths = [f"C:\\Mock\\Path_{i}" for i in range(10)]
        for p in test_paths:
            placeholder = batch_processor.submit_async(p, callback=make_cb(p))
            assert placeholder["risk_level"] == "ANALYZING"

        # 等待全部回调返回（聚合窗口 0.6s + 处理耗时，给足余量）
        deadline = time.time() + 10
        while len(results) < len(test_paths) and time.time() < deadline:
            time.sleep(0.1)

        # 1. 所有路径都收到了回调结果
        assert len(results) == len(test_paths), f"回调缺失: 仅 {len(results)}/{len(test_paths)} 完成"
        for p in test_paths:
            assert results[p]["risk_level"] == "LOW"
            assert results[p]["path"] == p

        # 2. 批次聚合契约：每批 ≤ max_batch_size，总量守恒
        assert observed_batches, "mock handler 未被调用"
        for batch in observed_batches:
            assert len(batch) <= batch_processor.max_batch_size, f"批次超限: {len(batch)}"
        assert sum(len(b) for b in observed_batches) == len(test_paths), "批次总量与提交量不一致"

        # 3. post_batch 全局回调被触发
        assert post_batches, "post_batch 回调未触发"
    finally:
        batch_processor.set_batch_handler(original_handler)
        batch_processor.set_post_batch_callback(original_post_cb)
