import threading
import time
import queue
from core.logger import logger

class CloudBatcher:
    """
    云端 AI 异步批处理处理器。
    负责将离散的单路径分析请求合并为批量请求，提升 API 利用率。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CloudBatcher, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, max_batch_size=8, max_wait_time=0.6):
        if hasattr(self, "_initialized") and self._initialized: return
        
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        
        self._pending_queue = []
        self._results = {}       # path -> result_dict
        self._events = {}        # path -> threading.Event
        self._callbacks = {}     # path -> [callback_funcs]
        
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="BatchProcessor-Worker")
        self._worker_thread.start()
        
        self._batch_handler = None   # 实际执行批量 AI 分析的函数
        self._post_batch_cb = None    # 批处理完成后通知 UI 的全局回调
        self._initialized = True
        logger.info(f"AI BatchProcessor initialized: batch_size={max_batch_size}, wait={max_wait_time}s")

    def set_batch_handler(self, handler_func):
        """设置底层的 AI 批量分析执行器"""
        self._batch_handler = handler_func

    def set_post_batch_callback(self, cb):
        """设置批处理完成后的全局通知回调（用于 UI 刷新）"""
        self._post_batch_cb = cb

    def submit(self, path: str):
        """同步提交并阻塞等待结果"""
        event = threading.Event()
        with self._lock:
            if path in self._events:
                event = self._events[path]
            else:
                self._events[path] = event
                self._pending_queue.append(path)
                
        # 阻塞等待事件触发
        completed = event.wait(timeout=15.0)
        
        result = None
        with self._lock:
            result = self._results.get(path)
            # 清理（仅同步调用需要立即清理结果字典，防止内存泄漏）
            if path in self._results:
                del self._results[path]
            if path in self._events:
                del self._events[path]
                
        if not completed or result is None:
            return {"risk_level": "UNKNOWN", "ai_advice": "分析超时。"}
        return result

    def submit_async(self, path: str, callback=None):
        """异步提交路径分析，不阻塞调用者"""
        with self._lock:
            if path not in self._pending_queue and path not in self._events:
                self._pending_queue.append(path)
                self._events[path] = threading.Event() 
            
            if callback:
                if path not in self._callbacks: self._callbacks[path] = []
                self._callbacks[path].append(callback)
                
        return {"risk_level": "ANALYZING", "ai_advice": "智能引擎研判中..."}

    def _worker_loop(self):
        """后台聚合逻辑主循环"""
        while True:
            batch = []
            with self._lock:
                if not self._pending_queue:
                    time.sleep(0.1)
                    continue
                
                # 开始聚合等待
                start_collect_time = time.time()
                while len(self._pending_queue) < self.max_batch_size:
                    elapsed = time.time() - start_collect_time
                    if elapsed >= self.max_wait_time:
                        break
                    time.sleep(0.05)
                
                # 取出当前批次
                batch = self._pending_queue[:self.max_batch_size]
                self._pending_queue = self._pending_queue[self.max_batch_size:]
                
            if batch:
                try:
                    self._process_batch(batch)
                except Exception as e:
                    logger.error(f"Error processing AI batch: {e}")
                    self._mark_batch_result(batch, None)

    def _process_batch(self, paths):
        """执行批量分析"""
        if not self._batch_handler:
            self._mark_batch_result(paths, None)
            return

        try:
            results_list = self._batch_handler(paths)
            # 归一化路径匹配：Windows 大小写不敏感 + 去除末尾分隔符
            results_map = {}
            for res in results_list:
                if "path" in res:
                    norm_path = res["path"].rstrip("\\/").lower()
                    results_map[norm_path] = res
            self._mark_batch_result(paths, results_map)
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            self._mark_batch_result(paths, None)

    def _mark_batch_result(self, paths, results_map):
        """统一分发结果并通知"""
        with self._lock:
            for path in paths:
                # 归一化路径查找，确保 Windows 大小写不敏感匹配
                norm_path = path.rstrip("\\/").lower()
                res = results_map.get(norm_path) if results_map else None
                if not res:
                    res = {"risk_level": "UNKNOWN", "ai_advice": "分析失败，可能由于网络抖动。"}
                
                self._results[path] = res
                
                # 触发异步回调
                if path in self._callbacks:
                    for cb in self._callbacks[path]:
                        try:
                            cb(res)
                        except Exception as e:
                            logger.error(f"Callback error for {path}: {e}")
                    del self._callbacks[path]
                
                # 唤醒同步等待线程
                if path in self._events:
                    self._events[path].set()
            
            # 触发全局批次完成回调
            if self._post_batch_cb and results_map:
                try:
                    self._post_batch_cb(results_map)
                except Exception as e:
                    import traceback
                    logger.error(f"Global post-batch callback error: {e}\n{traceback.format_exc()}")

# 全局单例
batch_processor = CloudBatcher()
