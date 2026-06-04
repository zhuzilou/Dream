# 🛠️ Design Spec: Feishu Interactive Card Text Extraction Enhancement

**ID**: DS-20260526-Feishu_Card_Enhancement
**Status**: DRAFT
**Author**: Codebase Investigator (Sub-Agent)
**Target Module**: `src/notifier/feishu.py`

---

## 1. 背景 (Background)
用户反馈在回复 Frank 的研报卡片并输入“审核”时，系统无法识别股票信息。原因是 `get_message_content` 提取卡片文本时没有顺序保证，且不支持 `markdown` 标签。股票名称通常在标题中，若标题文本在结果中位置靠后，会被 `FeishuListener` 的扫描窗口忽略。

## 2. 详细方案 (Detailed Design)

### 2.1 核心思路
按照 **Header -> Elements -> Others** 的顺序显式提取文本，确保标题内容位于返回字符串的顶部。

### 2.2 逻辑重构
- **方法提取**：新增私有方法 `_parse_interactive_card(self, card_data)`。
- **递归助手**：新增 `_recursive_extract_text(self, obj)`，支持 `plain_text`, `lark_md`, `markdown` 标签。
- **优先级策略**：手动先调用 header 解析，再调用 elements 解析，最后全量递归。

### 2.3 伪代码示例
```python
def _parse_interactive_card(self, card_data):
    results = []
    # 1. 优先提取 Header (权重最高)
    header_text = self._recursive_extract_text(card_data.get('header', {}))
    if header_text: results.append(f'[标题] {header_text}')
    
    # 2. 提取 Elements (主要内容)
    elements_text = self._recursive_extract_text(card_data.get('elements', []))
    if elements_text: results.append(elements_text)
    
    # 3. 兜底解析全量
    if not results: 
        return self._recursive_extract_text(card_data)
        
    return '\n'.join(results).strip()
```

## 3. 风险评估 (Risk Assessment)
- **重复提取**：全量递归可能会导致标题内容重复出现在结尾，但在 `FeishuListener` 中前 500 字符已足够匹配，重复不影响逻辑。
- **性能**：递归处理中小型 JSON 无性能风险。

---
## 4. 验收标准
1. 对包含股票名称的标题卡片回复“审核”，审计官能正确识别股票。
2. 单元测试覆盖 `_parse_interactive_card` 处理复杂嵌套结构的情况。
3. 提取结果首部包含 `[标题]` 标记。
