# PaddleOCR on Ascend NPU

在华为昇腾（Ascend NPU 910B）上运行 PaddleOCR-VL 和 PP-DocLayoutV2 的 Docker 测试环境。

## 环境要求

- 昇腾 NPU 910B 硬件
- CANN 8.0.0
- Docker + Docker Compose

## 快速开始

### 1. 构建镜像

```bash
docker build -t paddle-npu-ocr:latest .
```

### 2. 启动服务

```bash
# 启动全部服务
docker compose up -d

# 仅启动 vLLM 推理服务
docker compose up -d vllm-ascend
```

### 3. 运行测试

```bash
# 进入容器
docker exec -it paddle-npu-dev bash

# OCR 测试（vLLM API）
python /app/paddle/test/test_paddleocr.py

# 文档版面分析测试
python /app/paddle/test/test_ppdoclayout.py

# 压测
python /app/paddle/test/benchmark_paddleocr.py
```

## 测试说明

| 脚本 | 用途 |
|---|---|
| `test_paddleocr.py` | 通过 OpenAI 兼容 API 调用 PaddleOCR-VL 进行 OCR 识别 |
| `test_ppdoclayout.py` | 使用 PP-DocLayoutV2 进行文档版面分析，输出 JSON + Markdown |
| `benchmark_paddleocr.py` | 10 并发 OCR 压测，统计 QPS 与延迟分布 |

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PPDOCLAYOUT_MODEL_PATH` | `/app/models/PaddlePaddle/PP-DocLayoutV2` | 版面分析模型路径 |
| `VLLM_SERVER_URL` | `http://localhost:8000/v1` | vLLM 服务地址 |
| `DEMO_IMAGE_URL` | paddleocr_vl_demo.png | 测试图片 |
| `OUTPUT_DIR` | `/app/paddle/output` | 推理结果输出目录 |

## 目录结构

```
.
├── Dockerfile              # PaddleOCR + CustomNPU 镜像
├── docker-compose.yml      # paddle-npu + vllm-ascend 双服务编排
├── scripts/
│   └── start_vllm.sh       # vLLM 启动脚本（Ascend 后端）
└── test/
    ├── test_paddleocr.py       # OCR API 测试
    ├── test_ppdoclayout.py     # 版面分析测试
    └── benchmark_paddleocr.py  # 并发压测
```
