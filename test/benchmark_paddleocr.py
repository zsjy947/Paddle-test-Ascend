import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

# ====== 配置 ======
CONCURRENCY = 10
TOTAL_REQUESTS = 50
BASE_URL = "http://127.0.0.1:8000/v1"
MODEL = "PaddleOCR-VL-0.9B"
IMAGE_URL = "https://ofasys-multimodal-wlcb-3-toshanghai.oss-accelerate.aliyuncs.com/wpf272043/keepme/image/receipt.png"

TASKS = {
    "ocr": "OCR:",
    "table": "Table Recognition:",
    "formula": "Formula Recognition:",
    "chart": "Chart Recognition:",
}

# ====== 单次请求 ======
def send_request(task_type: str) -> dict:
    client = OpenAI(api_key="EMPTY", base_url=BASE_URL, timeout=3600)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": IMAGE_URL}},
                {"type": "text", "text": TASKS[task_type]},
            ],
        }
    ]

    start = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.0,
        )
        elapsed = time.perf_counter() - start
        text = resp.choices[0].message.content
        return {"ok": True, "latency": elapsed, "length": len(text)}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"ok": False, "latency": elapsed, "error": str(e)}


# ====== 主流程 ======
def main():
    print(f"并发数: {CONCURRENCY}  总请求数: {TOTAL_REQUESTS}")
    print(f"模型: {MODEL}")
    print("-" * 60)

    latencies = []
    success = 0
    fail = 0
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = []
        for i in range(TOTAL_REQUESTS):
            task_type = "ocr"  # 统一用 OCR 任务
            futures.append(pool.submit(send_request, task_type))

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

    # ====== 统计 ======
    print("\n" + "=" * 60)
    print("压测结果")
    print("=" * 60)
    print(f"总请求数: {TOTAL_REQUESTS}")
    print(f"成功: {success}  失败: {fail}")
    print(f"总耗时: {total_time:.2f}s")
    print(f"QPS: {TOTAL_REQUESTS / total_time:.2f}")

    if latencies:
        sorted_lat = sorted(latencies)
        print(f"\n延迟统计 (秒):")
        print(f"  平均:   {statistics.mean(latencies):.2f}")
        print(f"  中位数: {statistics.median(latencies):.2f}")
        print(f"  最小:   {min(latencies):.2f}")
        print(f"  最大:   {max(latencies):.2f}")
        p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
        print(f"  P50:    {p50:.2f}")
        print(f"  P95:    {p95:.2f}")
        print(f"  P99:    {p99:.2f}")


if __name__ == "__main__":
    main()
