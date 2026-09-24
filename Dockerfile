FROM ccr-2vdh3abv-pub.cnc.bj.baidubce.com/device/paddle-npu:cann800-ubuntu20-npu-910b-base-aarch64-gcc84

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

# 系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        wget \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 PaddlePaddle
RUN python -m pip install --no-cache-dir paddlepaddle==3.2.0

# 下载并安装 PaddleCustomNPU（aarch64 专用 wheel，需单独下载）
RUN wget https://paddle-whl.bj.bcebos.com/stable/npu/paddle-custom-npu/paddle_custom_npu-3.2.0-cp310-cp310-linux_aarch64.whl && \
    pip install --no-cache-dir paddle_custom_npu-3.2.0-cp310-cp310-linux_aarch64.whl && \
    rm paddle_custom_npu-3.2.0-cp310-cp310-linux_aarch64.whl

# Python 依赖（paddleocr / openai 等）
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

# NPU 环境兼容性降级：paddleocr 依赖解析会拉高版本，此处强制固定（勿并入 requirements.txt，
# 单文件解析会因 opencv 版本约束冲突而失败，必须事后降级覆盖）
RUN python -m pip install --no-cache-dir numpy==1.26.4 && \
    python -m pip install --no-cache-dir opencv-python==3.4.18.65

# /app/paddle 挂载仓库代码，docparse 包直接 import，无需 pip install
ENV PYTHONPATH=/app/paddle

WORKDIR /app

CMD ["/bin/bash"]
