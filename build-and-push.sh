# ================================================================
# MiniMax H3 - 一键本地构建 + 推送脚本
# ================================================================
# 用法 (本地有 Docker 的机器上执行):
#   1. 登录 Docker Hub:
#      docker login
#   2. 设置环境变量:
#      export DOCKERHUB_USER=your_username
#   3. 运行此脚本:
#      bash build-and-push.sh
# ================================================================

set -e

# ---------- 配置 ----------
DOCKERHUB_USER="${DOCKERHUB_USER:-YOUR_DOCKERHUB_USER}"
IMAGE_NAME="minimax-h3-gradio"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE="${DOCKERHUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"

# ---------- 检查 ----------
if [ "$DOCKERHUB_USER" = "YOUR_DOCKERHUB_USER" ]; then
  echo "❌ 请先设置 DOCKERHUB_USER 环境变量:"
  echo "   export DOCKERHUB_USER=your_actual_username"
  exit 1
fi

if ! command -v docker &> /dev/null; then
  echo "❌ Docker 未安装"
  exit 1
fi

# ---------- 检查必需文件 ----------
for f in Dockerfile requirements.txt app.py; do
  if [ ! -f "$f" ]; then
    echo "❌ 缺少文件: $f"
    exit 1
  fi
done

# ---------- 构建 (强制 amd64, Phala 要求) ----------
echo "🔨 构建镜像: ${FULL_IMAGE}"
echo "   平台: linux/amd64"
echo ""

# 检查 buildx
if docker buildx version &> /dev/null; then
  docker buildx build \
    --platform linux/amd64 \
    --tag "${FULL_IMAGE}" \
    --push \
    --progress=plain \
    .
else
  echo "⚠️  docker buildx 不可用,使用普通 build"
  echo "   注意: 必须在 amd64 机器上执行 (Mac M1/M2/M3 用户会失败)"
  docker build --tag "${FULL_IMAGE}" .
  echo "🚀 推送镜像..."
  docker push "${FULL_IMAGE}"
fi

echo ""
echo "✅ 完成!"
echo "   镜像已推送到: ${FULL_IMAGE}"
echo ""
echo "📋 下一步:"
echo "   1. 修改 docker-compose.yml 中的 image 为:"
echo "      image: ${FULL_IMAGE}"
echo "   2. 把 docker-compose.yml 上传到 Phala Cloud"
echo "   3. 等待启动,访问 7860 端口"
