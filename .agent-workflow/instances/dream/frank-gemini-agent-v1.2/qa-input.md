# QA Input

Workflow Instance: `dream/frank-gemini-agent-v1.2`

Role: `QA`

Execution Tool: `Codex`

Status: `READY_FOR_QA`

## QA Scope

Validate the V1.2 minimum closed loop against the PRD and Legacy boundary documents:

- V1.2 entry routing.
- Scenario 1 stock decision output.
- Scenario 2 board observation output and Observation Memory persistence.
- Term Learning Queue commands.
- Legacy isolation for watchlist/positions.
- Deprecated audit behavior, including blank parent replies.
- Scheduler default behavior for legacy direct news push.
- Banned strong trading phrase boundary.

## Evidence To Verify

- `dev-output.md`
- `review-result.md`
- `artifacts/command-output/dev-tests.txt`
- `artifacts/command-output/dev-banned-phrases-scan.txt`
- `tests/test_v12_agent_workflow.py`
- `tests/test_functional_commands.py`
- `tests/test_strategist.py`

## Required QA Commands

```bash
/Users/zhuzilou/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tests/run_tests.py
```

```bash
rg -n "建议建仓|建议加仓|最佳补仓点|严禁入场|果断减仓|必买|必卖" src doc/manuals tests
```

## QA Notes

Network/live AkShare connectivity is outside the current unit-test evidence and should be reported as a residual integration risk if not separately verified.
