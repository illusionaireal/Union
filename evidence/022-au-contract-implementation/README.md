# 022 AU 契约兼容实现

宿主快照新增au_contract，成员引用带AU域；默认只读投影不迁移旧组织。治理描述仅是显示/追溯元数据，实际authority_source仍legacy_board。新增/更新描述沿用实际board/session、版本与稳定回执，观察者没有内部行动权限。

- [专项](focused-tests.log)：24项契约/生命周期/工作区行为通过。
- [初轮全量](python-tests.log)：182项通过；后续审查修复回归另见下一项，最新联合回归将在023证据保存。
- [审查回归](review-regressions.log)：12项契约及申请验证通过，包括bootstrap伪任职和board Key拒绝前持久化保护。
- [npm](npm-check.log)：管理、旧计划、旧动作与前端检查通过。

[独立权限复核](../../docs/reviews/2026-10-28-au-contract-implementation.md)通过，26项独立专项及创建中断/幂等探测通过。没有真实企业身份集成、公司自主开发或部署验收；没有修改原公司治理描述。远端上传审批阻塞仍保留。
