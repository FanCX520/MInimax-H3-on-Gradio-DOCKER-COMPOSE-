# 🎬 MiniMax H3 视频生成 - Phala Cloud 部署

## ✅ 状态：镜像已构建并公开发布！

**镜像地址（公开可拉取）：**
```
ghcr.io/fancx520/minimax-h3-gradio:latest
```

**GitHub 仓库：**
```
https://github.com/FanCX520/MInimax-H3-on-Gradio-DOCKER-COMPOSE-
```

**镜像信息：**
- 基础：`nvidia/cuda:13.0.0-runtime-ubuntu22.04`
- PyTorch：`2.13.0+cu130`（含 torchvision, torchaudio）
- Python：3.11 venv
- Gradio：5.x
- 大小：~4.5 GB

## 🚀 部署到 Phala Cloud（现在只需 1 步！）

### 方法 1：Phala Dashboard（最简单）

1. 登录 https://cloud.phala.network
2. 点 **Deploy** → **docker-compose.yml**
3. 把项目根目录的 `docker-compose.yml` 内容粘贴进去（已配置好 `image:` 字段指向 GHCR）
4. 选择 GPU TEE 节点（H100/H200/B300）
5. 点 **Create**
6. 等 3-5 分钟启动，访问分配的 URL（端口 7860）

### 方法 2：Phala CLI

```bash
# 安装（一次性）
npm install -g phala

# 登录
phala auth login <YOUR_API_KEY>

# 创建 CVM
phala cvms create -n minimax-h3 -c docker-compose.yml

# 查看状态
phala cvms list

# 查看日志（如果启动失败）
phala logs --serial <cvm-id>
```

## 📋 部署清单

- ✅ GitHub 仓库已创建并 push
- ✅ GitHub Actions 工作流配置完成（自动构建+推送 GHCR）
- ✅ 镜像已成功构建（11 分钟）
- ✅ 镜像已公开（匿名可拉取）
- ✅ docker-compose.yml 已更新指向 GHCR 镜像
- ✅ Phala 兼容（image: 字段、命名卷、内联环境变量）

## 🔧 工作流说明

每次你修改代码并 push 到 GitHub，`.github/workflows/build-and-push.yml` 会自动：
1. 构建 linux/amd64 镜像
2. 推送到 `ghcr.io/fancx520/minimax-h3-gradio:latest`
3. 自动设置包为公开

```bash
# 修改代码后重新部署
git add -A
git commit -m "your changes"
git push
# 等待 Actions 完成 → Phala 重新拉取镜像
```

## 🛠️ Phala Cloud 限制（已规避）

| 限制 | 解决方案 |
|---|---|
| ❌ 不支持 `build.context` | ✅ 用 GHCR 预构建镜像 |
| ❌ 不支持外部 Dockerfile | ✅ 镜像已构建好 |
| ❌ 不支持 `env_file` | ✅ 环境变量直接写在 yml |
| ❌ 不支持 host bind volumes | ✅ 全部用命名卷 |
| ❌ 必须 linux/amd64 | ✅ GitHub Actions 强制 amd64 |

## 🐛 故障排查

### Phala 启动失败
```bash
phala logs --serial <cvm-id>
```

### 镜像拉取慢/超时
GHCR 在国内访问可能慢，可考虑：
- 用阿里云容器镜像服务（ACR）中转
- 或在 Phala 选择非亚洲节点

### 显存不足
修改 docker-compose.yml 中的环境变量：
```yaml
- VIDEO_DEFAULT_FRAMES=48    # 减少帧数
- VIDEO_DEFAULT_HEIGHT=480   # 降低分辨率
- VIDEO_DEFAULT_WIDTH=854
```

## 💡 后续优化

- [ ] 把 MiniMax-H3 真实模型集成（替换 app.py 中的占位代码）
- [ ] 添加 Cloudflare CDN 缓存加速 GHCR
- [ ] 配置 webhook 让 Phala 自动重启新版本
