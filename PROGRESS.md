# 进度记录

## 2026-07-03

- 初始提交：PaddleOCR on Ascend NPU 910B 测试环境
- Dockerfile 和 docker-compose.yml 基础配置

## 2026-07-06

- 调整 Dockerfile 和 compose 参数
- test_ppdoclayout.py 显式指定 `vl_rec_api_model_name="PaddleOCR-VL-0.9B"`
- 新增 `scripts/batch_inference_pdfs.py`：批量读取 `input/pdfs/` 下 PDF 文件，调用 PP-DocLayoutV2 pipeline 处理，输出 JSON 和 Markdown 至 `output/`
