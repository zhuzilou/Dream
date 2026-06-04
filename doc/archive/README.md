# 🗄️ 归档中心索引 (Archive Index)

本目录用于存放 Frank Gemini 项目演进过程中已废弃、但具备参考价值的历史资产。

---

## 📂 1. 运维脚本 (scripts/)
存放旧版的部署脚本，不再建议在生产环境使用。

- **`deploy.ps1` & `deploy.bat`**: 
  - **废弃原因**: 采用旧的单层镜像构建模式，且内部**硬编码**了飞书和 MiniMax 的 API Keys，存在安全风险。
  - **替代方案**: 当前推荐使用根目录 `.env` 配合 `scripts/deploy_win.ps1` (利用 Docker Compose 管理)。

---

## 📂 2. 设计方案 (designs/)
存放早期的项目规划和架构设计草案。

- **`投资团队搭建方案-20260419.md`**: 
  - **内容**: 项目启动初期的团队分工与愿景规划。
  - **状态**: 已被 `doc/design/` 下的最新模块化设计规约取代。

---

## 📂 3. 元数据 (metadata/)
存放已停用的工具代码段或特定环境的配置文件。

- **`CLAUDE.md.sot-snippet`**: 
  - **内容**: 早期用于同步指令的 Markdown 片段。

---

## 💡 历史变更注记 (History Notes)

### 2026-05-26: 架构大重构
- **目录规范**: 将 `.agent-artifacts` (带点隐藏目录) 统一迁移为 `agent-artifacts` (可见目录)，以提高可见性和管理效率。
- **镜像重构**: 废弃了原有的单层 `Dockerfile` 构建逻辑，引入了 `Dockerfile.base` (环境层) 和 `Dockerfile` (应用层) 的二层架构，显著提升了开发迭代效率。
- **多智能体规范**: 正式确立了“严格工件协议 (Strict Artifact Protocol)”，所有新功能必须在 `agent-artifacts/` 下具备 01-设计、02-实现、03-验证的完整记录。

---
*Last Updated: 2026-05-26*
