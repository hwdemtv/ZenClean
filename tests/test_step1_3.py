"""
步骤 1.3 验收测试

覆盖：
  A. ScanWorker 内部工具函数（Junction 检测、隐藏文件过滤）
  B. QueueConsumer 回调路由（done / error / 正常批次 / stop）
  C. 端到端集成：用真实临时目录跑 ScanWorker，验证批次推送与哨兵

运行方式（在项目根目录）：
    python -m pytest tests/test_step1_3.py -v
"""

import multiprocessing
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from core.queue_consumer import QueueConsumer
from core.scanner import ScanWorker, _is_junction_or_symlink, _is_hidden_or_system


# ══════════════════════════════════════════════════════════════════════════════
# 工具函数：构造临时目录树
# ══════════════════════════════════════════════════════════════════════════════

def _make_temp_tree(base: Path, files: list[str]) -> None:
    """在 base 下按 files 列表创建文件（自动创建子目录）。"""
    for rel in files:
        full = base / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("dummy content", encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Part A：ScanWorker 辅助判断函数
# ══════════════════════════════════════════════════════════════════════════════

class TestIsJunctionOrSymlink:

    def test_regular_dir_is_not_junction(self, tmp_path):
        """普通目录不是 Junction。"""
        d = tmp_path / "regular"
        d.mkdir()
        with os.scandir(tmp_path) as it:
            for entry in it:
                if entry.name == "regular":
                    assert _is_junction_or_symlink(entry) is False

    def test_symlink_file_is_detected(self, tmp_path):
        """普通文件符号链接必须被检测为 True。"""
        target = tmp_path / "target.txt"
        target.write_text("x")
        link = tmp_path / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("当前环境无法创建符号链接（需管理员权限）")
        with os.scandir(tmp_path) as it:
            for entry in it:
                if entry.name == "link.txt":
                    assert _is_junction_or_symlink(entry) is True

    def test_regular_file_is_not_junction(self, tmp_path):
        """普通文件不是 Junction。"""
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with os.scandir(tmp_path) as it:
            for entry in it:
                if entry.name == "file.txt":
                    assert _is_junction_or_symlink(entry) is False


class TestIsHiddenOrSystem:

    def test_regular_file_not_hidden(self, tmp_path):
        """普通文件不应被判定为隐藏/系统文件。"""
        f = tmp_path / "normal.txt"
        f.write_text("x")
        with os.scandir(tmp_path) as it:
            for entry in it:
                if entry.name == "normal.txt":
                    assert _is_hidden_or_system(entry) is False


# ══════════════════════════════════════════════════════════════════════════════
# Part B：QueueConsumer 回调路由
# ══════════════════════════════════════════════════════════════════════════════

class TestQueueConsumer:

    def _make_queue(self):
        return multiprocessing.Queue()

    def test_done_sentinel_triggers_on_done(self):
        """收到 done 哨兵后必须调用 on_done 回调，并携带正确的 total/skipped。"""
        q = self._make_queue()
        results = {}

        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: None,
            on_done=lambda total, skipped: results.update(total=total, skipped=skipped),
            on_error=lambda msg: None,
        )
        consumer.start()
        q.put({"type": "done", "total": 42, "skipped": 7})
        consumer.join(timeout=3)

        assert results.get("total") == 42
        assert results.get("skipped") == 7

    def test_error_sentinel_triggers_on_error(self):
        """收到 error 哨兵后必须调用 on_error 回调，并携带消息字符串。"""
        q = self._make_queue()
        errors = []

        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: None,
            on_done=lambda t, s: None,
            on_error=lambda msg: errors.append(msg),
        )
        consumer.start()
        q.put({"type": "error", "message": "磁盘读取失败"})
        consumer.join(timeout=3)

        assert len(errors) == 1
        assert "磁盘读取失败" in errors[0]

    def test_batch_triggers_on_nodes(self):
        """正常批次必须触发 on_nodes 回调，且参数为 list。"""
        q = self._make_queue()
        received: list[list] = []

        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: received.append(nodes),
            on_done=lambda t, s: None,
            on_error=lambda msg: None,
        )
        consumer.start()

        fake_batch = [{"path": "C:\\fake\\file.tmp", "risk_level": "LOW"}]
        q.put(fake_batch)
        q.put({"type": "done", "total": 1, "skipped": 0})
        consumer.join(timeout=3)

        assert len(received) == 1
        assert received[0] == fake_batch

    def test_multiple_batches_all_delivered(self):
        """多批次必须全部被 on_nodes 接收，不丢包。"""
        q = self._make_queue()
        received_nodes: list[dict] = []

        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: received_nodes.extend(nodes),
            on_done=lambda t, s: None,
            on_error=lambda msg: None,
        )
        consumer.start()

        for i in range(5):
            q.put([{"path": f"C:\\file_{i}.tmp", "risk_level": "LOW"}])
        q.put({"type": "done", "total": 5, "skipped": 0})
        consumer.join(timeout=3)

        assert len(received_nodes) == 5

    def test_stop_terminates_consumer(self):
        """调用 stop() 后消费线程应在轮询间隔内退出。"""
        q = self._make_queue()
        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: None,
            on_done=lambda t, s: None,
            on_error=lambda msg: None,
        )
        consumer.start()
        consumer.stop()
        consumer.join(timeout=3)
        assert not consumer.is_alive()

    def test_empty_batch_not_forwarded(self):
        """空列表不应触发 on_nodes（消费线程内部过滤）。"""
        q = self._make_queue()
        received: list = []

        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: received.append(nodes),
            on_done=lambda t, s: None,
            on_error=lambda msg: None,
        )
        consumer.start()
        q.put([])                                      # 空批次
        q.put({"type": "done", "total": 0, "skipped": 0})
        consumer.join(timeout=3)

        assert received == []


