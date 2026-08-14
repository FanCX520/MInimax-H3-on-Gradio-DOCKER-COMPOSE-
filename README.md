# 🎬 MiniMax H3 视频生成 - Phala Cloud 部署

## ⚠️ 重要前提

**Phala Cloud 不支持 `build.context`** —— 必须先在本地构建镜像并推送到 Docker Hub，
然后用 `image:` 字段引用。这是你只能上传 yml 文件无法绕过的硬限制。

## 🚀 部署流程（4 步）

### 第 1 步：本地构建 + 推送镜像

你必须有一台能跑 Docker 的机器（本地电脑 / 服务器 / GitHub Actions）。最简单的方式：

#### 方案 A：用 GitHub Actions（推荐，无需本地 Docker）

1. 把整个项目 push 到你的 GitHub 仓库
2. 进入仓库 Settings → Secrets and variables → Actions → New repository secret
3. 添加：
   - `DOCKERHUB_USERNAME` = 你的 Docker Hub 用户名
   - `DOCKERHUB_TOKEN` = 你的 Docker Hub Access Token（在 Docker Hub → Account Settings → Security 生成）
4. `git push` 触发自动构建，推送到 Docker Hub

#### 方案 B：本地构建（如果你有 Docker）

```bash
# 1. 登录 Docker Hub
docker login

# 2. 设置用户名
export DOCKERHUB_USER=你的用户名

# 3. 一键构建 + 推送
bash build-and-push.sh
```

镜像构建大约需要 10-20 分钟（要下载 PyTorch Nightly ~3GB）。

### 第 2 步：修改 docker-compose.yml

把 `docker-compose.yml` 中的：
```yaml
image: YOUR_DOCKERHUB_USER/minimax-h3-gradio:latest
```
改成你的实际镜像名，例如：
```yaml
image: zhangsan/minimax-h3-gradio:latest
```

### 第 3 步：上传到 Phala Cloud

两种方式：

#### A. Phala Dashboard（推荐新手）
1. 登录 https://cloud.phala.network
2. 点 Deploy → docker-compose.yml
3. 把修改后的 `docker-compose.yml` 内容粘贴进去
4. 选择 GPU TEE 型号（H100 / H200 / B300）
5. 点 Create

#### B. Phala CLI（推荐开发者）
```bash
# 安装
npm install -g phala

# 登录
phala auth login <YOUR_API_KEY>

# 部署
phala cvms create -n minimax-h3 -c docker-compose.yml
```

### 第 4 步：访问服务

部署完成后，Phala 会分配一个 URL，类似：
```
https://xxxxxx-7860.dstack-prod.phala.network
```

打开就能看到 Gradio 界面。

## 📁 项目文件

```
├── docker-compose.yml          # Phala 部署配置 (只有 image 字段，没有 build)
├── Dockerfile                  # 镜像构建
├── requirements.txt            # Python 依赖
├── app.py                      # Gradio 应用
├── build-and-push.sh           # 本地构建脚本
├── .github/workflows/build-and-push.yml   # GitHub Actions 自动构建
└── README.md
```

## 🔧 关键说明

| 项 | 配置 |
|---|---|
| 基础镜像 | `nvidia/cuda:13.0.0-runtime-ubuntu22.04` |
| PyTorch | Nightly cu130 (兼容你的日志) |
| Python | 3.11 |
| Gradio | >= 5.0 |
| 端口 | 7860 |
| 健康检查 | curl localhost:7860 |
| 架构 | linux/amd64 (Phala 硬性要求) |

## 🛠️ 故障排查

### 镜像拉取失败
- 确认 Docker Hub 镜像名拼写正确
- 确认镜像已设为 `public`（或 Private 但 Phala 有权限）
- 检查 `pull_policy: always`

### 容器启动失败
```bash
# Phala CLI 查看日志
phala logs --serial <cvm-id>
```

### GPU 不可用
Phala GPU TEE 节点（H100/H200/B300）会自动注入 NVIDIA 运行时。CPU TEE 节点不支持 GPU。

### 健康检查一直失败
首次启动需要下载 PyTorch + 模型权重，可能耗时 5-10 分钟。已设置 `start_period: 240s` 容忍。

## 💰 成本参考

Phala GPU TEE 节点按使用时长计费，H100 大约 $1-2/小时。建议：
- 测试时用小尺寸（256x256, 16 帧）
- 不用时及时停止 CVM（`phala cvms stop <id>`）
- 模型可以下载到命名卷，下次启动复用

## ❓ 为什么不能纯单文件？

Phala Cloud 的限制（来自官方文档 `phala-network-phala-cloud-compose-check`）：

> ❌ `build.context` 路径引用 → CVM 上不存在该路径
> ❌ 外部 `dockerfile` 文件 → CVM 上不存在该文件
> ❌ `env_file` → CVM 上不存在该文件
> ✅ 只能引用已推送到镜像仓库的 `image:`

所以"只能上传 docker-compose.yml" ≠ "单文件全自动"，必须配合镜像仓库使用。
