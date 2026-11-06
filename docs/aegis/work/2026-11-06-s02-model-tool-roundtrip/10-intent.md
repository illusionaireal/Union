# S02 核心模型与只读工具往返 - Intent

## TaskIntentDraft

- Requested outcome: 完整交付 U-072/S02/#21，验证后提交推送；最新接续先完成具体执行链设计与四块开发卡样板
- Goal: 完整交付 U-072/S02/#21，验证后提交推送
- Success evidence:
- 当前设计检查点：部署图、首份交付时序、模块改造及主账 U-072 样板与代码/证据一致；独立设计复核和结构检查
- M01-M10、真实profile、独立复核、完整固定检查与远端SHA读回
- Stop condition: 整卡含真实出口通过才done；账号/资源未落实不擅自调用、不关闭卡片
- Non-goals:
- S03任意目标/S04反馈、其他profiles、生产迁移或部署
- Scope: 父任务为核心配置、有限资源授权、持久两阶段模型工具往返和真实profile；本次先交付执行设计/样板，S03/S04/S06只拟议不实施
- Change kinds:
- feature
- Risk hints:
- 身份/费用/持久化/恢复/跨组件契约

## BaselineReadSetHint

- specs/053-union-rewrite/s02-contract.md
- docs/decisions/0005-au-runtime-boundaries.md
- docs/decisions/0006-charter-policy-adoption.md

## BaselineUsageDraft

- Required baseline refs:
- docs/UNION_CHARTER_v1.0.md
- specs/053-union-rewrite/s02-contract.md
- docs/decisions/0005-au-runtime-boundaries.md
- docs/decisions/0006-charter-policy-adoption.md
- Delivered context refs:
- none
- Acknowledged before plan:
- docs/UNION_CHARTER_v1.0.md
- specs/053-union-rewrite/s02-contract.md
- docs/decisions/0005-au-runtime-boundaries.md
- docs/decisions/0006-charter-policy-adoption.md
- Cited in plan:
- docs/UNION_CHARTER_v1.0.md
- specs/053-union-rewrite/s02-contract.md
- docs/decisions/0005-au-runtime-boundaries.md
- docs/decisions/0006-charter-policy-adoption.md
- Missing refs:
- none
- Advisory decision: continue

## ImpactStatementDraft

- Compatibility boundary: 保留schema1/2及legacy；schema3显式采用；本设计提交仅含已授权S02文档/记录，运行代码和无关dirty保留
- Affected layers:
- 当前设计与卡片文档；运行代码保持原S02工作树
- 后续拟议Runtime/Harness/modeld接缝，当前不实施
- Owners:
- codex/gpt-6/s02-2026-11-06 独占共享事务/主账/在线/Git
- Invariants:
- 主账唯一拥有状态与验收；文档通过不关闭U-072
- 原ID/责任/unknown与预算保留；无双派发、无读取迁移
- 原S02变更继续保留；不提交其他任务的既有修改
- Non-goals:
- S03任意目标/S04反馈、其他profiles、生产迁移或部署

These records are Method Pack drafts / hints, not authoritative runtime decisions.

## 2026-11-06 接续修正

用户指定会话的最后具体要求是先补清进程、接口、状态与代码设计，再把 U-072 写成四块完整样板。原 S02 未结束；原“只等真实 profile”记述不再准确：本轮复验凭据四反例仍 RED，另有线程 start 恢复、结构化诊断、中断事件用量、浏览器文字/完整场景及实际安装缺口。详见 evidence/058-s02-model-tools/design-readback.md。

当前检查点不修改运行行为；文档使用结构/一致性和独立源码复核，不制造行为 RED。后续行为保持 TDD Route strict。继续使用原 checkout/工作记录，开工源快照为宿主 .union/s02-design-resume/task-start.json，HEAD c31bf0e；只认领原 U-072 范围。ADR-0005 的增量方向保留，S03/S06 的游标/调用/并发接缝是实施前待冻结的具体方案。
