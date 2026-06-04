# 🛠️ Design Spec: Feishu Interactive Card Parsing for Audit

**ID**: DS-20260526-001
**Status**: COMPLETED
**Author**: Gemini CLI Orchestrator
**Target Module**: `src/notifier/feishu.py`

---

## 1. 问题背景 (Context)
用户反馈在使用“审核”功能时，回复 Frank 发送的研报（卡片消息）没有反应。经诊断，原因是 `get_message_content` 逻辑仅支持 `text` 和 `post` 类型，无法识别 `interactive` (消息卡片) 类型的消息体，导致审计官（RiskAuditor）无法获取上下文。

## 2. 方案目标 (Objectives)
- 实现对 Feishu `interactive` 消息类型的解析。
- 能够从复杂的卡片 JSON 结构中递归提取出所有的文本信息，以便识别股票代码（6位数字）或股票名称。

## 3. 详细设计 (Detailed Design)

### 3.1 核心算法：递归提取 (Recursive Extraction)
由于飞书卡片（Card）的结构高度嵌套且组件多样（`div`, `column_set`, `markdown` 等），采用硬编码路径解析不可行。
**策略**：
- 定义 `extract_text(obj)` 递归函数。
- 识别 `tag` 为 `plain_text` 或 `lark_md` 的对象，并提取其 `content` 字段。
- 深度优先遍历所有字典和列表。

### 3.2 模块集成
在 `src/notifier/feishu.py` 的 `get_message_content` 方法中增加条件分支：
```python
elif msg_type == "interactive":
    # 调用递归提取逻辑
```

## 4. 风险评估 (Risk Assessment)
- **性能**：由于卡片 JSON 通常较小（<10KB），递归深度有限，不会造成性能瓶颈。
- **误报**：提取出的纯文本将送往 `resolve_stock_symbol` 进行模糊匹配，需确保提取内容完整。

---
## 5. 验收标准
- [x] 能从 `interactive` 消息中提取文本。
- [x] 回复卡片消息并输入“审核”能正确触发 RiskAuditor。
- [x] 不破坏原有的 `text` 和 `post` 解析逻辑。
