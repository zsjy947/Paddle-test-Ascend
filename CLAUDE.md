# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

在华为昇腾（Ascend NPU 910B）上运行 PaddleOCR-VL 和 PP-DocLayoutV2 的 Docker 测试环境。

## 架构

- **PaddleOCR-VL**: 通过 vLLM Ascend 后端以 OpenAI 兼容 API 方式提供服务（端口 8000），处理 OCR、表格、公式、图表识别
- **PP-DocLayoutV2**: 通过 PaddleOCR pipeline 在 NPU 上运行文档版面分析，将 vLLM 作为视觉识别后端
- 两套服务通过 `docker-compose.yml` 编排，共享 NPU 设备和模型目录

## 启动命令

```bash
# 构建镜像
docker build -t paddle-npu-ocr:latest .

# 启动全部服务（PaddleOCR 环境 + vLLM Ascend）
docker compose up -d

# 仅 vLLM 服务
docker compose up -d vllm-ascend
```

## 测试

测试脚本在容器内运行，依赖 NPU 硬件和 vLLM 服务。

```bash
# 进入容器
docker exec -it paddle-npu-dev bash

# OCR 测试（调用 vLLM OpenAI API）
python /app/paddle/test/test_paddleocr.py

# 文档版面分析测试（PP-DocLayoutV2 pipeline）
python /app/paddle/test/test_ppdoclayout.py
```

环境变量：
- `PPDOCLAYOUT_MODEL_PATH`: PP-DocLayoutV2 模型路径，默认 `/app/models/PaddlePaddle/PP-DocLayoutV2`
- `VLLM_SERVER_URL`: vLLM 服务地址，默认 `http://localhost:8000/v1`
- `DEMO_IMAGE_URL`: 测试图片 URL
- `OUTPUT_DIR`: 推理结果输出目录，默认 `/app/paddle/output`
