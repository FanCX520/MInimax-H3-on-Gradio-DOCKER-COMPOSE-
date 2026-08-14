# MiniMax H3 视频生成 - Gradio 图参考文生图
# 基于 CUDA 13.0 + PyTorch (Nightly)

FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04

LABEL maintainer="WorkBuddy"
LABEL description="MiniMax H3 Video Generation with Gradio Image-to-Video UI"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CUDA_HOME=/usr/local/cuda-13.0
ENV LD_LIBRARY_PATH=/usr/local/cuda-13.0/targets/x86_64-linux/lib:${LD_LIBRARY_PATH}
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

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

# 先升级 pip 并安装 PyTorch nightly (CUDA 13.0)
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir \
        --pre torch torchvision \
        --index-url https://download.pytorch.org/whl/cu130

# 安装核心依赖 (Gradio 锁定到 5.x,避免 6.x API 破坏性变更)
RUN python -m pip install --no-cache-dir \
    gradio==5.49.1 \
    transformers \
    accelerate \
    diffusers \
    safetensors \
    einops \
    omegaconf \
    huggingface-hub \
    imageio \
    imageio-ffmpeg \
    av \
    opencv-python-headless \
    pillow \
    numpy \
    scipy \
    requests \
    pydantic \
    fastapi \
    uvicorn \
    python-multipart \
    sentencepiece \
    protobuf

# 安装 torchaudio (与 torch CUDA 13.0 对应)
RUN python -m pip install --no-cache-dir \
        --pre torchaudio \
        --index-url https://download.pytorch.org/whl/cu130 \
    || echo "torchaudio 安装失败，将以不可用状态继续运行"

# 修复 PyTorch 旧版本属性问题（total_mem -> total_memory）
RUN python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available())" \
    || true

# 复制应用代码
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

# 暴露 Gradio 端口
EXPOSE 7860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# 启动 Gradio
CMD ["python", "app.py"]
