# Evidence Manifest

Workflow Instance: `dream/frank-gemini-agent-v1.2`

Status: `DELIVERABLE`

## Source Evidence

| Evidence | Path | Status | Privacy |
| --- | --- | --- | --- |
| User pasted workflow instruction | `/Users/zhuzilou/.codex/attachments/8816789a-d1f0-4bab-a270-06850ebbc226/pasted-text-1.txt` | Read | Local file, not copied |
| Workflow entry | `/Users/zhuzilou/Documents/multi-agents-design/START_HERE.md` | Read | Local framework document |
| Workflow usage | `/Users/zhuzilou/Documents/multi-agents-design/USAGE.md` | Read | Local framework document |
| Role rules | `/Users/zhuzilou/Documents/multi-agents-design/roles/` | Read | Local framework documents |
| Runtime gates | `/Users/zhuzilou/Documents/multi-agents-design/doc/agent-workflow/workflow-runtime-gates.md` | Read | Local framework document |
| Heartbeat rules | `/Users/zhuzilou/Documents/multi-agents-design/doc/agent-workflow/heartbeat-and-progress-rules.md` | Read | Local framework document |
| Progress relay rules | `/Users/zhuzilou/Documents/multi-agents-design/doc/agent-workflow/subagent-progress-relay-rules.md` | Read | Local framework document |
| PRD | `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/PRD-Frank-Gemini-Agent-V1.2.md` | Read | Project design document |
| Role-positioning design | `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/Frank-Gemini-职能规划与小白友好设计原则.md` | Read | Project design document |
| Legacy boundary design | `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/Frank-Gemini-V1.2-Legacy-功能处置说明.md` | Read | Project design document |

## Localized Evidence

| Evidence | Path | Status |
| --- | --- | --- |
| Initial command summary | `artifacts/command-output/initial-checks.txt` | Present |

## Dev Evidence

| Evidence | Path | Status | Privacy |
| --- | --- | --- | --- |
| Full test run | `artifacts/command-output/dev-tests.txt` | Present | No secrets |
| Banned phrase scan | `artifacts/command-output/dev-banned-phrases-scan.txt` | Present | No secrets |
| Review rework regression | `tests/test_functional_commands.py` | Present | No secrets |

## Review Evidence

Review passed after Dev rework fixed blank parent reply RiskAuditor reachability.

## QA Evidence

| Evidence | Path | Status | Privacy |
| --- | --- | --- | --- |
| QA test run | `artifacts/command-output/qa-tests.txt` | Present | No secrets |
| QA banned phrase scan | `artifacts/command-output/qa-banned-phrases-scan.txt` | Present | No secrets |
| Docker integration smoke | `artifacts/command-output/docker-integration-tests-20260713.txt` | Present | Secrets redacted |
| Review fix verification | `artifacts/command-output/review-fix-tests-20260713.txt` | Present | No secrets |
| Follow-up review fix verification | `artifacts/command-output/followup-review-fix-tests-20260713.txt` | Present | No secrets |
| QA result | `qa-result.md` | Present | No secrets |

## Delivery Evidence

| Evidence | Path | Status | Privacy |
| --- | --- | --- | --- |
| Delivery summary | `delivery-summary.md` | Present | No secrets |
| Delivery gate checklist | `transition-gate-checklist.md` | Present | No secrets |
