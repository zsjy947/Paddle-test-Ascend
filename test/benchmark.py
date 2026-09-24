"""压测：vLLM OCR 并发 QPS / 延迟统计（原 benchmark_paddleocr.py）。容器内运行。

复用 ppdoc.VLMOcrClient（单 client 多线程复用，不再每请求新建连接）。
"""

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ppdoc.client import VLMOcrClient
from ppdoc.config import Settings

CONCURRENCY = int(os.environ.get("BENCH_CONCURRENCY", "10"))
TOTAL_REQUESTS = int(os.environ.get("BENCH_TOTAL_REQUESTS", "50"))
IMAGE_URL = os.environ.get(
    "DEMO_IMAGE_URL",
    "https://ofasys-multimodal-wlcb-3-toshanghai.oss-accelerate.aliyuncs.com/wpf272043/keepme/image/receipt.png",
)


def send_request(client: VLMOcrClient, task_type: str) -> dict:
    start = time.perf_counter()
    try:
        text = client.recognize(IMAGE_URL, task=task_type)
        return {"ok": True, "latency": time.perf_counter() - start, "length": len(text)}
    except Exception as e:
        return {"ok": False, "latency": time.perf_counter() - start, "error": str(e)}


def main():
    settings = Settings()
    client = VLMOcrClient(settings.vllm_server_url, settings.vllm_model_name)

    print(f"并发数: {CONCURRENCY}  总请求数: {TOTAL_REQUESTS}")
    print(f"vLLM 地址: {settings.vllm_server_url}")
    print(f"模型: {settings.vllm_model_name}")
    print("-" * 60)

    latencies = []
    success = 0
    fail = 0
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(send_request, client, "ocr") for _ in range(TOTAL_REQUESTS)]
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            latencies.append(result["latency"])
            if result["ok"]:
                success += 1
                print(f"[{i:3d}/{TOTAL_REQUESTS}] OK  {result['latency']:.2f}s  output_len={result['length']}")
            else:
                fail += 1
                print(f"[{i:3d}/{TOTAL_REQUESTS}] FAIL  {result['latency']:.2f}s  {result['error']}")

    total_time = time.perf_counter() - start_time

    print("\n" + "=" * 60)
    print("压测结果")
    print("=" * 60)
    print(f"总请求数: {TOTAL_REQUESTS}")
    print(f"成功: {success}  失败: {fail}")
    print(f"总耗时: {total_time:.2f}s")
    print(f"QPS: {TOTAL_REQUESTS / total_time:.2f}")

    if latencies:
        sorted_lat = sorted(latencies)
        print("\n延迟统计 (秒):")
        print(f"  平均:   {statistics.mean(latencies):.2f}")
        print(f"  中位数: {statistics.median(latencies):.2f}")
        print(f"  最小:   {min(latencies):.2f}")
        print(f"  最大:   {max(latencies):.2f}")
        p50 = sorted_lat[min(int(len(sorted_lat) * 0.50), len(sorted_lat) - 1)]
        p95 = sorted_lat[min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)]
        p99 = sorted_lat[min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)]
        print(f"  P50:    {p50:.2f}")
        print(f"  P95:    {p95:.2f}")
        print(f"  P99:    {p99:.2f}")


if __name__ == "__main__":
    main()
