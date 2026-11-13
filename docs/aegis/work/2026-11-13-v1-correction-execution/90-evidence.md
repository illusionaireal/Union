# 当前纠偏候选的证据

- [U-110设计与派单](../../../../evidence/U-110/README.md)：文档独立复核、40条/旅程/链接检查和实际Kanban读回。
- [续审处置](../../../reviews/2026-11-13-v1-correction-followup.md)：偏差、责任、六子卡与父级出口。
- [U-118严格循环](../../../../evidence/U-118/README.md)：有效RED、GREEN、42项定向及源码SHA。
- [协调者验证](../../../../evidence/U-118/coordinator-review.md)：两阶段独立审查，npm363前端完整重跑及Python847项/9跳过；原失败保留。

ADR采用项目原有owner：ADR-0003细化React与界面责任，ADR-0004补当前在线准入及退役边界；PRD/ARCHITECTURE/FRONTEND/DEVELOPMENT/053同步。没有新增另一套ADR或运行态账本。

这是已检查候选的证据，不替代PR/Git交付读回，不宣称U-111或整个V1产品完成。机器路径仅在公开日志中标准化，原始日志字节保存在宿主本地；摘要见evidence/U-118/log-redaction.json。

候选记录已通过 `aegis-workspace.py bundle` 与 `check`；新工作区先执行 helper init 恢复过程目录并补齐本次索引。该结果只证明过程结构。显式 mutateLedger 增加两条 review 交付记录后，management render/check 与37项管理测试通过；既有任务历史、owner和模块成熟度保持。提交前64份任务文件的凭据/私有机器路径检查通过。
