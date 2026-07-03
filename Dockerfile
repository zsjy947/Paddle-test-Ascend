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


# 下载并安装 PaddleCustomNPU
RUN wget -q https://paddle-whl.bj.bcebos.com/stable/npu/paddle-custom-npu/paddle_custom_npu-3.2.0-cp310-cp310-linux_aarch64.whl && \
    pip install --no-cache-dir paddle_custom_npu-3.2.0-cp310-cp310-linux_aarch64.whl && \
    rm paddle_custom_npu-3.2.0-cp310-cp310-linux_aarch64.whl

# 安装 PaddleOCR 及 safetensors
RUN python -m pip install --no-cache-dir -U "paddleocr[doc-parser]" && \
    pip install --no-cache-dir safetensors

RUN python -m pip install --no-cache-dir numpy==1.26.4 && \
    python -m pip install --no-cache-dir opencv-python==3.4.18.65

WORKDIR /app

CMD ["/bin/bash"]
