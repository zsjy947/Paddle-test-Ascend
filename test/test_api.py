"""smoke 测试：vLLM OpenAI 兼容 API 连通性（原 test_paddleocr.py）。容器内运行。"""

import os

from ppdoc.client import VLMOcrClient
from ppdoc.config import Settings

image = os.environ.get(
    "DEMO_IMAGE_URL",
    "https://ofasys-multimodal-wlcb-3-toshanghai.oss-accelerate.aliyuncs.com/wpf272043/keepme/image/receipt.png",
)

settings = Settings()
print(f"vLLM 地址: {settings.vllm_server_url}")
print(f"模型: {settings.vllm_model_name}")
print(f"测试图片: {image}")
print("-" * 50)

client = VLMOcrClient(settings.vllm_server_url, settings.vllm_model_name)
print(f"Generated text: {client.recognize(image, task='ocr')}")
