import os
import sys
from paddleocr import PPStructureV3

# 版面模型路径
doc_layout_model_dir = os.environ.get(
    "PPDOCLAYOUT_MODEL_PATH",
    "/app/models/PaddlePaddle/PP-DocLayoutV2"
)

# 印章检测模型路径
seal_det_model_dir = os.environ.get(
    "SEAL_DET_MODEL_PATH",
    "/app/models/PaddlePaddle/PP-OCRv4_server_seal_det"
)

# 印章识别模型路径
seal_rec_model_dir = os.environ.get(
    "SEAL_REC_MODEL_PATH",
    "/app/models/PaddlePaddle/PP-OCRv4_server_rec"
)

# 校验模型路径
for name, path in [
    ("版面模型", doc_layout_model_dir),
    ("印章检测模型", seal_det_model_dir),
    ("印章识别模型", seal_rec_model_dir),
]:
    if not os.path.isdir(path):
        print(f"[ERROR] {name} 目录不存在: {path}")
        sys.exit(1)

layout_config = {
    "model_dir": doc_layout_model_dir,
    "label_list": ["text", "title", "figure", "table", "seal", "footer", "header"]
}

seal_config = {
    "det_model_dir": seal_det_model_dir,
    "rec_model_dir": seal_rec_model_dir,
}

output_dir = os.environ.get("OUTPUT_DIR", "/app/paddle/output")
os.makedirs(output_dir, exist_ok=True)

pdf_file = os.environ.get(
    "PDF_FILE",
    "/app/paddle/input/pdfs/摩智视界（湖州）科技有限公司_技术_应答文件格式（技术+报价）.pdf"
)

if not os.path.isfile(pdf_file):
    print(f"[ERROR] PDF 文件不存在: {pdf_file}")
    sys.exit(1)

basename = os.path.splitext(os.path.basename(pdf_file))[0]
pdf_output_dir = os.path.join(output_dir, basename)
os.makedirs(pdf_output_dir, exist_ok=True)

print(f"版面模型路径: {doc_layout_model_dir}")
print(f"印章检测模型: {seal_det_model_dir}")
print(f"印章识别模型: {seal_rec_model_dir}")
print(f"输出目录: {pdf_output_dir}")
print(f"PDF 文件: {pdf_file}")
print("-" * 50)

pipeline = PPStructureV3(
    use_doc_layout=True,
    use_seal_recognition=True,

    layout_config=layout_config,
    seal_config=seal_config,

    use_table_recognition=False,
    use_formula_recognition=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,

    device="npu"
)

print("开始推理...")
output = pipeline.predict(pdf_file)
pages_res = list(output)

# 合并跨页表格 + 重建多级标题 + 合并多页结果
output = pipeline.restructure_pages(
    pages_res,
    merge_tables=True,
    relevel_titles=True,
    concatenate_pages=True
)

for i, res in enumerate(output):
    suffix = f"_{i}" if len(output) > 1 else ""
    json_path = os.path.join(pdf_output_dir, f"{basename}{suffix}.json")
    md_path = os.path.join(pdf_output_dir, f"{basename}{suffix}.md")
    res.save_to_json(save_path=json_path)
    res.save_to_markdown(save_path=md_path)
    print(f"  [OK] -> {basename}/{os.path.basename(json_path)}, {basename}/{os.path.basename(md_path)}")

print("推理完成")
