# ppdoc：昇腾 NPU 文档解析工具

在华为昇腾（Ascend NPU 910B）上运行 PaddleOCR-VL 和 PP-DocLayoutV2 的文档解析环境。
核心能力封装在 `ppdoc` Python 库中，通过 `python -m ppdoc` 命令行使用。

## 架构

```
┌─────────────────────────────────────────────────────┐
│ ppdoc-npu 容器 (paddle-npu-ocr:v1)                  │
│  ppdoc 库 + CLI                                     │
│   ├─ vl-server 引擎: PP-DocLayoutV2 版面(本地 NPU)  │
│   │   + PaddleOCR-VL 文字识别 ──┐                   │
│   ├─ structure 引擎: PPStructureV3 全本地 + 印章    │
│   └─ seal 引擎: 印章独立识别     │                   │
└─────────────────────────────────┼───────────────────┘
                                  │ OpenAI 兼容 API (:8000)
┌─────────────────────────────────▼───────────────────┐
│ vllm-ascend 容器 (PaddleOCR-VL 0.9B, NPU 卡 3)      │
└─────────────────────────────────────────────────────┘
```

## 环境要求

- 昇腾 NPU 910B 硬件
- CANN 8.0.0
- Docker + Docker Compose
- 宿主机 `~/paddle` 为本仓库、`/data1/models` 为模型目录

## 快速开始

### 1. 构建镜像并启动服务

```bash
docker build -t paddle-npu-ocr:v1 .
docker compose up -d          # vLLM 就绪（healthcheck 通过）后才启动 ppdoc-npu
```

### 2. CLI 使用（容器内）

```bash
docker exec -it ppdoc-dev bash

# 预检：模型目录 + vLLM 就绪状态
python -m ppdoc check

# 单文件解析（--engine 可选 vl-server / structure / seal，默认 vl-server）
python -m ppdoc parse input/pdfs/xxx.pdf
python -m ppdoc parse xxx.pdf --engine structure

# 批量解析整个目录（等价旧版 scripts/batch_inference_pdfs.py）
python -m ppdoc parse                          # 缺省取 INPUT_PDF_DIR
python -m ppdoc parse input/pdfs --retries 3   # 失败重试 3 次
python -m ppdoc parse --wait-vllm 600          # 先等 vLLM 加载完成

# 直连 vLLM API 识别单张图片
python -m ppdoc ocr demo.png --task ocr        # task: ocr/table/formula/chart
```

批量模式：单文件失败不影响整批（自动重试 + 指数退避），结束打印汇总并写
`output/batch_report.json`（成功/失败/单文件耗时/错误信息）。

输出结构（vl-server / structure 引擎）：

```
output/
├── <PDF 文件名>/
│   ├── <PDF 文件名>.json      # 单结果无后缀；跨页合并后通常为一个结果
│   └── <PDF 文件名>.md
└── batch_report.json          # 批量模式汇总报告
```

### 3. smoke 测试与压测（容器内）

| 脚本 | 用途 | 等价 CLI |
|---|---|---|
| `test/test_api.py` | vLLM API 连通性 | `python -m ppdoc ocr` |
| `test/test_vl_server.py` | 版面+vLLM 混合管线 | `parse --engine vl-server` |
| `test/test_structure.py` | 全本地管线（版面+印章） | `parse --engine structure` |
| `test/test_seal.py` | 印章独立识别 | `parse --engine seal` |
| `test/benchmark.py` | 10 并发压测 QPS/延迟 | - |

```bash
python /app/paddle/test/test_api.py
python /app/paddle/test/benchmark.py
```

## 解析引擎

| 引擎 | 组成 | 依赖 vLLM | 适用 |
|---|---|---|---|
| `vl-server` | PP-DocLayoutV2 版面（本地）+ PaddleOCR-VL 识别（vLLM） | 是 | 默认，识别质量优先 |
| `structure` | PPStructureV3（版面含 seal 标签 + 印章 det/rec，全本地） | 否 | 单容器部署、印章场景 |
| `seal` | SealRecognition 独立印章识别 | 否 | 仅印章 |

