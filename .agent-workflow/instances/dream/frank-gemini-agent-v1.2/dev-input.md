# Dev Input

Workflow Instance: `dream/frank-gemini-agent-v1.2`

Role: `Dev`

Execution Tool: `Codex`

Status: `READY_FOR_DEV`

## Mandatory Role Boundary

You are now acting as Dev for this workflow instance.

Dev may modify business code, tests, and documentation within the project as needed to implement the frozen requirements below.

Dev must not:

- Change product boundaries defined by the PRD.
- Restore PRD-deprecated functionality as a main user flow.
- Skip Review, QA, or Delivery.
- Claim final delivery.
- Hide unimplemented requirements or failing tests.

During execution, update:

- `dev-heartbeat.json`
- `progress-events.jsonl`
- `dev-output.md`
- `evidence-manifest.md`

If work takes longer than 10 minutes without user-visible output, update `dev-heartbeat.json`.

Long commands must have progress events before and after execution.

## Project

`/Users/zhuzilou/workspace/ai/gemini/Dream`

## Feature

Frank Gemini Agent V1.2

## Source Of Truth

Use these documents in priority order:

1. `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/PRD-Frank-Gemini-Agent-V1.2.md`
2. `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/Frank-Gemini-职能规划与小白友好设计原则.md`
3. `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/Frank-Gemini-V1.2-Legacy-功能处置说明.md`

Framework instructions:

- `/Users/zhuzilou/Documents/multi-agents-design/roles/dev-agent.md`
- `/Users/zhuzilou/Documents/multi-agents-design/doc/agent-workflow/heartbeat-and-progress-rules.md`

## Goal

Implement the V1.2 minimum closed loop:

1. Entry routing and Legacy isolation.
2. Scenario 1: individual-stock buy decision and observation plan.
3. Scenario 2: board/sector observation pool and teaching review.
4. Observation Memory persistence and basic commands.
5. Term Learning Queue with explicit commands.
6. Shared structured Markdown / Feishu card output layer.

## Frozen Product Boundaries

Frank Gemini is not a stock recommendation robot. It is an A-share research companion for beginners.

All user-visible answers must preserve the user's final decision authority.

Do not output deterministic buy/sell commands.

Avoid these phrases:

- 建议建仓
- 建议加仓
- 最佳补仓点
- 严禁入场
- 果断减仓
- 必买
- 必卖

Use conditional / lower-intensity phrasing:

- 可观察
- 可轻仓试错
- 等待确认
- 降低仓位风险
- 回避
- 不适合追高
- 暂不满足买入条件
- 条件满足时可以考虑

Deprecated as main user flows:

- 定时新闻直接推送
- 回复消息触发的 RiskAuditor 审核

Retain and isolate:

- Feishu message ingress/reply
- Stock name/code recognition
- AkShare stock data, historical K line, news, announcements where available
- Individual-stock technical analysis
- Existing `watchlist` as long-term manual watchlist
- Existing positions
- Markdown / Feishu card sending capability as shared output infrastructure

Do not mix `watchlist` with new Observation Memory.

## Required User Entrypoints

Route these to Scenario 1:

- `xx 股票能买吗`
- `xx 现在能不能买`
- `xx 最近一直跌，可以抄底吗`
- `分析下 xx 的走势，是否有合适买入点`
- `分析 600021`
- `上海电力最近一直在跌，可以买入吗`

Route these to Scenario 2:

- `最近有哪些板块值得关注`
- `有什么股票值得关注`
- `我不知道接下来该看什么`
- `收盘后帮我看方向`
- `选股`
- `推荐一些股票`
- `买什么`

Route these to Term Learning Queue:

- `记录术语 放量修复 场景7.1`
- `待补充术语`
- `术语记录`
- `导出术语记录`

Route these to Observation Memory:

- `查看观察池`
- `最近观察池`
- `复盘观察池`
- `复盘观察池 1`

Legacy commands such as `监控`、`买入`、`卖出`、`池子`、`持仓分析` may remain, but must be isolated and must not reuse V1.2 Observation Memory incorrectly.

`审核` must not remain a main flow. If kept, return a deprecated guidance message that redirects users to concrete stock/board questions.

