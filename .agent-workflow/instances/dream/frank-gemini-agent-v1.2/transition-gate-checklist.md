# Transition Gate Checklist

Workflow Instance: `dream/frank-gemini-agent-v1.2`

## Startup Checklist

- 已阅读 START_HERE.md：PASS
- 已阅读 USAGE.md：PASS
- 已阅读角色规则：PASS
- 当前身份仅为 Coordinator Candidate：PASS
- 已确认当前项目：PASS
- 已确认功能名：PASS
- 已确认需求目标：PASS
- 已确认验收标准：PASS
- 已确认角色工具分配：PASS
- 已检查实例目录是否已存在：PASS
- 已确认实例处理方式：NEW_INSTANCE
- 已创建 Workflow Instance：PASS
- 必需文件和目录完整：PASS

## Requirement -> Dev Gate

- from_stage: requirement
- to_stage: dev
- 输出文件存在：PASS (`dev-input.md`)
- 状态结论合法：PASS (`DEV_INPUT_READY`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`coordinator-heartbeat.json`, `dev-heartbeat.json`)
- evidence-manifest 已更新：PASS
- 必需证据已写入 artifacts/ 或有人工确认：PASS
- transition-gate-checklist 已更新：PASS
- 结论：GATE_PASSED

## Dev -> Review Gate

- from_stage: dev
- to_stage: review
- 输出文件存在：PASS (`dev-output.md`, `review-input.md`)
- 状态结论合法：PASS (`DEV_DONE`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`dev-heartbeat.json`)
- evidence-manifest 已更新：PASS
- 必需证据已写入 artifacts/ 或有人工确认：PASS
- transition-gate-checklist 已更新：PASS
- 结论：GATE_PASSED

## Review -> Dev Rework Gate

- from_stage: review
- to_stage: dev
- 输出文件存在：PASS (`review-result.md`)
- 状态结论合法：PASS (`REVIEW_REJECTED`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`review-heartbeat.json`)
- evidence-manifest 已更新：PASS
- 阻断问题已明确：PASS
- 结论：GATE_PASSED

## Dev Rework -> Review Gate

- from_stage: dev
- to_stage: review
- 输出文件存在：PASS (`dev-output.md`, `artifacts/command-output/dev-tests.txt`)
- 状态结论合法：PASS (`DEV_DONE`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`dev-heartbeat.json`)
- 回归测试已补充：PASS
- 结论：GATE_PASSED

## Review -> QA Gate

- from_stage: review
- to_stage: qa
- 输出文件存在：PASS (`review-result.md`, `qa-input.md`)
- 状态结论合法：PASS (`REVIEW_PASSED`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`review-heartbeat.json`)
- evidence-manifest 已更新：PASS
- 结论：GATE_PASSED

## QA -> Delivery Gate

- from_stage: qa
- to_stage: delivery
- 输出文件存在：PASS (`qa-result.md`, `delivery-summary.md`)
- 状态结论合法：PASS (`QA_PASSED`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`qa-heartbeat.json`)
- QA 证据已写入 artifacts：PASS
- 结论：GATE_PASSED

## Delivery Final Gate

- from_stage: delivery
- to_stage: delivered
- 输出文件存在：PASS (`delivery-summary.md`, `state.json`, `current-status.md`)
- 状态结论合法：PASS (`DELIVERABLE`)
- 结论与正文无冲突：PASS
- heartbeat 存在且未阻塞：PASS (`delivery-heartbeat.json`)
- evidence-manifest 已更新：PASS
- 必需证据已写入 artifacts/ 或有人工确认：PASS
- transition-gate-checklist 已更新：PASS
- 结论：GATE_PASSED
