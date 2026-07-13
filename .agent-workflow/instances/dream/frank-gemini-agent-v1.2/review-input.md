# Review Input

Status: `READY_FOR_REVIEW`

Workflow Instance: `dream/frank-gemini-agent-v1.2`

Role: `Review`

Execution Tool: `Codex`

## Role Boundary

You are now acting as Review.

Review is read-only. Do not modify business code, tests, or docs.

Review must inspect the implementation against PRD, Dev output, tests, evidence, and role boundaries.

## Required Inputs

- `.agent-workflow/instances/dream/frank-gemini-agent-v1.2/dev-input.md`
- `.agent-workflow/instances/dream/frank-gemini-agent-v1.2/dev-output.md`
- `.agent-workflow/instances/dream/frank-gemini-agent-v1.2/evidence-manifest.md`
- `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/PRD-Frank-Gemini-Agent-V1.2.md`
- `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/Frank-Gemini-职能规划与小白友好设计原则.md`
- `/Users/zhuzilou/workspace/ai/gemini/Dream/doc/design/Frank-Gemini-V1.2-Legacy-功能处置说明.md`

## Review Scope

Review all Dev-modified files listed in `dev-output.md`, including new files under:

- `src/generator/`
- `src/listener/`
- `src/memory/`
- `src/scenarios/`
- `src/scraper/`
- `src/strategist/`
- `tests/`
- `doc/manuals/`

## Checklist Verification

Mark each item as `PASSED`, `FAILED`, `NOT_APPLICABLE`, or `NOT_VERIFIABLE`.

1. Entry routing sends stock buy-decision questions to Scenario 1.
2. Entry routing sends recommendation / board observation questions to Scenario 2.
3. Audit no longer enters RiskAuditor main flow.
4. Direct scheduled news push is disabled by default.
5. Scenario 1 output includes real data evidence, trigger conditions, invalidation conditions, position discipline, observation checklist, missing/fallback notes, and term explanations.
6. Scenario 1 avoids banned strong trading language.
7. Scenario 2 outputs observation pool, not buy list.
8. Scenario 2 supports intraday temporary version and lower-confidence messaging.
9. Scenario 2 persists Observation Memory.
10. Observation Memory tables and helper methods are present.
11. Term Learning Queue explicit commands are implemented.
12. Shared structured output layer exists and is reused by new scenes.
13. Existing `watchlist` and positions remain isolated from Observation Memory.
14. Tests include `AGENT_WORKFLOW_TEST`, workflow instance, and feature markers where framework-generated.
15. Dev self-test evidence exists and matches changed behavior.
16. No product-boundary changes beyond PRD.

## Required Review Output

Write `.agent-workflow/instances/dream/frank-gemini-agent-v1.2/review-result.md`.

It must include:

- Conclusion: `REVIEW_PASSED` / `REVIEW_REJECTED` / `REVIEW_BLOCKED`.
- Execution tool.
- Input and output files.
- Checklist Verification.
- Review scope.
- Blocking issues.
- Non-blocking issues.
- Code evidence.
- Fix suggestions.
- Review evidence path.

If rejected, each blocking issue must include severity, location/module, trigger condition, risk, evidence, and suggested fix direction.