## Scenario 1 Requirements

For a stock buy-decision question, output:

- User question translation.
- Conclusion first.
- Real data evidence.
- Current state judgment.
- Trigger conditions.
- Invalidation conditions.
- Position discipline.
- Observation checklist.
- Data missing / fallback notes.
- Key term explanations.

At minimum, attempt to fetch:

- Stock name, code, exchange.
- Current price or latest close.
- 20-day high/low.
- 60-day high/low.
- 5/10/20-day moving averages.
- Recent 3-5 trading-day volume.
- Key support and resistance.
- Data fallback / missing fields.

If data is missing, state it explicitly and do not fabricate values.

When using these terms, explain them as executable rules:

- 一日游
- 有效跌破
- 站不稳
- 放量下跌
- 缩量企稳
- 放量修复
- 轻仓试错
- 支撑位
- 压力位

## Scenario 2 Requirements

For board/sector observation requests, output:

- Explicit boundary: this is an observation pool, not a buy list.
- Data timestamp.
- Whether output is official after-close pool or intraday temporary version.
- Market environment.
- Board/sector levels: A/B/C/D.
- 1-2 candidate stocks per board.
- Observation conditions per stock.
- Next step: each candidate should enter Scenario 1 before buy/sell decisions.

Board scoring weights:

- Board capital flow: 30%
- Board price change: 20%
- Board turnover/activity: 20%
- Sustainability: 20%
- Beginner friendliness: 10%

Intraday handling:

- Do not reject intraday.
- Mark as `盘中临时观察版`.
- State data is changing, confidence is lower, and after-close regeneration is needed.

Candidate filters:

- Board has heat and capital support.
- Individual stock has sufficient turnover/liquidity.
- Exclude ST, delisting, suspended, or obviously abnormal-risk symbols.
- Avoid candidates that are only limit-up, cannot be bought, or obviously overheated.
- Prefer representative, explainable stocks that can be further observed via Scenario 1.
- Max 1-2 stocks per board.

## Observation Memory Requirements

Add persistence for:

- `observation_runs`
- `observation_boards`
- `observation_stocks`
- `observation_reviews`

Suggested columns from PRD:

`observation_runs`:

- id
- trade_date
- market_summary
- data_timestamp
- created_at
- status

`observation_boards`:

- id
- run_id
- board_name
- board_level
- reason
- risk_note

`observation_stocks`:

- id
- run_id
- board_id
- symbol
- name
- reason
- observe_conditions
- invalidation_conditions
- status

`observation_reviews`:

- id
- stock_id
- review_date
- price_snapshot
- condition_results
- conclusion
- lesson

Implementation may add fields if needed for traceability, but must not change the product meaning.

Review output should explain:

- Why later movement supports considering buy / continued observation.
- Why later movement supports removal / risk reduction.
- Which conditions were primary and which were auxiliary.
- What the user should watch next time.

## Term Learning Queue Requirements

Add `term_learning_queue` with at least:

- id
- term
- raw_message
- frank_answer
- user_feedback
- related_scene
- status
- created_at
- resolved_at

First version only needs explicit commands:

- `记录术语 xxx 场景x`
- `待补充术语`
- `术语记录`
- `导出术语记录`

Statuses:

- new
- needs_review
- added_to_design
- implemented
- ignored

## Shared Output Layer Requirements

Add or refactor a shared structured output layer.

Scene/business layers should produce structured content such as:

- title
- conclusion
- evidence
- conditions
- risks
- next_steps
- metadata

Markdown and Feishu card output should share this intermediate representation where practical.

Do not break existing `FeishuBot.send_interactive_message` low-level behavior.

Avoid repeated ad-hoc Markdown card construction in every scene.

## Suggested Technical Approach

Follow existing project style: Python modules under `src/`, `unittest` tests under `tests/`, SQLite persistence through existing DB path conventions.

Likely modules to create:

- `src/core/db.py`
- `src/generator/card_renderer.py`
- `src/listener/intent_router.py`
- `src/scenarios/stock_decision.py`
- `src/scenarios/board_observation.py`
- `src/memory/observation_memory.py`
- `src/memory/term_learning.py`

Likely modules to modify:

