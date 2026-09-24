# PROJECT KNOWLEDGE BASE

**Updated:** 2026-09-24
**Branch:** main

## OVERVIEW

华为昇腾 NPU 910B 上的 PaddleOCR-VL + PP-DocLayoutV2 文档解析环境。核心能力封装在 `ppdoc` Python 库（三条可切换解析管线），通过 `python -m ppdoc` CLI 使用；vLLM Ascend 后端提供 PaddleOCR-VL 推理服务。

## STRUCTURE

```
paddle/
├── Dockerfile              # paddle-npu-ocr 镜像（PaddlePaddle + CustomNPU）
├── docker-compose.yml      # ppdoc-npu + vllm-ascend 双服务编排（含 healthcheck）
├── config.yaml             # ★ 主配置：模型名/路径、引擎构造参数（版本升级入口）
├── requirements.txt        # Python 依赖（paddleocr/openai 等）
├── ppdoc/                  # ★ 核心库
│   ├── config.py           # config.yaml + 环境变量加载（Settings，env > file > 默认）
│   ├── pipelines.py        # 三引擎管线工厂（build_pipeline_kwargs 参数透传）
│   ├── client.py           # vLLM OpenAI 兼容客户端 + TASKS + 就绪探测
│   ├── postprocess.py      # restructure_pages 封装 + 统一保存（json+md）
│   ├── batch.py            # 批量：异常隔离/重试/进度/batch_report.json
│   └── cli.py              # python -m ppdoc parse|ocr|check
├── scripts/
│   └── start_vllm.sh       # vLLM 启动脚本（Ascend 后端，参数环境变量化）
├── test/
│   ├── test_api.py         # vLLM API 连通性 smoke
│   ├── test_vl_server.py   # 版面+vLLM 混合管线 smoke
│   ├── test_structure.py   # PPStructureV3 全本地（版面+印章）smoke
│   ├── test_seal.py        # 印章识别 smoke
│   └── benchmark.py        # 并发压测
├── input/                  # 测试输入（PDF、图片，gitignore）
└── output/                 # 推理结果输出（gitignore）
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Docker 构建 | `Dockerfile`, `docker-compose.yml` | NPU 设备映射、模型挂载 |
| vLLM 启动 | `scripts/start_vllm.sh` | VLLM_MODEL_PATH/VLLM_PORT/VLLM_MODEL_NAME 等可覆盖 |
| 配置/模型版本调整 | `config.yaml` + `ppdoc/config.py` | 优先级：环境变量 > config.yaml > 默认 |
| 管线构造 | `ppdoc/pipelines.py` | build_pipeline_kwargs / create_pipeline；引擎段未知参数透传 |
| 批量推理 | `ppdoc/batch.py` + CLI `parse` | PDF → JSON + Markdown + batch_report.json |
| OCR API 调用 | `ppdoc/client.py` | VLMOcrClient / check_vllm / wait_vllm |

## CONVENTIONS

- 测试脚本与 CLI 在**容器内运行**，依赖 NPU 硬件（`ppdoc` 懒加载重依赖，宿主机可 `--help`）
- vLLM 服务端口：8000（OpenAI 兼容 API）
- 模型名/路径、引擎参数调整**优先改 `config.yaml`**（优先级：环境变量 > config.yaml > 内置默认值）
- 环境变量只允许在 `ppdoc/config.py` 读取，其他模块从 `Settings` 取值
- pipeline 构造参数集中在 `ppdoc/pipelines.py`，引擎段未知参数透传给 paddleocr 构造器（新版本参数免改代码）

## ANTI-PATTERNS (THIS PROJECT)

- **不要**在宿主机直接运行推理/测试（需要 NPU 设备）
- **不要**修改 `docker-compose.yml` 中的 NPU 设备映射（`/dev/davinci*`）与卡号分配
- **不要**删除 `input/seal_test/` 测试数据
- **不要**把 numpy/opencv 降级版本并入 `requirements.txt`（需事后覆盖安装，见 Dockerfile 注释）

## COMMANDS

```bash
# 构建镜像
docker build -t paddle-npu-ocr:v1 .

# 启动全部服务（vLLM 健康后自动启动 ppdoc-npu）
docker compose up -d

# 只启动开发容器（不等 vLLM）
docker compose up -d --no-deps ppdoc-npu

# 进入容器
docker exec -it ppdoc-dev bash

# CLI（容器内）
python -m ppdoc check
python -m ppdoc parse                          # 批量解析 INPUT_PDF_DIR
python -m ppdoc parse input/pdfs/xxx.pdf --engine structure
python -m ppdoc ocr demo.png --task table

# smoke 测试
python /app/paddle/test/test_api.py
python /app/paddle/test/test_vl_server.py
```

## ENVIRONMENT VARIABLES

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PPDOC_CONFIG` | 仓库根 config.yaml | 配置文件路径 |
| `PPDOCLAYOUT_MODEL_PATH` | `/app/models/PaddlePaddle/PP-DocLayoutV2` | 版面分析模型路径 |
| `PPDOCLAYOUT_MODEL_NAME` | `PP-DocLayoutV2` | 版面模型名（vl-server 引擎） |
| `SEAL_DET_MODEL_PATH` | `/app/models/PaddlePaddle/PP-OCRv4_server_seal_det` | 印章检测模型路径 |
| `SEAL_REC_MODEL_PATH` | `/app/models/PaddlePaddle/PP-OCRv4_server_rec` | 印章识别模型路径 |
| `VLLM_SERVER_URL` | `http://localhost:8000/v1` | vLLM 服务地址 |
| `VLLM_MODEL_NAME` | `PaddleOCR-VL-0.9B` | vLLM served 模型名 |
| `VLLM_MODEL_PATH` | `/app/models/PaddlePaddle/PaddleOCR-VL` | vLLM 模型路径（start_vllm.sh） |
| `VLLM_PORT` | `8000` | vLLM 端口 |
| `VLLM_MAX_BATCHED_TOKENS` | `16384` | vLLM 批处理 token 上限（start_vllm.sh） |
| `OUTPUT_DIR` | `/app/paddle/output` | 推理结果输出目录 |
| `INPUT_PDF_DIR` | `/app/paddle/input/pdfs` | 批量推理输入目录 |
| `PPDOC_DEVICE` | `npu` | 推理设备 |

## NOTES

- vLLM 使用 Ascend 后端，需要 CANN 8.0.0 环境
- vl-server 引擎：PP-DocLayoutV2 本地推理 + vLLM 远端识别；structure/seal 引擎全本地，不依赖 vLLM
- 输出结构：`output/<文件名>/<文件名>[_i].json/.md`；批量模式另写 `output/batch_report.json`
- 旧 `scripts/batch_inference_pdfs.py` 已由 `python -m ppdoc parse` 取代（2026-09-24 重构）

## 进度记录

详见 [PROGRESS.md](PROGRESS.md)。
