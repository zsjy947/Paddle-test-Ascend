#!/bin/bash
# vLLM Ascend 后端启动脚本：参数可用环境变量覆盖，默认值与历史行为一致
set -euo pipefail

VLLM_MODEL_PATH="${VLLM_MODEL_PATH:-/app/models/PaddlePaddle/PaddleOCR-VL}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_MODEL_NAME="${VLLM_MODEL_NAME:-PaddleOCR-VL-0.9B}"
VLLM_MAX_BATCHED_TOKENS="${VLLM_MAX_BATCHED_TOKENS:-16384}"

export VLLM_USE_MODELSCOPE=True
export TASK_QUEUE_ENABLE=1
export CPU_AFFINITY_CONF=1
export PYTORCH_NPU_ALLOC_CONF="expandable_segments:True"

# hf-overrides 说明：部分 ModelScope 来源的 PaddleOCR-VL 副本 config.json 带 speculators 草稿模型
# 声明，vLLM>=0.11 启动时会按字面值解析草稿模型名（如 "model"），非本地路径也非合法 repo id，
# 叠加 VLLM_USE_MODELSCOPE 后直接抛 Invalid repo_id 退出；置空该字段以禁用未启用的投机解码
exec vllm serve "$VLLM_MODEL_PATH" \
  --max-num-batched-tokens "$VLLM_MAX_BATCHED_TOKENS" \
  --served-model-name "$VLLM_MODEL_NAME" \
  --trust-remote-code \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --compilation-config '{"cudagraph_mode":"FULL_DECODE_ONLY"}' \
  --additional_config '{"enable_cpu_binding":true}' \
  --port "$VLLM_PORT" \
  --hf-overrides '{"speculators": []}'
