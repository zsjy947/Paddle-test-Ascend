# docparse：昇腾 NPU 文档解析工具

在华为昇腾（Ascend NPU 910B）上运行 PaddleOCR-VL 和 PP-DocLayoutV2 的文档解析环境。
核心能力封装在 `docparse` Python 库中，通过 `python -m docparse`（容器内）或 `uv run docparse`（宿主机）使用。

## 架构

```
┌─────────────────────────────────────────────────────┐
│ docparse-npu 容器 (docparse-npu:v1)                 │
│  docparse 库 + CLI                                  │
│   ├─ vl-server 引擎: PP-DocLayoutV2 版面(本地 NPU)  │
│   │   + PaddleOCR-VL 文字识别 ──┐                   │
│   ├─ structure 引擎: PPStructureV3 全本地 + 印章    │
│   └─ seal 引擎: 印章独立识别     │                   │
└─────────────────────────────────┼───────────────────┘
                                  │ OpenAI 兼容 API (容器 8000 / 宿主机 8312)
┌─────────────────────────────────▼───────────────────┐
│ vllm-ascend 容器 (PaddleOCR-VL 0.9B, NPU 卡 3)      │
└─────────────────────────────────────────────────────┘
```

## 环境要求

- 昇腾 NPU 910B 硬件
- CANN 8.0.0
- Docker + Docker Compose
- 宿主机 `${HOME}/drawbridge/var/projects/paddle` 为本仓库、`/data1/models` 为模型目录
- 宿主机轻量运行（可选）：[uv](https://docs.astral.sh/uv/)

## 配置文件 config.yaml

模型名、模型路径、引擎参数集中在 [config.yaml](config.yaml)，调整**优先改配置文件**，无需改代码。

优先级：**环境变量 > config.yaml > 内置默认值**。配置文件路径可用 `DOCPARSE_CONFIG` 指定，
缺省依次查找 仓库根/config.yaml、当前目录/config.yaml（`docparse check` 会显示实际加载来源）。

模型 / paddleocr 版本升级的常见调整：

| 场景 | 改法 |
|---|---|
| 版面模型升级（如 PP-DocLayoutV2 → V3） | `layout_model_name` + `doclayout_model_dir` |
| PaddleOCR-VL 换新模型 | `vllm_model_name` + `start_vllm.sh` 的 `VLLM_MODEL_NAME`/`VLLM_MODEL_PATH` |
| 印章模型更换 | `seal_det_model_dir` / `seal_rec_model_dir` |
| 开关表格/公式识别等 | `engines.structure.*` 对应开关 |
| paddleocr 升级引入**新**构造参数 | 直接写在 `engines.<引擎>` 段内，原样透传给构造器 |

## 解析引擎

| 引擎 | 组成 | 依赖 vLLM | 适用 |
|---|---|---|---|
| `vl-server` | PP-DocLayoutV2 版面（本地）+ PaddleOCR-VL 识别（vLLM） | 是 | 默认，识别质量优先 |
| `structure` | PPStructureV3（版面含 seal 标签 + 印章 det/rec，全本地） | 否 | 单容器部署、印章场景 |
| `seal` | SealRecognition 独立印章识别 | 否 | 仅印章 |

文档引擎默认开启 `restructure_pages`（跨页表格合并、多级标题重建、多页拼接），
`--no-restructure` 可关闭。

## 完整验收流程

### 阶段 0：部署与启动（服务器宿主机）

```bash
# 构建镜像（compose 已含 build 配置，自动构建并打 tag docparse-npu:v1；
# 仅在 Dockerfile/requirements.txt 变更后需要重建，代码更新 git pull 即生效）
docker compose build

# 也可以构建 + 启动一步完成
docker compose up -d --build

# 启动全部服务：先起 vllm-ascend，healthcheck 通过（模型加载完成）后自动启动 docparse-npu
docker compose up -d

# 观察 vLLM 模型加载进度（NPU 加载数分钟属正常）
docker logs -f vllm-ascend

# 进入开发容器（此后所有推理命令在其中执行）
docker exec -it docparse-dev bash
```

### 阶段 1：容器内推理验收（依赖 NPU）

```bash
# ① 预检：配置来源 / 三引擎模型目录 / vLLM 就绪与已加载模型名，全部 OK 再继续
python -m docparse check

# ② vLLM API 连通性：单图识别，换 --task 依次验证 ocr/table/formula/chart
python -m docparse ocr /app/paddle/test/demo.png --task ocr

# ③ 单文件解析全流程（三条引擎各验一遍）
python -m docparse parse input/pdfs/某文件.pdf                      # vl-server（默认）
python -m docparse parse input/pdfs/某文件.pdf --engine structure   # 全本地+印章
python -m docparse parse /app/paddle/input/seal_test/xx.png --engine seal

# ④ 批量推理：验证异常隔离（单文件失败不中断）、重试、进度与汇总报告
python -m docparse parse                      # 缺省取 INPUT_PDF_DIR 整目录
python -m docparse parse --retries 3          # 失败重试 3 次
# 结束查看 output/batch_report.json（成功/失败/单文件耗时/错误信息）

# ⑤ smoke 脚本（等价于上述 CLI，test_seal.py 额外打印识别明细）
python /app/paddle/test/test_api.py
python /app/paddle/test/test_vl_server.py
python /app/paddle/test/test_structure.py
python /app/paddle/test/test_seal.py

# ⑥ 压测：QPS 与延迟分布（容器内跑）
python /app/paddle/test/benchmark.py
```

### 阶段 2：宿主机验收（无需 NPU，仅 HTTP API 类命令）

`check`（vLLM 部分）、`ocr`、`test/benchmark.py` 只访问 vLLM 的 HTTP API，不加载模型，
可在宿主机（或任何能访问 NPU 服务器的机器）用 uv 直接运行。vLLM 容器使用 host 网络，
宿主机通过 `http://<NPU服务器IP>:8000/v1` 访问：

```bash
# 首次运行 uv 会按 pyproject.toml 自动建虚拟环境并安装 docparse（仅轻量依赖 openai/PyYAML）
# vLLM 端口映射为宿主机 8312（8000 被占用）
export VLLM_SERVER_URL=http://<NPU服务器IP>:8312/v1

uv run docparse check                    # 宿主机上模型目录显示"缺失"属正常，只看 vLLM 行
uv run docparse ocr demo.png --task table
uv run python test/benchmark.py          # 压测也可以在宿主机跑
```

> 注意：`parse`（vl-server/structure/seal 引擎）需要 NPU 推理，**必须在容器内运行**；
> 宿主机仅限 `ocr` / `check` / `benchmark` 三类纯 HTTP 命令。

## 环境变量

全部有默认值，完整清单见 [.env.example](.env.example)。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DOCPARSE_CONFIG` | 仓库根 config.yaml | 配置文件路径 |
| `PPDOCLAYOUT_MODEL_PATH` | `/app/models/PaddlePaddle/PP-DocLayoutV2` | 版面分析模型路径 |
| `PPDOCLAYOUT_MODEL_NAME` | `PP-DocLayoutV2` | 版面模型名（vl-server 引擎） |
| `SEAL_DET_MODEL_PATH` | `/app/models/PaddlePaddle/PP-OCRv4_server_seal_det` | 印章检测模型路径 |
| `SEAL_REC_MODEL_PATH` | `/app/models/PaddlePaddle/PP-OCRv4_server_rec` | 印章识别模型路径 |
| `VLLM_SERVER_URL` | `http://localhost:8000/v1` | vLLM 服务地址（容器内由 compose 注入服务名地址） |
| `VLLM_MODEL_NAME` | `PaddleOCR-VL-0.9B` | vLLM served 模型名 |
| `VLLM_MODEL_PATH` | `/app/models/PaddlePaddle/PaddleOCR-VL` | vLLM 模型路径（start_vllm.sh） |
| `VLLM_PORT` | `8000` | vLLM 容器内端口（start_vllm.sh + 健康检查） |
| `VLLM_HOST_PORT` | `8312` | vLLM 宿主机映射端口（compose ports） |
| `VLLM_MAX_BATCHED_TOKENS` | `16384` | vLLM 批处理 token 上限（start_vllm.sh） |
| `OUTPUT_DIR` | `/app/paddle/output` | 推理结果输出目录 |
| `INPUT_PDF_DIR` | `/app/paddle/input/pdfs` | 批量推理输入目录 |
| `DOCPARSE_DEVICE` | `npu` | 推理设备 |

## 目录结构

```
.
├── Dockerfile              # docparse-npu 镜像（PaddlePaddle + CustomNPU）
├── docker-compose.yml      # docparse-npu + vllm-ascend 双服务编排
├── config.yaml             # ★ 主配置（模型/引擎参数，版本升级入口）
├── pyproject.toml          # 宿主机 uv run 支持（轻量依赖 + docparse 命令）
├── requirements.txt        # 容器内 Python 依赖（含 NPU 推理依赖）
├── docparse/               # ★ 核心库
│   ├── config.py           # config.yaml + 环境变量加载（Settings）
│   ├── pipelines.py        # 三引擎管线工厂（构造参数可透传）
│   ├── client.py           # vLLM OpenAI 兼容客户端 + 就绪探测
│   ├── postprocess.py      # restructure_pages + 统一保存
│   ├── batch.py            # 批量：异常隔离/重试/进度/汇总报告
│   └── cli.py              # docparse parse|ocr|check
├── scripts/
│   └── start_vllm.sh       # vLLM 启动脚本（参数环境变量化）
├── test/                   # smoke 测试 + 压测（复用 docparse 库）
├── input/                  # 测试输入（gitignore，数据在服务器）
└── output/                 # 推理结果输出（gitignore）
```
