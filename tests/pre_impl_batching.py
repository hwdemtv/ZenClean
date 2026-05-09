import threading
import time
import random
import uuid
from collections import deque

class MockBatchProcessor:
    def __init__(self, max_batch_size=10, max_wait_time=0.5):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.queue = []
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.results = {}  # Map: path -> result_dict
        self.api_call_count = 0
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def submit(self, path):
        """模拟调用方提交路径并阻塞等待结果"""
        with self.lock:
            # 记录请求进入队列
            self.queue.append(path)
            self.condition.notify_all()
            
        print(f"  [THREAD] Submitted: {path}, waiting...")
        
        # 等待结果出现
        start_wait = time.time()
        while True:
            with self.lock:
                if path in self.results:
                    res = self.results.pop(path)
                    print(f"  [THREAD] Got result for {path} after {time.time()-start_wait:.2f}s: {res['risk_level']}")
                    return res
            time.sleep(0.05)
            if time.time() - start_wait > 10: # 10s 超时保护
                return {"risk_level": "TIMEOUT", "ai_advice": "FAILED"}

    def _worker(self):
        """后台批处理器逻辑"""
        while True:
            batch_to_process = []
            with self.lock:
                # 等待队列有货
                while not self.queue:
                    self.condition.wait(timeout=1.0)
                
                # 触发逻辑：满员或超时
                # 这里简单模拟：如果队列有内容，先等一小会儿看看有没有后来者
                time.sleep(0.2) 
                
                # 取出批次
                batch_to_process = self.queue[:self.max_batch_size]
                self.queue = self.queue[self.max_batch_size:]
                
            if batch_to_process:
                self._mock_ai_request(batch_to_process)

    def _mock_ai_request(self, paths):
        """模拟云端 AI 接口调用"""
        self.api_call_count += 1
        print(f"\n>>> [AI_API] Processing batch of {len(paths)} paths: {paths}")
        
        # 模拟网络延迟
        time.sleep(1.0 + random.random() * 0.5)
        
        # 构造批量结果
        mock_results = []
        for p in paths:
            mock_results.append({
                "path": p,
                "risk_level": random.choice(["LOW", "MEDIUM", "HIGH"]),
                "ai_advice": f"Advice for {p}"
            })
            
        # 分发结果
        with self.lock:
            for res in mock_results:
                self.results[res["path"]] = res
        print(f">>> [AI_API] Completed batch of {len(paths)}.\n")

def run_test():
    processor = MockBatchProcessor(max_batch_size=10, max_wait_time=0.5)
    
    test_paths = [f"C:\\Users\\Desktop\\Folder_{i}" for i in range(25)]
    threads = []
    
    print(f"--- Starting Concurrent Test with {len(test_paths)} paths ---")
    start_time = time.time()
    
    for path in test_paths:
        t = threading.Thread(target=processor.submit, args=(path,))
        threads.append(t)
        t.start()
        # 稍微错开一点点提交时间，模拟扫描器速度
        time.sleep(0.02)
        
    for t in threads:
        t.join()
        
    total_time = time.time() - start_time
    print(f"\n--- Test Finished ---")
    print(f"Total Paths: {len(test_paths)}")
    print(f"Total API Calls: {processor.api_call_count}")
    print(f"Total Elapsed Time: {total_time:.2f}s")
    print(f"Efficiency: {len(test_paths)/processor.api_call_count:.1f} paths per request")

if __name__ == "__main__":
    run_test()
