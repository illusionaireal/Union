# S05 受控治理、撤权与责任交接 - Intent

## TaskIntentDraft

- Requested outcome: 完整交付 U-069 / S05 / 在线 #24 并验证提交推送
- Goal: 完整交付 U-069 / S05 / 在线 #24 并验证提交推送
- Success evidence:
- S05 G01–G10 的真实 RED/GREEN、独立身份/持久化与 UI 复核、固定工具链全量、实际浏览器及安装候选证据齐备。
- U-069 通过统一适配器以 controlled 记录，在线 #24 读回完成；仅本轮增量提交推送 rewrite/charter-v1 并核对远端 SHA。
- Stop condition: 全部 S05 受控验收和交付满足后停止，不继续后续切片；尚未满足的证据明确保留为待验证。
- Non-goals:
- S02/S03 自动执行、真实模型、真实数据迁移、部署和真实业务治理验收
- Scope: 受控核心治理、参与者身份、显式采用、有效修订、继任退出、责任与本地结果接受、用户闭环
- Change kinds:
- feature
- Risk hints:
- 身份与权限 / 持久化升级 / 生产者消费者

## BaselineReadSetHint

- specs/053-union-rewrite/tasks.md
- docs/decisions/0006-charter-policy-adoption.md
- docs/UNION_CHARTER_v1.0.md

## BaselineUsageDraft

- Required baseline refs:
- docs/UNION_CHARTER_v1.0.md
- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/decisions/0006-charter-policy-adoption.md
- specs/053-union-rewrite/s05-contract.md
- Delivered context refs:
- none
- Acknowledged before plan:
- specs/053-union-rewrite/plan.md
- docs/decisions/0006-charter-policy-adoption.md
- Cited in plan:
- evidence/057-s05-governance/review-contract.md
- specs/053-union-rewrite/s05-contract.md
- Missing refs:
- none
- Advisory decision: continue

## ImpactStatementDraft

- Compatibility boundary: S01 schema 1 创建/原回执和 legacy 执行保持；auth 0/1 仅显式升级到 2，已采用治理的 AU schema 2 拒绝不兼容候选；无读取迁移或真实数据操作。
- Affected layers:
- 核心认证/显式升级、AU 领域规则、应用编排、SQLite 事务/历史、HTTP/React、安装兼容。
- Owners:
- Identity/identity_schema；domain governance/responsibility；application governance；governance_store；React governance；既有 release_package。
- 协调者 codex/gpt-6/session-01a1a9fa-d89d-7091-ba52-c31a1df00b23 独占主账、Kanban 和 Git。
- Invariants:
- 原创建证据不可变；当前授权由 AU 规则持有；无 legacy 绕过
- Non-goals:
- S02/S03 自动执行、真实模型、真实数据迁移、部署和真实业务治理验收

These records are Method Pack drafts / hints, not authoritative runtime decisions.
