# U-110 完整体验契约与派单证据

2026-11-13；核查基线 `d27d543e044a4111204c898130f9187c9e4770f7`。范围为 documentation：完整体验契约、独立设计复核、规范追踪和已经读回的 Kanban 修正。不代表新前端、真实执行或持续组织能力已交付。

交付文件：[产品体验](../../docs/product-design.md)、[前端责任](../../docs/FRONTEND.md)、[规范追踪](../../specs/053-union-rewrite/charter-traceability.md)、[续审处置](../../docs/reviews/2026-11-13-v1-correction-followup.md)。

## 复核

独立角色 `audit_v1_experience` 对实际源码和草稿初审后提出：成果 URL 缺 Work 作用域（High）、旅程编号与 PRD 冲突（Medium）、任务来源冲突（Medium）及生产者名称修正。协调者已修正；二审确认无剩余阻断，并验证退出/会话到期与运行授权撤销分开，以及 U-092/U-093 的共享事实边界。

独立角色 `audit_branch_delivery` 检查当前分支、PR 目标与任务来源，发现 053/tasks 和 PROJECT 非生成段的残留权威句；修正后二审通过。旧日期记录没有被改成新的实现事实。

## 可重复检查

在仓库根使用固定 Node 24.19.0：

```sh
node evidence/U-110/check-design.mjs
```

[结构结果](design-structure.json)：Main Charter SHA256 保持采用值；规范 40/40、细化旅程 10、整体验收 10、所查相对链接目标 47；历史开发附录 SHA256 `e7ecf31dca5933415bc702c7d7adeffe667c91a8cabbb52de92631e6214a81bd` 与基线一致。此脚本只检结构和明确引用，语义由上述独立复核提供，不能用行数证明产品符合性。

## Kanban

U-110/#64 从 ready 认领进入 progress，HTTP 200，实际成员 `zbook-codex`；分支为 `codex/v1-correction-execution-20261113`。真实 actor 和写入版本记录在[派单读回](assignment-readback.json)中，不保存访问凭据。

[派单计划](assignment-plan.json)是先准备的具体范围；U-119–U-124 六张卡随后逐一创建并读回。U-112/U-113/U-114 保留完整验收，子卡继承真实前置，原在制责任不变。revision 1172 依赖图无环、无归档或缺失前置。后续状态不得从此快照推断。

实现层面的缺口仍由各执行卡负责：公开业务资料、持久完整工作意图、AI Work 交接，以及新页面与反馈/恢复/改进/合作的贯通。父卡不因本文档或子卡通过而自动完成。