文档引擎默认开启 `restructure_pages`（跨页表格合并、多级标题重建、多页拼接），
`--no-restructure` 可关闭。

## 配置文件 config.yaml

模型名、模型路径、引擎参数集中在 [config.yaml](config.yaml)，调整**优先改配置文件**，无需改代码。

优先级：**环境变量 > config.yaml > 内置默认值**。配置文件路径可用 `PPDOC_CONFIG` 指定，
缺省依次查找 仓库根/config.yaml、当前目录/config.yaml（`python -m ppdoc check` 会显示实际加载来源）。

模型 / paddleocr 版本升级的常见调整：

| 场景 | 改法 |
|---|---|
| 版面模型升级（如 PP-DocLayoutV2 → V3） | `layout_model_name` + `doclayout_model_dir` |
| PaddleOCR-VL 换新模型 | `vllm_model_name` + `start_vllm.sh` 的 `VLLM_MODEL_NAME`/`VLLM_MODEL_PATH` |
| 印章模型更换 | `seal_det_model_dir` / `seal_rec_model_dir` |
| 开关表格/公式识别等 | `engines.structure.*` 对应开关 |
| paddleocr 升级引入**新**构造参数 | 直接写在 `engines.<引擎>` 段内，原样透传给构造器 |

## 环境变量

全部有默认值，完整清单见 [.env.example](.env.example)。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PPDOC_CONFIG` | 仓库根 config.yaml | 配置文件路径 |
| `PPDOCLAYOUT_MODEL_PATH` | `/app/models/PaddlePaddle/PP-DocLayoutV2` | 版面分析模型路径 |
| `PPDOCLAYOUT_MODEL_NAME` | `PP-DocLayoutV2` | 版面模型名（vl-server 引擎） |
| `SEAL_DET_MODEL_PATH` | `/app/models/PaddlePaddle/PP-OCRv4_server_seal_det` | 印章检测模型路径 |
| `SEAL_REC_MODEL_PATH` | `/app/models/PaddlePaddle/PP-OCRv4_server_rec` | 印章识别模型路径 |
| `VLLM_SERVER_URL` | `http://localhost:8000/v1` | vLLM 服务地址 |
| `VLLM_MODEL_NAME` | `PaddleOCR-VL-0.9B` | vLLM served 模型名 |
| `VLLM_MODEL_PATH` | `/app/models/PaddlePaddle/PaddleOCR-VL` | vLLM 模型路径（start_vllm.sh） |
| `VLLM_PORT` | `8000` | vLLM 端口（start_vllm.sh + 健康检查） |
| `VLLM_MAX_BATCHED_TOKENS` | `16384` | vLLM 批处理 token 上限（start_vllm.sh） |
| `OUTPUT_DIR` | `/app/paddle/output` | 推理结果输出目录 |
| `INPUT_PDF_DIR` | `/app/paddle/input/pdfs` | 批量推理输入目录 |
| `PPDOC_DEVICE` | `npu` | 推理设备 |

## 目录结构

```
.
├── Dockerfile              # paddle-npu-ocr 镜像（PaddlePaddle + CustomNPU）
├── docker-compose.yml      # ppdoc-npu + vllm-ascend 双服务编排
├── config.yaml             # ★ 主配置（模型/引擎参数，版本升级入口）
├── requirements.txt        # Python 依赖
├── ppdoc/                  # ★ 核心库
│   ├── config.py           # config.yaml + 环境变量加载（Settings）
│   ├── pipelines.py        # 三引擎管线工厂（构造参数可透传）
│   ├── client.py           # vLLM OpenAI 兼容客户端 + 就绪探测
│   ├── postprocess.py      # restructure_pages + 统一保存
│   ├── batch.py            # 批量：异常隔离/重试/进度/汇总报告
│   └── cli.py              # python -m ppdoc parse|ocr|check
├── scripts/
│   └── start_vllm.sh       # vLLM 启动脚本（参数环境变量化）
├── test/                   # smoke 测试 + 压测（复用 ppdoc 库）
├── input/                  # 测试输入（gitignore，数据在服务器）
└── output/                 # 推理结果输出（gitignore）
```
