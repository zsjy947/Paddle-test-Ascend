# 进度记录

## 2026-09-24

- 架构重构：散装脚本重组为 `ppdoc` 核心库 + CLI（`python -m ppdoc parse|ocr|check`）
  - 三条解析管线统一工厂可切换：vl-server（版面+vLLM）/ structure（PPStructureV3 全本地+印章）/ seal（印章独立）
  - 配置收编至 `config.py` 单一来源，消除模型名/端口 5 处硬编码（新增 `VLLM_MODEL_NAME` 环境变量）
  - 批量推理增强：单文件异常隔离 + 失败重试（线性退避）、N/M 进度与耗时统计、`batch_report.json` 汇总报告
  - `test/` 五个脚本重写为复用库的薄 smoke 脚本；删除 `scripts/batch_inference_pdfs.py`（由 CLI 取代）
- 编排改进：vllm-ascend 增加 healthcheck（/v1/models）与 restart 策略，ppdoc-npu depends_on 健康后启动；
  `start_vllm.sh` 参数环境变量化（VLLM_MODEL_PATH/VLLM_PORT/VLLM_MODEL_NAME）；NPU 设备映射与卡号未改动
- 依赖管理：新增 `requirements.txt`；Dockerfile 增加 `PYTHONPATH=/app/paddle`（挂载即用 ppdoc 包）
- 环境变量名与默认值、输出目录结构（output/<文件名>/<文件名>[_i].json/.md）保持不变，服务器侧用法兼容

## 2026-07-06

- 调整 Dockerfile 和 compose 参数
- test_ppdoclayout.py 显式指定 `vl_rec_api_model_name="PaddleOCR-VL-0.9B"`
- 新增 `scripts/batch_inference_pdfs.py`：批量读取 `input/pdfs/` 下 PDF 文件，调用 PP-DocLayoutV2 pipeline 处理，输出 JSON 和 Markdown 至 `output/`

## 2026-07-03

- 初始提交：PaddleOCR on Ascend NPU 910B 测试环境
- Dockerfile 和 docker-compose.yml 基础配置
