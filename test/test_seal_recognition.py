import os
import sys
from paddleocr import SealRecognition

output_dir = os.environ.get("OUTPUT_DIR", "/app/paddle/output")
os.makedirs(output_dir, exist_ok=True)

seal_image = os.environ.get(
    "SEAL_IMAGE",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/seal_text_det.png"
)

print(f"输出目录: {output_dir}")
print(f"印章图片: {seal_image}")
print("-" * 50)

pipeline = SealRecognition(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    device="npu"
)

print("开始推理...")
output = pipeline.predict(seal_image)

for i, res in enumerate(output):
    res.print()
    res.save_to_img(output_dir)
    res.save_to_json(output_dir)
    print(f"[OK] 印章识别结果已保存至 {output_dir}")

print("推理完成")
