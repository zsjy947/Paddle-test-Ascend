#!/bin/bash

export VLLM_USE_MODELSCOPE=True
export TASK_QUEUE_ENABLE=1
export CPU_AFFINITY_CONF=1
export PYTORCH_NPU_ALLOC_CONF="expandable_segments:True"

vllm serve /app/models/PaddlePaddle/PaddleOCR-VL \
  --max-num-batched-tokens 16384 \
  --served-model-name PaddleOCR-VL-0.9B \
  --trust-remote-code \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --compilation-config '{"cudagraph_mode":"FULL_DECODE_ONLY"}' \
  --additional_config '{"enable_cpu_binding":true}' \
  --port 8000
