# ⚖️ Audit Report: Feishu Interactive Card Text Extraction Enhancement

**Audit ID**: AR-20260526-Feishu_Card_Enhancement_Report
**Design Doc**: `doc/design/DS-20260526-Feishu_Card_Enhancement.md`
**Auditor**: RiskAuditor (Gemini CLI Agent)
**Status**: ⚠️ NEEDS_WORK

---

## 1. 证伪分析 (Falsification Analysis)

### 1.1 递归死循环与安全性风险
- **风险描述**：虽然 `json.loads` 生成的对象是树状的，但在递归解析时，如果飞书推送了超大规模或极端深度的恶意卡片结构，可能导致 **RecursionError**。
- **证伪逻辑**：目前的方案 `_recursive_extract_text` 没有任何 `max_depth` 限制，也没有针对重复节点的检测（虽然 JSON 本身无循环，但防御性编程不足）。

### 1.2 i18n 国际化结构缺失
- **风险描述**：飞书卡片协议允许文本字段以 `i18n` 对象形式存在（例如 `{"i18n": {"zh_cn": "文本", "en_us": "Text"}}`）。
- **证伪逻辑**：方案仅考虑了 `content` 字段。如果研报卡片采用 i18n 结构，`header` 和 `elements` 的提取将全部返回空值，导致审计失败。

### 1.3 标题权重前缀的“噪音”干扰
- **风险描述**：方案引入了 `[标题]` 前缀。
- **证伪逻辑**：`FeishuListener.handle_audit` 使用 2-4 位的滑动窗口匹配中文。`[标题]` 中的 `标题` 符合匹配长度要求。虽然目前 A 股没有名为“标题”的股票，但这种强侵入性的标记增加了 `resolve_stock_symbol` 的无效查询开销，且如果未来出现类似名称的行业或个股，会产生误报。

### 1.4 解析逻辑的覆盖面漏洞
- **风险描述**：方案逻辑为：如果 `Header` 或 `Elements` 有内容，则跳过“兜底全量解析”。
- **证伪逻辑**：飞书卡片可能包含 `extra` 或自定义的 `div` 模块。如果这些模块位于 `elements` 之外，则在满足前两个条件时，这些关键信息将被丢失。

---

## 2. 改进建议 (Actionable Items)

1.  **增加 i18n 支持**：`_recursive_extract_text` 必须支持从 `i18n` 字段中优先提取 `zh_cn`。
2.  **防御性递归**：引入 `max_depth=10` 的深度限制。
3.  **无损权重标记**：建议取消 `[标题]` 这种自然语言标记，改为在结果字符串头部直接放置标题内容，或者使用不可见字符/特殊占位符，以防干扰模糊匹配。
4.  **合并解析流**：不要分阶段返回，而是建立一个 `seen_text` 集合，先处理 Header 内容加入集合，再递归处理全量，跳过已存在于集合中的文本，确保顺序正确且不丢失信息。

---

## 3. 最终审计结论

### ⚠️ NEEDS_WORK

**结论说明**：方案在“有序提取”上方向正确，但在 **i18n 兼容性** 和 **防御性递归** 上存在明显缺陷。特别是 i18n 的缺失可能导致针对特定类型卡片的解析彻底失效。建议修复上述问题后再进行实施。
