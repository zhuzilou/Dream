# 🚀 Frank Gemini 部署与发布指南 (Ops Guide)

本文件详细说明如何将 Frank Gemini 从本地开发环境迁移至 24 小时运行的服务器（x86_64 架构）。

---

## 📦 1. 发布准备 (在本机/开发环境)

在发布新版本之前，请确保本地测试已通过。

### A. 版本定型
修改项目根目录下的 `.env` 文件：
```bash
APP_VERSION=v1.1.1  # 递增版本号
```

### B. 打包源码
在项目根目录下执行以下命令，排除无关文件并打包：
```bash
tar -czvf frank_gemini_release.tar.gz \
    --exclude='.DS_Store' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.idea' \
    --exclude='tests' \
    .env docker-compose.yml Dockerfile Dockerfile.base requirements.txt src/ data/
```
*注：`data/` 目录包含现有的数据库历史，如果是首次部署且不需要历史数据，可以排除。*

---

## 🚚 2. 环境迁移 (至目标服务器)

### A. 传输文件
使用 `scp` 或 SFTP 将压缩包传送到服务器：
```bash
scp frank_gemini_release.tar.gz user@your_server_ip:/path/to/deploy/
```

### B. 解压并进入目录
```bash
tar -xzvf frank_gemini_release.tar.gz
cd Dream  # 进入解压后的目录
```

---

## ⚡ 3. 线上部署 (在目标服务器)

确保服务器已安装 `Docker` 和 `Docker Compose`。

### A. 架构说明 (二层镜像架构)
为了极大提升构建速度，本项目采用分层部署模式：
1.  **基础镜像 (`dream-base`)**：包含操作系统、时区、Python 库环境。仅在依赖变更时重构。
2.  **应用镜像 (`dream-frank`)**：仅包含业务逻辑代码。秒级构建。

### B. 首次部署或依赖变更
如果你是第一次部署，或者修改了 `requirements.txt`，请先构建基础镜像：
```bash
# 构建基础环境（仅需执行一次，除非依赖变更）
docker build -t dream-base:latest -f Dockerfile.base .
```

### C. 启动/更新业务服务
每次修改代码后，执行以下命令即可实现秒级发布：
```bash
docker compose up --build -d
```

### D. 验证运行状态
```bash
docker compose ps                # 查看容器是否 Running
docker compose logs -f --tail 50 # 实时查看运行日志
```

---

## 🔄 4. 版本管理与维护

### 如何升级到新版本？
1.  在本机修改代码并更新 `.env` 中的 `APP_VERSION`。
2.  重复“打包、传输”步骤。
3.  在服务器执行 `docker compose up --build -d`。

### 如何回滚？
如果新版本出现问题，无需重新传输文件：
1.  在服务器修改 `.env` 中的 `APP_VERSION` 为旧版本号。
2.  执行 `docker compose up -d`。系统将秒级切换回旧版容器。

---

## 📝 5. 发版说明

### v1.1.1 (Current - 2026-05-26)
*   **部署架构大重构 (Infrastructure Optimization)**：
    *   **二层镜像架构**：引入 `Dockerfile.base` 隔离环境与代码，代码构建速度从 13 分钟缩短至 **<1 秒**。
    *   **镜像源加速**：`Dockerfile.base` 自动将 Debian 系统源与 Python pip 源切换至国内阿里云镜像，解决网络延迟问题。
    *   **环境自动同步**：新增 `.env` 自动加载机制，实现宿主机与 Docker 容器配置的一致性。
*   **核心功能增强**：
    *   **RiskAuditor 专家代理**：重构风险审计官架构，采用 Orchestrator + Sub-Agent 模式，实现审计人格的冷酷证伪逻辑。
    *   **审计指标增强**：引入换手率、5 日涨幅等量化指标辅助情绪面审核。

### v1.1.0 (2026-05-15)
*   **重大修复**：
    *   **修复飞书 230001 错误**：通过移除冗余的 JSON 包装层，恢复了富文本消息（Post）的发送功能。
*   **稳定性增强**：
    *   同步更新并修复了全量单元测试。

---
*Last Updated: 2026-05-26*
