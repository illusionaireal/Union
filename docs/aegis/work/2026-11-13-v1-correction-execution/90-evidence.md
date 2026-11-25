# 当前纠偏候选的证据

- [U-110设计与派单](../../../../evidence/U-110/README.md)：文档独立复核、40条/旅程/链接检查和实际Kanban读回。
- [续审处置](../../../reviews/2026-11-13-v1-correction-followup.md)：偏差、责任、六子卡与父级出口。
- [U-118严格循环](../../../../evidence/U-118/README.md)：有效RED、GREEN、42项定向及源码SHA。
- [协调者验证](../../../../evidence/U-118/coordinator-review.md)：两阶段独立审查，npm363前端完整重跑及Python847项/9跳过；原失败保留。

ADR采用项目原有owner：ADR-0003细化React与界面责任，ADR-0004补当前在线准入及退役边界；PRD/ARCHITECTURE/FRONTEND/DEVELOPMENT/053同步。没有新增另一套ADR或运行态账本。

这是已检查候选的证据，不替代PR/Git交付读回，不宣称U-111或整个V1产品完成。机器路径仅在公开日志中标准化，原始日志字节保存在宿主本地；摘要见evidence/U-118/log-redaction.json。

候选记录已通过 `aegis-workspace.py bundle` 与 `check`；新工作区先执行 helper init 恢复过程目录并补齐本次索引。该结果只证明过程结构。显式 mutateLedger 增加两条 review 交付记录后，management render/check 与37项管理测试通过；既有任务历史、owner和模块成熟度保持。提交前64份任务文件的凭据/私有机器路径检查通过。

## EvidenceBundleDraft: U-125

- Artifact key: u125-engineering-20261118
- Slice ID: U-125
- Type: controlled
- Source: evidence/U-125/README.md
- Summary: U125完整受控与独立复核通过；用户授权直接更新7756920已实际采用，7项CI全部success，原保护恢复并读回；旧PR及看板失败属历史。U126已认领并完成本机受控验收，远端采用另记。
- Verifier: Codex协调者实测；review_u125与review_u125_restart独立工程复核
- Evidence status: evidence-finalized

## EvidenceBundleDraft: U-126

- Artifact key: u126-engineering-20261124
- Slice ID: U-126
- Type: controlled
- Source: evidence/U-126/verification.json
- Summary: 分开目标段落/可读确认/原请求恢复；三个及四规则RED，长名称浏览器RED后GREEN；npm404、Python863/9跳过、44创建、116入口、独立25与布局通过；远端采用另读在线看板。
- Verifier: Codex协调者本机验收；review_u126独立工程复核
- Evidence status: evidence-finalized

## EvidenceBundleDraft: U-119

- Artifact key: u119-controlled
- Slice ID: U-119
- Type: controlled-engineering
- Source: evidence/U-119/verification.json
- Summary: 严格RED/GREEN、npm412/Python863含9跳过/80五宽浏览器/独立8+76；真实模型0；远端采用另验
- Verifier: coordinator; review_u119 independent engineering
- Evidence status: evidence-finalized

## EvidenceBundleDraft: U-120

- Artifact key: u120-controlled
- Slice ID: U-120
- Type: controlled-engineering
- Source: evidence/U-120/verification.json
- Summary: 严格RED/GREEN；npm425/Python873含7跳过/104五宽浏览器及独立权限复核；真实模型零，远端采用另验
- Verifier: coordinator; review_u120 independent permission engineering
- Evidence status: evidence-finalized
