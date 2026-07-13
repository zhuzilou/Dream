# Frank Gemini V1.2 补充审查报告

## 审查范围

- 基准提交：`179111a fix: address V1.2 review blockers`
- 审查目标：复查上一轮阻塞项修复情况，并确认是否仍有影响 V1.2 部署的入口问题。
- 测试结果：本地执行 `tests/run_tests.py`，共 29 个用例通过。

## 总体结论

上一轮审查报告中的 4 个阻塞项已基本修复：

- 常见个股问题已进入场景一。
- `复盘观察池 1` 已能写入 `observation_reviews`。
- 板块数据为空时不再生成“数据待确认方向”假观察池。
- 飞书帮助文案已切换为 V1.2 产品口径。

但仍发现一个高频自然语言入口会绕过 V1.2 场景二。建议修复后再部署。

## P2：`买哪只/哪支` 类推荐入口仍会绕回 Legacy 分支

### 位置

- `src/listener/intent_router.py:52`
- `src/listener/feishu_listener.py:176`
- `src/listener/feishu_listener.py:254`

### 触发条件

用户输入以下口语化选股问题：

- `买哪只股票`
- `买哪支股票`
- `哪只股票值得看`
- `哪支股票值得关注`
- `帮我看看买哪只`

### 当前表现

实测 `route_intent` 结果如下：

```text
买哪只股票 => chat_fallback
买哪支股票 => chat_fallback
哪只股票值得看 => chat_fallback
哪支股票值得关注 => chat_fallback
帮我看看买哪只 => chat_fallback
```

这些问题没有在 `intent_router` 中进入 `SCENARIO_BOARD_OBSERVATION`。随后在 `feishu_listener.py` 的旧分支里，会被 `is_recommendation_request` 捕获，并进入旧的 `handle_stock_recommendation`。

### 影响

这是股市小白非常常见的问法，语义上等价于“最近有哪些板块值得关注 / 有什么股票值得关注”。如果继续走 Legacy 推荐逻辑，用户会看到旧版基于 watchlist / positions 的候选说明，而不是 V1.2 的“板块观察池”。

这会造成两类问题：

- 产品体验不一致：同样是“我不知道买什么”，有些问法进入场景二，有些问法进入旧流程。
- 场景二使用率下降：用户最自然的口语入口没有命中新流程。

### 建议修复

在 `intent_router.py` 的 `board_keywords` 中补充以下关键词：

```python
"买哪",
"哪支",
"哪只",
"哪支股票",
"哪只股票",
"值得看",
"值得关注"
```

或者更稳妥地增加一个推荐类意图判断，将 `feishu_listener.py` 中 `is_recommendation_request` 的关键词集合前移到 `intent_router.py`，统一由路由层决定是否进入 `SCENARIO_BOARD_OBSERVATION`，避免后续 Legacy 分支继续分流。

### 建议补充测试

新增或扩展 `tests/test_v12_agent_workflow.py`：

```python
self.assertEqual(route_intent("买哪只股票").intent_type, IntentType.SCENARIO_BOARD_OBSERVATION)
self.assertEqual(route_intent("买哪支股票").intent_type, IntentType.SCENARIO_BOARD_OBSERVATION)
self.assertEqual(route_intent("哪只股票值得看").intent_type, IntentType.SCENARIO_BOARD_OBSERVATION)
self.assertEqual(route_intent("哪支股票值得关注").intent_type, IntentType.SCENARIO_BOARD_OBSERVATION)
```

新增或扩展 `tests/test_functional_commands.py`：

```python
self.listener.handle_board_observation.assert_called_once()
self.listener.handle_stock_recommendation.assert_not_called()
```

## 部署建议

建议暂缓部署。该问题修复成本较低，但命中用户真实口语表达的概率较高。修复后再跑完整测试，并重点验证：

- `买哪只股票` 进入场景二。
- `不知道买什么，帮我推荐几支股票` 仍进入场景二。
- `上海电力最近一直跌，可以买吗` 仍进入场景一。
- Legacy `监控 / 买入 / 卖出 / 池子` 不受影响。