- `src/main.py`
- `src/listener/feishu_listener.py`
- `src/scraper/akshare_client.py`
- `src/strategist/technical_analysis.py`
- `src/strategist/trade_advisor.py`
- tests under `tests/`

This is guidance, not a requirement. Dev may choose a better decomposition if it preserves product scope and testability.

## Existing Code Risks To Address

Known conflicts observed by Coordinator:

- `src/listener/feishu_listener.py` currently routes `推荐/选股/买什么` into old recommendation behavior.
- `src/listener/feishu_listener.py` currently keeps reply-message `审核` as a main flow.
- `src/main.py` currently schedules and pushes direct news cards.
- `src/strategist/trade_advisor.py` contains strong trading phrases that conflict with PRD.
- `src/scraper/akshare_client.py` currently lacks board capital-flow / board constituent helpers.
- `tests/test_strategist.py` currently expects old strong `建仓` behavior and must be updated.

## Testing Requirements

Use Python `unittest` style consistent with the project.

Add tests for at least:

1. Intent routing:
   - Recommendation requests go to Scenario 2.
   - Stock buy-decision requests go to Scenario 1.
   - Deprecated audit does not enter `handle_audit`.

2. Scenario 1:
   - Includes required data fields when mock data is available.
   - Explicitly lists missing/fallback data when mock data is incomplete.
   - Includes key term explanations.
   - Does not include banned strong trading phrases.

3. Scenario 2:
   - Produces observation pool, not buy list.
   - Marks intraday temporary version when appropriate.
   - Persists `observation_runs`, `observation_boards`, and `observation_stocks`.
   - Limits candidates to 1-2 stocks per board.

4. Observation Memory:
   - Can list recent observation pools.
   - Can create a manual review record from mocked later K-line / price data.

5. Term Learning Queue:
   - Can add explicit term record.
   - Can list recent / pending terms.
   - Can export term records.

6. Shared output layer:
   - Renders structured content to Markdown.
   - Keeps title/conclusion/evidence/conditions/risks/next_steps visible.

Framework-generated tests must include these text markers:

```text
AGENT_WORKFLOW_TEST
workflow_instance: dream/frank-gemini-agent-v1.2
feature: Frank Gemini Agent V1.2
```

Run targeted tests. If running full historical test suite is feasible, run it too; if not, explain why and list residual risk.

Preferred baseline command:

```bash
python tests/run_tests.py
```

## Required Dev Output

Write `.agent-workflow/instances/dream/frank-gemini-agent-v1.2/dev-output.md`.

It must include:

- Conclusion: `DEV_DONE` / `DEV_BLOCKED` / `NEEDS_CONTEXT`.
- Execution tool.
- Input and output files.
- Modified files list.
- Design and implementation summary.
- Implementation details.
- Test strategy.
- Self-test commands and results.
- Test logs or command-output artifact paths.
- Evidence paths.
- Known risks.
- Privacy check.
- If fixing Review/QA feedback, include Fix Traceability Matrix.

If Dev cannot proceed because of product-boundary ambiguity, stop and write `NEEDS_CONTEXT` plus the exact question.

Do not mark `DEV_DONE` unless tests or valid test exemptions are recorded.

## Evidence Requirements

Store command outputs under:

`.agent-workflow/instances/dream/frank-gemini-agent-v1.2/artifacts/command-output/`

If any evidence cannot be localized under `artifacts/`, update `evidence-manifest.md` with:

- external path or manual confirmation source
- reason it cannot be localized
- who confirmed it and when
- privacy status

## Privacy Constraints

Do not write secrets, tokens, `.env` values, Feishu credentials, API keys, or private production data into workflow outputs.

Use placeholders for sensitive configuration.

## Dev Start Checklist

Before editing code, Dev must verify:

- `dev-input.md` read: PASS/FAIL
- PRD read: PASS/FAIL
- Role-positioning design read: PASS/FAIL
- Legacy boundary design read: PASS/FAIL
- Current git status inspected: PASS/FAIL
- Existing tests relevant to touched areas inspected: PASS/FAIL
- Deprecated flows identified: PASS/FAIL
- Business-code edit plan written in Dev notes: PASS/FAIL
