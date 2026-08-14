# Qwen3-VL 视觉问答 - Gradio 界面
# 基于 CUDA 13.0 + PyTorch (Nightly) + Qwen3-VL-32B

FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04

LABEL maintainer="WorkBuddy"
LABEL description="Qwen3-VL Visual Question Answering with Gradio"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CUDA_HOME=/usr/local/cuda-13.0
ENV LD_LIBRARY_PATH=/usr/local/cuda-13.0/targets/x86_64-linux/lib:${LD_LIBRARY_PATH}
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

# HuggingFace 缓存目录(挂载到命名卷实现持久化)
ENV HF_HOME=/app/models/huggingface
ENV HUGGINGFACE_HUB_CACHE=/app/models/huggingface
ENV TRANSFORMERS_CACHE=/app/models/huggingface

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3.11-venv \
    git \
    git-lfs \
    wget \
    curl \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 设置 python3.11 为默认
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

# 先升级 pip 并安装 PyTorch (CUDA 13.0)
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir \
        --pre torch torchvision \
        --index-url https://download.pytorch.org/whl/cu130

# 安装核心依赖 (Gradio 锁定到 5.x,避免 6.x API 破坏性变更)
RUN python -m pip install --no-cache-dir \
    gradio==5.49.1 \
    "transformers>=4.50.0" \
    "accelerate>=1.0.0" \
    safetensors \
    einops \
    huggingface-hub \
    pillow \
    numpy \
    requests \
    sentencepiece \
    protobuf \
    qwen-vl-utils

# 安装 torchaudio (与 torch CUDA 13.0 对应)
RUN python -m pip install --no-cache-dir \
        --pre torchaudio \
        --index-url https://download.pytorch.org/whl/cu130 \
    || echo "torchaudio 安装失败，将以不可用状态继续运行"

# 创建持久化目录
RUN mkdir -p /app/models /app/outputs /app/uploads /app/cache

# 复制应用代码
COPY app.py /app/app.py

# 暴露 Gradio 端口
EXPOSE 7860

# 健康检查 - 给 10 分钟启动窗口(下载模型可能需要时间)
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# 启动 Gradio
CMD ["python", "app.py"]
