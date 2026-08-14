# Qwen3-VL 视觉问答 - Gradio 界面
# 基于 CUDA 13.0 + PyTorch + Qwen3-VL-32B
# 优化策略: 多阶段构建 + 依赖分层缓存,代码修改只重 build 最后阶段

# ============ 阶段 1: 系统依赖 + Python (极少变更) ============
FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04 AS base

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

# 系统依赖 - 这一层几乎不变,GitHub Actions 会永久缓存
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

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

# ============ 阶段 2: PyTorch (极少变更) ============
FROM base AS pytorch

# 升级 pip + 安装 PyTorch (CUDA 13.0) - 这一层也很少变
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir \
        --pre torch torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/cu130 \
    || (echo "torchaudio 安装失败,重试不带 torchaudio" && \
        python -m pip install --no-cache-dir \
            --pre torch torchvision \
            --index-url https://download.pytorch.org/whl/cu130)

# ============ 阶段 3: Python 依赖 (requirements.txt 变更时才重建) ============
FROM pytorch AS deps

# Qwen3-VL 需要 transformers >= 4.55.0
# Gradio 锁定 5.x (避免 6.x API 破坏性变更)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

# ============ 阶段 4: 应用代码 (代码变更只重建这一层) ============
FROM deps AS app

# 创建持久化目录
RUN mkdir -p /app/models /app/outputs /app/uploads /app/cache

# 复制应用代码 (放在最后,变更最频繁)
COPY app.py /app/app.py

# 暴露 Gradio 端口
EXPOSE 7860

# 健康检查 - 给 15 分钟启动窗口(首次下载 67GB 模型)
HEALTHCHECK --interval=30s --timeout=10s --start-period=900s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# 启动 Gradio
CMD ["python", "app.py"]
