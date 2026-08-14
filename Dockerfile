# Qwen3-VL 视觉问答 - Gradio 界面
# 基于 NVIDIA PyTorch 官方镜像 (包含兼容的 Python 3.11 和 PyTorch 2.8 + CUDA 12.8)

# ============ 阶段 1: 基础镜像 (NVIDIA 官方 PyTorch) ============
FROM nvcr.io/nvidia/pytorch:25.08-py3 AS base

LABEL maintainer="WorkBuddy"
LABEL description="Qwen3-VL Visual Question Answering with Gradio"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# HuggingFace 缓存目录 (挂载到命名卷实现持久化)
ENV HF_HOME=/app/models/huggingface
ENV HUGGINGFACE_HUB_CACHE=/app/models/huggingface
ENV TRANSFORMERS_CACHE=/app/models/huggingface

# 系统依赖 - 这一层几乎不变
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    wget \
    curl \
    ca-certificates \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ============ 阶段 2: Python 依赖 (requirements.txt 变更时才重建) ============
FROM base AS deps

# Qwen3-VL 需要 transformers >= 4.55.0
# Gradio 锁定 5.x (避免 6.x API 破坏性变更)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r /app/requirements.txt

# ============ 阶段 3: 应用代码 (代码变更只重建这一层) ============
FROM deps AS app

# 创建持久化目录
RUN mkdir -p /app/models /app/outputs /app/uploads /app/cache

# 复制应用代码 (放在最后,变更最频繁)
COPY app.py /app/app.py

# 暴露 Gradio 端口
EXPOSE 7860

# 健康检查 - 给 15 分钟启动窗口 (首次下载 67GB 模型)
HEALTHCHECK --interval=30s --timeout=10s --start-period=900s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# 启动 Gradio
CMD ["python", "app.py"]
