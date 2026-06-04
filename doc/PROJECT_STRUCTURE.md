# 📂 Frank Gemini 项目目录结构说明 (Project Structure)

本文档旨在说明 Frank Gemini 项目的目录组织规范，帮助开发者快速定位资源。

---

## 1. 根目录 (Root Directory)
根目录仅保留核心配置文件与项目入口。

- `.env`: 环境变量配置（包含 API Key、飞书凭据、版本号）。
- `GEMINI.md`: 项目核心指令、技术规约与 AI 行为准则。
- `DEPLOYMENT.md`: 详细的部署、发布与发版记录指南。
- `requirements.txt`: Python 依赖清单。
- `Dockerfile.base`: **基础环境镜像**（OS、时区、库环境），极大加速构建。
- `Dockerfile`: **应用镜像**（仅包含业务代码），基于基础镜像构建。
- `docker-compose.yml`: Docker 服务编排定义。
- `gemini-extension.json`: 项目扩展程序元数据。

---

## 2. 核心文件夹 (Core Directories)

### 📂 `src/` (源代码)
存放所有业务逻辑。
- `analyst/`: 核心分析引擎。包含 `llm_engine.py` (LLM 调用) 和 `risk_auditor.py` (风险审计专家)。
- `scraper/`: 数据抓取。包含 `akshare_client.py` 等行情获取逻辑。
- `strategist/`: 策略逻辑。包含技术指标分析与交易建议生成。
- `listener/`: 消息监听。包含飞书 WebSocket 交互逻辑。
- `notifier/`: 消息推送。包含飞书富文本/卡片消息推送逻辑。
- `generator/`: 内容生成。负责 Markdown 研报和卡片模板的渲染。
- `main.py`: 系统总入口，负责调度与初始化。

### 📂 `tests/` (测试与验证)
- `run_tests.py`: 自动化测试套件执行入口。
- `test_*.py`: 各模块的单元测试。
- `verify_connectivity.py`: API 连通性验证工具。

### 📂 `doc/` (文档中心)
- `design/`: 功能设计文档、架构演进方案。
- `manuals/`: 用户手册、操作指南。
- `test_reports/`: 自动化测试生成的质量报告。
- `action_logs/`: Orchestrator 的执行决策日志。
- `archive/`: 历史过期的方案、文档归档。

### 📂 `scripts/` (运维脚本)
- `deploy.ps1` / `deploy.bat`: 辅助部署脚本。

### 📂 `data/` (持久化数据)
- `scout.db`: 系统核心 SQLite 数据库（存储持仓、监控记录）。
- `reports/`: 系统生成的历史研报存档 (Markdown 格式)。

### 📂 `logs/` (系统日志)
- `app.log`: 运行时的详细调试日志。

---

## 3. 设计原则
1. **环境与代码分离**：通过 Docker 镜像分层，将耗时的软件环境安装与频繁变动的代码逻辑隔离。
2. **多智能体解耦**：`src/analyst/` 下的不同专家代理（如 RiskAuditor）保持逻辑独立，通过 Orchestrator 调度。
3. **文档即资产**：所有的设计决策、测试报告和变更日志均有文档沉淀，方便回溯。

---
*Last Updated: 2026-05-26*
