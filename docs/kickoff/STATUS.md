# UNION 启动状态

更新：2026-10-10。阶段：M0 准备/预验证。工程执行者：本轮编码 Agent；实际 E1/E2/O 人选、验收人和投入尚未确认，不折算为新增全职产能。

## 本轮已完成的具体工作

- 核对并初始化用户指定的 GitHub 仓库；保持其原有 public 可见性。
- 保存五份 UNION-B1 原文快照及 SHA-256 校验；不覆盖 Library 原文件。
- 建立 82 个唯一任务的机器可读目录及 181 条依赖检查，未发现缺失节点、有向环或本期依赖延期项。
- 编写 PLAN-001 范围稿和 ADR-0001，记录当前 Mock 范围及生产验证缺口。
- 实现离线动作安全预验证，9 项本地测试通过。证据与限制见 [VALIDATION.md](VALIDATION.md)。
- 建立 Ubuntu/Windows CI 工作流与 PR 模板；远程运行结果见 GitHub Actions，未通过前不计为远程验收。
- 首批 8 个 GitHub Issues 已建立；其余 74 项保留在任务目录，未批量创建远程 Issue。

这些是准备成果，不将任何 PLAN/ENG/OPS 的完整验收标准提前打勾。资金与权限实验仍需另一工程角色复核后采用；M0 尚未通过，不开始生产经营。

## 首批任务

| ID | GitHub | 当前状态 | 本轮成果 / 剩余条件 |
| --- | --- | --- | --- |
| PLAN-001 | [#1](https://github.com/illusionaireal/Union/issues/1) | 准备中 | 范围稿；业务能力与供应商可用性待验证 |
| PLAN-002 | [#2](https://github.com/illusionaireal/Union/issues/2) | 准备中 | 离线动作协议测试；PostgreSQL/Temporal/沙箱/模型及接口待验证 |
| PLAN-003 | [#3](https://github.com/illusionaireal/Union/issues/3) | 准备中 | 完整目录与依赖检查；任务系统分阶段导入及实际接口核对待完成 |
| PLAN-004 | [#4](https://github.com/illusionaireal/Union/issues/4) | 等待前置 | 基线已有门槛；当前版本证据与验收人待落实 |
| PLAN-005 | [#5](https://github.com/illusionaireal/Union/issues/5) | 等待前置 | 资源预算模板；真实人选、工时、预算和日期待填写 |
| PLAN-006 | [#6](https://github.com/illusionaireal/Union/issues/6) | 等待前置 | 原始基线存档；执行基线未冻结 |
| OPS-014 | [#7](https://github.com/illusionaireal/Union/issues/7) | 准备中 | 仓库已初始化；维护责任、恢复和治理待验收 |
| OPS-016 | [#8](https://github.com/illusionaireal/Union/issues/8) | 等待前置 | 许可/贡献权利和正式公开范围待决；未默认添加开源许可证 |

## 下一步顺序

1. 审阅本轮范围与预验证结果，完成金额/权限实现的另一工程角色复核。
2. 在相同测试场景下接入 PostgreSQL 和 Temporal，锁定实际版本并做 Worker 重启、服务失联、外部动作查询恢复及两租户隔离测试。
3. 检验一个模型接口、一个允许的渠道及一个产品模板。任何付费调用前必须有已确认的成本上限。
4. 明确人力与预算，按真实容量完成 PLAN-005/006，再推进 ENG-001–008。

候选 T0=2026-10-12、D90=2027-01-09 保持原文，不等于已承诺。真实客户付款 G2 与真实投资募集 G3 独立准备。

## 状态来源

原始任务状态在 baseline/ 和 tasks.json 中为归档时状态；执行进展以本文件与 GitHub Issues 为准。没有关闭完整任务；没有真实订单、收入、客户交付或投资权益。
