# PROJECT KNOWLEDGE BASE

**Generated:** 2026-07-09
**Commit:** 6d8c979
**Branch:** main

## OVERVIEW

华为昇腾 NPU 910B 上的 PaddleOCR-VL + PP-DocLayoutV2 Docker 测试环境。通过 vLLM Ascend 后端提供 OCR 服务，PP-DocLayoutV2 pipeline 处理文档版面分析。

## STRUCTURE

```
paddle/
├── Dockerfile              # PaddleOCR + CustomNPU 镜像
├── docker-compose.yml      # paddle-npu + vllm-ascend 双服务编排
├── scripts/
│   ├── start_vllm.sh       # vLLM 启动脚本（Ascend 后端）
│   └── batch_inference_pdfs.py  # 批量 PDF 推理
├── test/
│   ├── test_paddleocr.py       # OCR API 测试
│   ├── test_ppdoclayout.py     # 版面分析测试
│   ├── test_ppstructure.py     # PP-Structure 测试
│   ├── test_seal_recognition.py # 印章识别测试
│   └── benchmark_paddleocr.py  # 并发压测
├── input/                  # 测试输入（PDF、图片）
└── output/                 # 推理结果输出
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Docker 构建 | `Dockerfile`, `docker-compose.yml` | NPU 设备映射、模型挂载 |
| vLLM 启动 | `scripts/start_vllm.sh` | Ascend 后端配置 |
| OCR 测试 | `test/test_paddleocr.py` | 调用 OpenAI 兼容 API |
| 版面分析 | `test/test_ppdoclayout.py` | PP-DocLayoutV2 pipeline |
| 批量推理 | `scripts/batch_inference_pdfs.py` | PDF → JSON + Markdown |

## CONVENTIONS

- 测试脚本在**容器内运行**，依赖 NPU 硬件
- vLLM 服务端口：8000（OpenAI 兼容 API）
- 模型路径通过环境变量配置，默认 `/app/models/PaddlePaddle/`

## ANTI-PATTERNS (THIS PROJECT)

- **不要**在宿主机直接运行测试脚本（需要 NPU 设备）
- **不要**修改 `docker-compose.yml` 中的 NPU 设备映射（`/dev/davinci*`）
- **不要**删除 `input/seal_test/` 测试数据

## COMMANDS

```bash
# 构建镜像
docker build -t paddle-npu-ocr:latest .

# 启动全部服务
docker compose up -d

# 进入容器
docker exec -it paddle-npu-dev bash

# 运行测试
python /app/paddle/test/test_paddleocr.py
python /app/paddle/test/test_ppdoclayout.py
python /app/paddle/scripts/batch_inference_pdfs.py
```

## ENVIRONMENT VARIABLES

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PPDOCLAYOUT_MODEL_PATH` | `/app/models/PaddlePaddle/PP-DocLayoutV2` | 版面分析模型路径 |
| `VLLM_SERVER_URL` | `http://localhost:8000/v1` | vLLM 服务地址 |
| `DEMO_IMAGE_URL` | - | 测试图片 URL |
| `OUTPUT_DIR` | `/app/paddle/output` | 推理结果输出目录 |
| `INPUT_PDF_DIR` | `/app/paddle/input/pdfs` | 批量推理输入目录 |

## NOTES

- vLLM 使用 Ascend 后端，需要 CANN 8.0.0 环境
- PP-DocLayoutV2 将 vLLM 作为视觉识别后端
- 测试结果输出到 `output/` 目录（JSON + Markdown 格式）

## 进度记录

详见 [PROGRESS.md](PROGRESS.md)。