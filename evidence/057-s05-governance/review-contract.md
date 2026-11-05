# S05 交付契约与文档一致性复核

2026-11-05；评审者：Codex `/root/s05_boundary_review`。建议性工程复核，范围为 `rewrite/charter-v1` 工作树，基线 HEAD `d9ff5ad23201ee0813707a00f65a0b0d9012a3ee`。除本报告外未修改代码、文档、Git 或任务账，也未重跑已独立验证的后端套件。

**发现结论：本次范围内没有未关闭的 P1/P2。** 发现一项当前任务归属文案漂移，协调者修复后已读回；未发现 S05 契约弱化完整 U-069 受控验收，或将本地人类操作升级为真实治理、AI Execution、自动业务、发布或持续运行证据。

| 发现 | 影响与处置 | 状态 |
| --- | --- | --- |
| DOC-01 / P2 / Implementation Drift / scope: requirements | [安装说明首段](../../ops/release/README.md#L3)原将完整发布验收继续归属旧 U-054 / 048 D，容易成为 V1 的错误前置。现已明确 052/048 与 U-054 仅为历史引用，当前 V1 发布、维护和恢复指向 S08/U-074 及主账；旧任务不成为 V1 前置。此修正不扩大 S05，也不要求重跑治理规则测试。 | 已修复并读回 |

**核对依据。** 阅读了 [S05 契约](../../specs/053-union-rewrite/s05-contract.md)、[plan §9](../../specs/053-union-rewrite/plan.md#9-2026-11-05完整-s05-受控治理)、[tasks 的 S05](../../specs/053-union-rewrite/tasks.md#s05治理准备有效修订与责任交接)、[总体架构](../../docs/ARCHITECTURE.md)、[PRD](../../docs/PRD.md)、[ADR-0006](../../docs/decisions/0006-charter-policy-adoption.md)、[开发入口](../../docs/DEVELOPMENT.md)、[前端说明](../../docs/FRONTEND.md)、[产品设计](../../docs/product-design.md)和[安装说明](../../ops/release/README.md)的当前适用段落，并与以下实际所有者交叉核对。历史日期条目未被当作当前能力或任务状态。

| 交付约定 | 实现核对及结论 |
| --- | --- |
| 稳定主体、普通参与者与 auth 2 | [Identity](../../ai_union/identity.py)仍统一认证；owner/core 分开，core 会话无 legacy/platform 权限。逐账号失败桶不被其他账户成功登录清除；[身份升级器](../../ai_union/identity_schema.py)显式处理 auth 0/1→2，保留已有 principal、原创建回执并使旧会话失效；[重置工具](../../scripts/reset_owner.py)只清理 owner 及其关联账号记录。 |
| 初始根、当前权威和历史回执 | [治理规则](../../ai_union/domain/governance.py)区分不可变初始根与当前治理者；[创建读取](../../ai_union/application/creation.py)交给当前 AU 投影授权，catalog 只定位。原创建回执继续属于 creator；[治理回执](../../ai_union/adapters/governance_store.py)按原提交 principal 查询，不以当前 AU 读取权替代。 |
| schema 1 拒绝与显式采用 | [应用顺序](../../ai_union/application/governance.py)先校验身份、支持范围及输入；合法初次规则/版本拒绝保存原回执而不升级。成功采用才初始化原始快照和 schema 2。[CoreAUStore](../../ai_union/adapters/core_au_store.py)对 schema 1 的可选回执只读校验，不建表、不升级；同 ID 改内容不能重新采用。 |
| 单一写入者、历史与事务 | [治理存储](../../ai_union/adapters/governance_store.py)将状态、Charter、采用/责任变化、原命令、审计和回执关联在一个 AU 事务内；原 state/Charter 字节、创建意图和创建采用保留。认证库事务内重验账号，再提交独立 AU 事务；文档没有将其描述为跨库全局事务。 |
| 当前可用性和有效程序 | 当前治理者/适用后继账号在激活、续期、行动和结果采用处重验；[投影](../../ai_union/application/governance.py)用 `readiness_gaps` 说明缺失主体并关闭相应能力。超时效力在行动边界求值，读取不物化修复；正常交接与失能恢复各按旧政策执行，后者不要求失能者在线。 |
| 责任、撤权及迟到事实 | [责任规则](../../ai_union/domain/responsibility.py)实际消费 Member/绑定、Work、目标、Charter、政策和至多四层 Mandate 链；行动与接受都核验当前授权。迟到内容为 `not_adopted`、`effect=evidence_only`，不完成 Work。交接保存原 ID 和已交付归属，未完工作进入核对；来源账号丢失不阻止有权主体交接原责任。 |
| 用户入口与能力声明 | 10 种治理命令与 11 种责任命令由同一治理 HTTP 入口消费，React 使用对应命令/回执接口。`kind=local_submission` 与 human Member 的声明一致；模型、真实资源、外部承诺和自主业务仍未启用。注册、当前 AU 权限和历史回执查询没有混为一项权力。 |
| 安装与恢复边界 | [发布器](../../scripts/release_package.py)声明 auth 2/catalog 1、AU schema 1/2，并在代码采用、回滚、启动前检查已登记 V1 AU 的实际 schema/完整性。安装不迁移 AU；升级后有新写入不能以旧身份备份抹去新事实。实际安装验证仍以最终候选及对应日志为准。 |

**证据审查。** 已读回 [Python 全量日志](python-full.txt)中的 `Ran 525 tests` / `OK (skipped=5)`，以及[后端独立报告](review-backend.md)的 75 项通过和已关闭反例；[UI 独立报告](review-ui.md)明确组件反例/控制与实际浏览器证据分开。上述测试由各执行者运行，本次没有重新执行或把日志数量当作新的独立测试结果。相关已跟踪文档的 `git diff --check` 通过。

审阅时 [057 总证据](README.md)仍明确等待最终浏览器、重建安装候选、库外验证及 Git/在线收据；这些进行中项目不被判作文档矛盾，也未在本报告中提前记为通过。仅全部 G01–G10 及必要独立复核完成后，协调者才可按主账流程关闭 U-069。S02/S03、真实业务治理、发布及持续运行继续保留各自授权与证据出口。

**补充核对（2026-11-05）：** 只读复核 [CONSOLE 顶部 V1 使用指南](../../docs/CONSOLE.md#L3)后发现第 3 步将首次采用入口提前写为“AU与治理”，协调者已修正为在“AU准备记录”点击“采用本地治理”、采用后进入“AU与治理”并经本评审读回，第 6 步“迟到内容保留为未采用、工作尚未因此完成”与当前回执文案一致，其余命令、权限和能力说明未发现新增问题，本次未重跑测试或修改其他文件。

**评审权限：** 可继续完成本片剩余验证与交付；本报告不是 U-069 完成、合并、真实数据迁移、模型支出或部署批准。
