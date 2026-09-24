"""smoke 测试：PP-DocLayoutV2 版面 + vLLM 识别混合管线（原 test_ppdoclayout.py）。容器内运行。

等价 CLI：python -m ppdoc parse "$DEMO_IMAGE_URL" --engine vl-server --no-restructure
"""

import os

from ppdoc import pipelines, postprocess
from ppdoc.config import Settings

settings = Settings()
errors = settings.validate("vl-server")
if errors:
    for e in errors:
        print(f"[ERROR] {e}")
    raise SystemExit(1)

image = os.environ.get(
    "DEMO_IMAGE_URL",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png",
)
output_dir = os.environ.get("OUTPUT_DIR", settings.output_dir)
os.makedirs(output_dir, exist_ok=True)

print(f"模型路径: {settings.doclayout_model_dir}")
print(f"vLLM 地址: {settings.vllm_server_url}")
print(f"测试图片: {image}")
print(f"输出目录: {output_dir}")
print("-" * 50)

pipeline = pipelines.create_pipeline("vl-server", settings)
saved = postprocess.parse_and_save(pipeline, image, output_dir, engine="vl-server", restructure=False)
for path in saved:
    print(f"[OK] 已保存: {path}")
print("推理完成")
