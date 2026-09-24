"""smoke 测试：PPStructureV3 全本地管线（版面+印章，原 test_ppstructure.py）。容器内运行。

等价 CLI：python -m docparse parse "$PDF_FILE" --engine structure
"""

import os

from docparse import pipelines, postprocess
from docparse.config import Settings

settings = Settings.load()
errors = settings.validate("structure")
if errors:
    for e in errors:
        print(f"[ERROR] {e}")
    raise SystemExit(1)

pdf_file = os.environ.get(
    "PDF_FILE",
    "/app/paddle/input/pdfs/摩智视界（湖州）科技有限公司_技术_应答文件格式（技术+报价）.pdf",
)
if not os.path.isfile(pdf_file):
    print(f"[ERROR] PDF 文件不存在: {pdf_file}")
    raise SystemExit(1)

output_dir = os.environ.get("OUTPUT_DIR", settings.output_dir)
os.makedirs(output_dir, exist_ok=True)

print(f"版面模型路径: {settings.doclayout_model_dir}")
print(f"印章检测模型: {settings.seal_det_model_dir}")
print(f"印章识别模型: {settings.seal_rec_model_dir}")
print(f"输出目录: {output_dir}")
print(f"PDF 文件: {pdf_file}")
print("-" * 50)

pipeline = pipelines.create_pipeline("structure", settings)
saved = postprocess.parse_and_save(pipeline, pdf_file, output_dir, engine="structure")
for path in saved:
    print(f"[OK] 已保存: {path}")
print("推理完成")
