import os
import sys
import glob
from paddleocr import PaddleOCRVL

# 模型路径
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

# 输入 PDF 目录 & 输出目录
input_dir = os.environ.get("INPUT_PDF_DIR", "/app/paddle/input/pdfs")
output_dir = os.environ.get("OUTPUT_DIR", "/app/paddle/output")
os.makedirs(output_dir, exist_ok=True)

if not os.path.isdir(input_dir):
    print(f"[ERROR] 输入目录不存在: {input_dir}")
    sys.exit(1)

pdf_files = sorted(glob.glob(os.path.join(input_dir, "*.pdf")))
if not pdf_files:
    print(f"[INFO] {input_dir} 中没有找到 PDF 文件")
    sys.exit(0)

print(f"模型路径: {doclayout_model_path}")
print(f"vLLM 地址: {vl_rec_server_url}")
print(f"输入目录: {input_dir} ({len(pdf_files)} 个 PDF)")
print(f"输出目录: {output_dir}")
print("-" * 50)

pipeline = PaddleOCRVL(
    vl_rec_backend="vllm-server",
    vl_rec_server_url=vl_rec_server_url,
    vl_rec_api_model_name="PaddleOCR-VL-0.9B",
    layout_detection_model_name="PP-DocLayoutV2",
    layout_detection_model_dir=doclayout_model_path,
    device="npu"
)

for pdf_path in pdf_files:
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n处理: {os.path.basename(pdf_path)}")

    output = pipeline.predict(pdf_path)

    for i, res in enumerate(output):
        suffix = f"_{i}" if len(output) > 1 else ""
        json_path = os.path.join(output_dir, f"{basename}{suffix}.json")
        md_path = os.path.join(output_dir, f"{basename}{suffix}.md")
        res.save_to_json(save_path=json_path)
        res.save_to_markdown(save_path=md_path)
        print(f"  [OK] {os.path.basename(json_path)}, {os.path.basename(md_path)}")

print("\n全部处理完成")
