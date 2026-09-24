"""vLLM OpenAI 兼容 API 客户端：TASKS prompt 表 + 单图识别 + 就绪探测。"""

import base64
import json
import os
import time
import urllib.request

# 任务类型 → prompt 前缀（PaddleOCR-VL 约定）
TASKS = {
    "ocr": "OCR:",
    "table": "Table Recognition:",
    "formula": "Formula Recognition:",
    "chart": "Chart Recognition:",
}


def _to_image_url(image: str) -> str:
    """本地图片路径转 base64 data URL；URL 原样返回。"""
    if os.path.exists(image):
        ext = os.path.splitext(image)[1].lstrip(".").lower() or "png"
        mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
        with open(image, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    return image


class VLMOcrClient:
    """复用单个 OpenAI client 的轻量识别客户端。"""

    def __init__(self, base_url: str, model_name: str, timeout: float = 3600):
        from openai import OpenAI  # 懒加载：--help 等场景无需安装 openai

        self.model_name = model_name
        self._client = OpenAI(api_key="EMPTY", base_url=base_url, timeout=timeout)

    def recognize(self, image: str, task: str = "ocr") -> str:
        """对单张图片（本地路径或 URL）执行识别，返回模型输出文本。"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": _to_image_url(image)}},
                    {"type": "text", "text": TASKS[task]},
                ],
            }
        ]
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
        )
        return response.choices[0].message.content


def check_vllm(base_url: str, timeout: float = 5.0):
    """探测 vLLM 服务是否就绪，返回 (是否就绪, 已加载模型列表或错误信息)。"""
    url = base_url.rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = ", ".join(m.get("id", "?") for m in data.get("data", []))
            return True, models
    except Exception as e:  # 探测失败一律视为未就绪
        return False, str(e)


def wait_vllm(base_url: str, timeout: float = 600.0, interval: float = 5.0) -> bool:
    """阻塞等待 vLLM 就绪（NPU 上模型加载可能耗时数分钟）。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ok, _ = check_vllm(base_url)
        if ok:
            return True
        time.sleep(interval)
    return False
