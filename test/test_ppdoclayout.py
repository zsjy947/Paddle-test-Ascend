import os
import sys
from paddleocr import PaddleOCRVL

# 模型路径：可通过环境变量指定，默认从 /app/paddle 挂载目录读取
doclayout_model_path = os.environ.get(
    "PPDOCLAYOUT_MODEL_PATH",
    "/app/models/PaddlePaddle/PP-DocLayoutV2"
)

if not os.path.isdir(doclayout_model_path):
    print(f"[ERROR] 模型目录不存在: {doclayout_model_path}")
    print("请通过 PPDOCLAYOUT_MODEL_PATH 环境变量指定正确的模型路径")
    sys.exit(1)

# vLLM 服务地址
vl_rec_server_url = os.environ.get("VLLM_SERVER_URL", "http://localhost:8000/v1")

# 测试图片 URL
demo_image_url = os.environ.get(
    "DEMO_IMAGE_URL",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png"
)

output_dir = os.environ.get("OUTPUT_DIR", "/app/paddle/output")
os.makedirs(output_dir, exist_ok=True)

print(f"模型路径: {doclayout_model_path}")
print(f"vLLM 地址: {vl_rec_server_url}")
print(f"测试图片: {demo_image_url}")
print(f"输出目录: {output_dir}")
print("-" * 50)

pipeline = PaddleOCRVL(
    vl_rec_backend="vllm-server",
    vl_rec_server_url=vl_rec_server_url,
    layout_detection_model_name="PP-DocLayoutV2",
    layout_detection_model_dir=doclayout_model_path,
    device="npu"
)

print("开始推理...")
output = pipeline.predict(demo_image_url)

for i, res in enumerate(output):
    json_path = os.path.join(output_dir, f"output_{i}.json")
    md_path = os.path.join(output_dir, f"output_{i}.md")
    res.save_to_json(save_path=json_path)
    res.save_to_markdown(save_path=md_path)
    print(f"[OK] output_{i}.json, output_{i}.md 已保存至 {output_dir}")

print("推理完成")