# ══════════════════════════════════════════════════════════════════════════════
# Part C：端到端集成测试
# ══════════════════════════════════════════════════════════════════════════════

class TestScanWorkerIntegration:
    """
    用临时目录模拟真实扫描，验证：
      - 所有文件最终通过批次到达主进程
      - done 哨兵携带正确 total
      - NodeDict 格式完整
      - 扫描不阻塞主线程（消费线程正常工作）
    """

    def _run_scan(self, root: Path) -> tuple[list[dict], dict]:
        """在临时目录上运行完整的 Worker+Consumer，返回 (all_nodes, done_info)。"""
        q: multiprocessing.Queue = multiprocessing.Queue()
        all_nodes: list[dict] = []
        done_info: dict = {}
        finished = threading.Event()

        def on_nodes(nodes):
            all_nodes.extend(nodes)

        def on_done(total, skipped):
            done_info["total"] = total
            done_info["skipped"] = skipped
            finished.set()

        def on_error(msg):
            done_info["error"] = msg
            finished.set()

        consumer = QueueConsumer(q, on_nodes=on_nodes, on_done=on_done, on_error=on_error)
        worker = ScanWorker(q, root=root, skip_hidden=False)

        consumer.start()
        worker.start()

        finished.wait(timeout=30)
        worker.join(timeout=5)

        return all_nodes, done_info

    def test_all_files_discovered(self, tmp_path):
        """临时目录中的所有文件都必须被扫描到（total 与创建数量一致）。"""
        files = [
            "subdir_a/file1.tmp",
            "subdir_a/file2.log",
            "subdir_b/file3.txt",
            "root_file.dat",
        ]
        _make_temp_tree(tmp_path, files)

        all_nodes, done_info = self._run_scan(tmp_path)

        assert "error" not in done_info, f"扫描出错: {done_info.get('error')}"
        assert done_info.get("total") == len(files)
        assert len(all_nodes) == len(files)

    def test_done_sentinel_received(self, tmp_path):
        """扫描完成后必须收到 done 哨兵，total >= 0。"""
        (tmp_path / "a.txt").write_text("x")
        _, done_info = self._run_scan(tmp_path)

        assert "total" in done_info
        assert done_info["total"] >= 0

    def test_nodedict_fields_complete(self, tmp_path):
        """每个 NodeDict 必须包含 8 个规定字段。"""
        (tmp_path / "sample.txt").write_text("content")
        all_nodes, _ = self._run_scan(tmp_path)

        required = {"path", "size_bytes", "risk_level", "category",
                    "is_checked", "ai_advice", "is_whitelisted", "scan_ts"}
        for node in all_nodes:
            assert required.issubset(node.keys()), f"字段缺失: {node}"

    def test_size_bytes_correct(self, tmp_path):
        """NodeDict 的 size_bytes 必须与文件实际大小一致。"""
        content = b"Hello ZenClean!" * 100   # 1500 bytes
        f = tmp_path / "sized.bin"
        f.write_bytes(content)

        all_nodes, _ = self._run_scan(tmp_path)
        sized_nodes = [n for n in all_nodes if n["path"].endswith("sized.bin")]

        assert len(sized_nodes) == 1
        assert sized_nodes[0]["size_bytes"] == len(content)

    def test_paths_are_absolute(self, tmp_path):
        """NodeDict 中的 path 必须为绝对路径。"""
        (tmp_path / "x.tmp").write_text("x")
        all_nodes, _ = self._run_scan(tmp_path)

        for node in all_nodes:
            assert os.path.isabs(node["path"]), f"非绝对路径：{node['path']}"

    def test_whitelist_dirs_excluded(self, tmp_path):
        """白名单保护路径内的文件不得出现在扫描结果中。"""
        # 白名单检测仅对真实系统路径生效，此处验证非保护目录被扫到
        (tmp_path / "safe.tmp").write_text("safe")
        all_nodes, _ = self._run_scan(tmp_path)

        for node in all_nodes:
            assert not node["is_whitelisted"], (
                f"临时目录下不应出现 is_whitelisted=True 的条目：{node['path']}"
            )

    def test_batch_size_respected(self, tmp_path):
        """当文件数 > SCAN_BATCH_SIZE 时，必须分多批推送（每批 ≤ SCAN_BATCH_SIZE）。"""
        from config.settings import SCAN_BATCH_SIZE

        # 创建略多于一个批次的文件
        N = SCAN_BATCH_SIZE + 10
        for i in range(N):
            (tmp_path / f"file_{i:04d}.tmp").write_text(f"content_{i}")

        q: multiprocessing.Queue = multiprocessing.Queue()
        batches: list[list] = []
        finished = threading.Event()

        consumer = QueueConsumer(
            q,
            on_nodes=lambda nodes: batches.append(nodes),
            on_done=lambda t, s: finished.set(),
            on_error=lambda msg: finished.set(),
        )
        worker = ScanWorker(q, root=tmp_path, skip_hidden=False)

        consumer.start()
        worker.start()
        finished.wait(timeout=30)
        worker.join(timeout=5)

        # 必须有多于一批
        assert len(batches) > 1, "文件数超过批次阈值时应分多批推送"
        # 每批大小 ≤ SCAN_BATCH_SIZE
        for batch in batches:
            assert len(batch) <= SCAN_BATCH_SIZE

    def test_empty_dir_sends_done(self, tmp_path):
        """空目录扫描也必须收到 done 哨兵，total=0。"""
        _, done_info = self._run_scan(tmp_path)
        assert done_info.get("total") == 0
        assert "error" not in done_info

    def test_scan_does_not_block_main_thread(self, tmp_path):
        """扫描期间主线程必须保持响应（消费线程独立运行）。"""
        for i in range(20):
            (tmp_path / f"t_{i}.tmp").write_text("x")

        q: multiprocessing.Queue = multiprocessing.Queue()
        finished = threading.Event()

        consumer = QueueConsumer(
            q,
            on_nodes=lambda _: None,
            on_done=lambda t, s: finished.set(),
            on_error=lambda _: finished.set(),
        )
        worker = ScanWorker(q, root=tmp_path, skip_hidden=False)

        consumer.start()
        worker.start()

        # 主线程在 worker 运行期间做其他操作，不应被阻塞
        tick = 0
        deadline = time.time() + 10
        while not finished.is_set() and time.time() < deadline:
            tick += 1
            time.sleep(0.01)

        assert finished.is_set(), "扫描超时未完成"
        assert tick > 0, "主线程未能保持运行（被阻塞）"
