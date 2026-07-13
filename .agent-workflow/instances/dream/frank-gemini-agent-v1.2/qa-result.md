# QA Result

Status: `QA_PASSED`

Workflow Instance: `dream/frank-gemini-agent-v1.2`

QA Tool: `Codex`

## Commands Executed

```bash
/Users/zhuzilou/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tests/run_tests.py
```

Result:

```text
Ran 24 tests in 0.110s
OK
```

```bash
rg -n "建议建仓|建议加仓|最佳补仓点|严禁入场|果断减仓|必买|必卖" src doc/manuals tests
```

Result:

```text
Matches only in test assertions.
No matches in src/ or doc/manuals/.
```

```bash
rg -n "handle_audit\(|get_message_content\(|回复某条资讯消息|直接回复.*审核" src/listener src/notifier doc/manuals tests
```

Result:

```text
No Feishu listener user-routing call to handle_audit remains.
get_message_content remains only in notifier infrastructure.
```

## QA Coverage

- V1.2 intent routing: PASS
- Scenario 1 stock decision card: PASS
- Scenario 2 board observation and persistence: PASS
- Observation Memory commands: PASS
- Term Learning Queue commands: PASS
- Legacy watchlist/position isolation: PASS
- Deprecated audit command and blank parent reply behavior: PASS
- Legacy news push disabled by default: PASS
- Banned phrase boundary: PASS

## Residual Risk

Live AkShare connectivity and production Feishu API behavior were not exercised in this local QA pass because the test runner uses mocks for unavailable external packages.

## QA Decision

`QA_PASSED`
