import time
import threading
from ai.cloud_engine import query, batch_processor

def test_integration():
    print("--- Starting AI Batching Integration Test ---")
    
    # 记录结果
    results = {}
    
    def my_callback(res):
        path = res.get("path")
        results[path] = res
        print(f"  [CALLBACK] Received result for {path}: {res['risk_level']}")

    # 模拟 10 个未知路径的并发请求
    test_paths = [f"C:\\Mock\\Path_{i}" for i in range(10)]
    
    for p in test_paths:
        print(f"  [QUERY] Querying {p}...")
        # query() 现在是非阻塞的，返回 ANALYZING
        placeholder = query(p, callback=my_callback)
        print(f"  [QUERY] Placeholder returned: {placeholder['risk_level']}")
    
    print("\nWaiting for BatchProcessor to finish (max 5s)...")
    start_wait = time.time()
    while len(results) < 10 and time.time() - start_wait < 5:
        time.sleep(0.5)
        
    print(f"\n--- Test Results ---")
    print(f"Target count: 10, Actual count: {len(results)}")
    
    if len(results) == 10:
        print("SUCCESS: All 10 results received via asynchronous callbacks.")
    else:
        print("FAILED: Missing some results.")

if __name__ == "__main__":
    # 需要 Mock 掉真正的网络请求，或者在一个受控环境下运行
    # 这里的 query 内部会调用 batch_processor -> _batch_analyze -> requests.post
    # 由于我没有真实 Token，测试可能会在网络层报错，但我们可以观察 
    # 是否正确触发了 _batch_analyze (通过日志)。
    
    # 我们先测试逻辑链路
    test_integration()
