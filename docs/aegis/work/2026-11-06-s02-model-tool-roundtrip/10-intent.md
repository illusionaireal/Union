# S02 核心模型与只读工具往返 - Intent

## TaskIntentDraft

- Requested outcome: 完整交付 U-072/S02/#21，验证后提交推送；最新用户反馈先改写全部 12 张 V1 卡，使操作、产物和演示可直接理解
- Goal: 完整交付 U-072/S02/#21，验证后提交推送
- Success evidence:
- 卡片检查点：12 张线上卡 HTTP 200 读回；完整技术原文移到现有开发附录；64 项其他任务和全部非文字管理字段保持；独立表达复核与结构检查通过
- 当前设计检查点：部署图、首份交付时序、模块改造及主账 U-072 样板与代码/证据一致；独立设计复核和结构检查
- M01-M10、真实profile、独立复核、完整固定检查与远端SHA读回
- Stop condition: 整卡含真实出口通过才done；账号/资源未落实不擅自调用、不关闭卡片
- Non-goals:
- S03任意目标/S04反馈、其他profiles、生产迁移或部署
- Scope: 父任务仍为 S02 配置、有限资源授权、持久模型工具往返和真实验证；当前检查点只改 12 卡文案及引用，保留技术要求与任务状态，不实施未来卡
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

- Compatibility boundary: 保留 schema 1/2 与 legacy；schema 3 显式采用；当前提交仅含 12 卡文案、完整技术验收附录和对应记录，运行代码与无关修改保留
- Affected layers:
- 当前只改 12 张 V1 卡及其开发引用；原 S02 运行代码保持
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

## 2026-11-06 接续修正（上一设计检查点）

用户指定会话的最后具体要求是先补清进程、接口、状态与代码设计，再把 U-072 写成四块完整样板。原 S02 未结束；原“只等真实 profile”记述不再准确：本轮复验凭据四反例仍 RED，另有线程 start 恢复、结构化诊断、中断事件用量、浏览器文字/完整场景及实际安装缺口。详见 evidence/058-s02-model-tools/design-readback.md。

当前检查点不修改运行行为；文档使用结构/一致性和独立源码复核，不制造行为 RED。后续行为保持 TDD Route strict。继续使用原 checkout/工作记录，开工源快照为宿主 .union/s02-design-resume/task-start.json，HEAD c31bf0e；只认领原 U-072 范围。ADR-0005 的增量方向保留，S03/S06 的游标/调用/并发接缝是实施前待冻结的具体方案。

## 2026-11-06 最新卡片可读性反馈

用户指出“每一个卡片要干啥看不懂，内容太抽象”。本次将 12 张现有 V1 卡改为完成后可做的事情、具体操作、演示和当前进度；详细技术验收保留在原 tasks.md 的开发附录。上次设计检查点已提交推送至 4c49d5d；本次从该 HEAD 接续原记录，没有替换父任务。证据为 evidence/058-s02-model-tools/card-clarity.json。

开始时有 136 份既有修改文件；134 份哈希保持，另两份未跟踪看板脚本出现本任务外变化，来源未确认并保留现场。不能声称所有预存文件完全不变；此次仅提交文案和对应记录，S02 原有缺陷与真实验收仍未完成。
