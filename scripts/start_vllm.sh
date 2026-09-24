#!/bin/bash
# vLLM Ascend 后端启动脚本：参数可用环境变量覆盖，默认值与历史行为一致
set -euo pipefail

VLLM_MODEL_PATH="${VLLM_MODEL_PATH:-/app/models/PaddlePaddle/PaddleOCR-VL}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_MODEL_NAME="${VLLM_MODEL_NAME:-PaddleOCR-VL-0.9B}"

export VLLM_USE_MODELSCOPE=True
export TASK_QUEUE_ENABLE=1
export CPU_AFFINITY_CONF=1
export PYTORCH_NPU_ALLOC_CONF="expandable_segments:True"

exec vllm serve "$VLLM_MODEL_PATH" \
  --max-num-batched-tokens 16384 \
  --served-model-name "$VLLM_MODEL_NAME" \
  --trust-remote-code \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --compilation-config '{"cudagraph_mode":"FULL_DECODE_ONLY"}' \
  --additional_config '{"enable_cpu_binding":true}' \
  --port "$VLLM_PORT"
