"""smoke 测试：印章识别独立管线（原 test_seal_recognition.py）。容器内运行。

等价 CLI：python -m ppdoc parse "$SEAL_IMAGE" --engine seal
模型目录（SEAL_DET_MODEL_PATH / SEAL_REC_MODEL_PATH）存在时用本地模型，否则回退库内置默认。
"""

import os

from ppdoc import pipelines
from ppdoc.config import Settings

settings = Settings.load()

seal_image = os.environ.get(
    "SEAL_IMAGE",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/seal_text_det.png",
)
output_dir = os.environ.get("OUTPUT_DIR", settings.output_dir)
os.makedirs(output_dir, exist_ok=True)

print(f"输出目录: {output_dir}")
print(f"印章图片: {seal_image}")
print("-" * 50)

pipeline = pipelines.create_pipeline("seal", settings)

print("开始推理...")
for res in pipeline.predict(seal_image):
    res.print()
    res.save_to_img(output_dir)
    res.save_to_json(output_dir)
    print(f"[OK] 印章识别结果已保存至 {output_dir}")

print("推理完成")
