# 完成声明逐项核对

2026-10-31 02:35–02:45（UTC+8）；检查基线 `dev@ed0d411`。主账43任务，16项done：10项documentation、6项controlled；没有real或sustained完成项。本表核对主账验收范围、实际产物、已有独立复核及当前代码/测试，不能将文件存在自动视为内容真实或重新完成历史业务验收。当前回归结果另见README；历史数量按各时点理解。

| 完成项 | 实际产物或代码依据 | 本轮结论与验证边界 |
| --- | --- | --- |
| U-001 管理基线 | PROJECT/TASKS及2026-10-27-project-baseline记录 | 文档完成；原公司审计基线为10月27日，本轮02:44另做本地数据只读复查，不是生产读取 |
| U-004 首个真实研发任务定义 | specs/020-organization-diagnostics/real-task.md | 输入、成果、反馈和资源门槛已定义；U-006实际交付未执行 |
| U-012 指标口径 | specs/021-work-lifecycle/metrics.md | 口径已定义，缺数据保持unknown；U-020真实采集未验 |
| U-016 管理工具 | scripts/project-management.mjs、tests/project-management.test.mjs、017证据 | 生成、证据路径及管理规则受控验证；不是组织自主采用 |
| U-017 自主改善协议 | management/SELF_IMPROVEMENT.md及评审模板 | 预先评估与人工介入口径具备；U-019真实改善未验 |
| U-018 能力核查 | docs/AU_CAPABILITY_AUDIT.md、scripts/audit_au_capabilities.py及019探测 | 上下文/工具边界有源码与临时Engine探测；不代表模型能主动改善 |
| U-021 同构AU路线 | docs/DEVELOPMENT_ROADMAP.md、018证据 | 规划已保存；旧日期“下一项”须结合当前主账，不算新能力已实现 |
| U-022 核心契约 | specs/019-au-core-contract/spec.md、migration.md、examples.json | 契约交付；实现和权限采用由U-023单列 |
| U-023 兼容投影/治理描述 | ai_union/au_contract.py、tests/test_au_contract.py、022证据和独立复核 | 兼容及现有授权受控验证；不是企业身份集成或多AU成员 |
| U-024 轻量工作组判断 | evidence/026-batch-closeout/decisions.md、能力核查 | 接受“复用现有工作/岗位/依赖”的有条件决定；没有新增工作组对象 |
| U-025 工具服务契约 | specs/024-tool-services-contract/spec.md及024证据 | 契约完成；没有已服务化、采购、付费开通或计费验收 |
| U-027 AU委托契约 | specs/025-au-delegation-contract/spec.md及025证据 | 关系、双边回执与资源边界已定义；跨AU执行/派生未实现 |
| U-033 有界诊断 | ai_union/diagnostics.py、tests/test_diagnostics.py、Harness测试、020独立复核 | 有界脱敏、决策与普通成员资料范围受控验证；真实诊断效果未验 |
| U-034 可选申请 | ai_union/support_requests.py、tests/test_support_requests.py、SDK/Console和023复核 | 申请与受信响应受控验证；同意意向不授予工具/预算，不自动采购 |
| U-035 生命周期 | ai_union/lifecycle.py、tests/test_lifecycle.py及021证据 | 持久时间和旧数据unknown兼容有回归；不是运营成功率 |
| U-040 成员执行/托管计划 | specs/028-member-runtime-management/spec.md、plan.md及028证据 | 计划与验收矩阵完成；U-041未完成、U-042未实现、真实主机待验 |

所有done项的completion.evidence引用均实际存在；权限相关采用记录U-023/U-033/U-034具备既有独立工程复核。当前全量回归验证工程机制，不能独立证明历史供应商事实；历史真实局部证据仍来自014等归档，没有新增公司成员、模型调用或运营成果。

U-037网关是代码已实现、实际浏览器待验；U-039真实New API仍待实际实例/上游授权；U-041观察投影仍有确定性缺口及浏览器门槛。三者未被记为done。G1–G5及其他真实结果阶段仍未accepted；不按16/43计算产品完成度。

本轮只读远端查询：dev `b39c06c76e3b83a6d5413b45f58a9c736e2f15bc`，main `e11c389366814060ea4475a359c9b62036ccd176`。combined-status返回statuses=[]；workflow_runs接口仅覆盖PR触发首批记录且返回[]，不能推断全部Actions不存在或通过。本地7个提交未推送，没有本地新改动的远端CI证据。
