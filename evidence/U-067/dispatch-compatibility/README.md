# S03 自动派发的发布兼容边界

2026-11-08，实施 actor：codex-home 当前值守会话；在线成员
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`。原 #22 owner DSH 保持。
基线为已合并 PR #17 的 `bbe8068335c32c04bdcf6d4fa20375245b912cf9`；
任务分支 `codex/u067-dispatch-compatibility`，范围与 2–4 小时粒度评估
已在在线 #22 评论 #47 记录。单一结果是安全选择代码版本，不拆分共享
事务和发布门禁，也不修改 DSH 的 PR #22 验收 driver/099/100。

编码前契约：[派发兼容合同](../../../specs/053-union-rewrite/s03-dispatch-compatibility-contract.md)，
决定见 [ADR-0005](../../../docs/decisions/0005-au-runtime-boundaries.md)。
对应 PRD F12/F20，Charter A-04、R-05、K-04、S-03。

## 缺陷与修复

原跨版本反例使用 `39db061` 的自动派发（PR #24，预约语义与基线相同）
和旧 `90d8b1f`：预约仍为 schema 3，当前发布器接受旧候选；旧 Console
成功把持久自动预约手工结算为 released，没有核对原模型请求。原请求
字段仍存在，但不足以阻止旧规则释放占用。原反例与失败日志留在宿主，
没有用删除正常实现制造 RED。

首次显式自动派发/父循环准备，现在在 GovernanceStore 原事务标记
schema 4；预约失败连同版本一起回滚，transport 入口已能读到标记。
治理、责任、模型记录验证继续适用，后续命令不降级。读取、被拒准入
及普通手工工作仍保持旧版本，不迁移真实数据。

发布器按打包目标源码声明 `[1,2,3,4]`，而非使用当前 Python 已导入的
版本。activate/rollback/run 拒绝不能理解自动预约的候选，保留指针、
AU、catalog、原身份和未知请求。对于 PR #17 已写入的 schema 3 自动
记录，新发布器也只读检查并要求候选支持 schema 4。

## 已执行验证

- 首轮 8 项：5 个行为失败、0 errors、1 跳过；版本未标记、旧候选
  未被拒绝均实际复现。第一次 GREEN 尝试仍有 1 failure/2 errors，
  补齐 schema 4 的模型记录校验后通过，原失败历史保留。
- 补充打包反例在固定 `bbe8068` 原发布代码上失败：目标源码支持
  schema 4，归档清单仍声明 `[1,2,3]`。修复后真实临时归档及摘要验证
  通过；更换目标源码可准确声明旧支持范围，并且不执行目标源码。
  构建文件为明确的惰性夹具，不作为可安装产品证据。
- 当前候选与 PR #24 精确 `39db061e307accc7410bee6d71c14756abd43fbd`
  的运行代码和 7 项回执测试组合：55 项，0 failures/errors，1 跳过。
  仅在测试进程装配该代码，没有改动 PR #24 或把它合入本分支。
- 当前候选单独及与 PR #24 组合的原三项独立探针均通过：派发前预约、
  工具正文传递、撤权后计量。
- [跨版本探针](cross-version-probe.py) 使用真实临时 SQLite 和旧运行时。
  旧导出目录的 68 个运行时/发布源码文件逐字节匹配 `90d8b1f`。
  旧运行时读取 schema 4 返回 `incompatible_state`，原数据库不变；
  当前运行时重开原请求仍为 unknown/reserved，0 次重派。

- DTO 消费端复核发现前端只识别 schema 2/3。新增刷新行为测试先
  1 failure/15 passed，实际显示“无 AU 投影”；补齐类型与版本识别后
  通过。保留并扩展 schema 2/3/4 的跨主体、跨服务实例拒绝用例。
- Python 全量：716 项，10 跳过，0 failures/errors，433.509 秒。
  真实模型 opt-in 未启用；完整产品打包检查因本地缺 modeld 构建跳过，
  另有始终执行的真实临时归档/清单测试，不把夹具包当完整产品构建。
- 最终 `npm run check` 通过：80 项交付历史一致性、37 项管理回归、
  9 项 action-safety、212 项前端测试，以及类型检查和正式前端构建。
- 实际 Chrome、HTTP 和 SQLite：从 schema 3 显式准备自动预约到
  schema 4，刷新后同一 AU 与治理页面继续可读，预约仍 reserved。
  详见 [浏览器结果](browser-result.json)。

浏览器的首次扩大探针在等待 AI 工作标题时超时。进一步核对确认
schema 3 和 4 页面都不显示该工作：`Layout` 对核心 `/tasks` 路由呈现
`GovernanceWorkspace` / `ResponsibilityWorkspace`，未挂载原 S03
`WorkPanel`。这不是版本识别修复已完成的产品能力；保留此独立 UI
接入缺口，后续按 S03 修复处理。本次浏览器通过只证明原 AU/治理
读取兼容，不宣称自动工作页面或完整业务验收通过。

复现兼容套件：`python -m unittest tests.test_work_dispatch_compatibility -v`。
复现旧运行时拒绝：先将 `90d8b1f` 的 `ai_union/` 导出到临时目录，
再执行 `python evidence/U-067/dispatch-compatibility/cross-version-probe.py <current-source> <old-source>`。
两个源码目录均不含真实业务数据；模型为替身。

## 采用条件与未完成边界

实施会话的自查不是独立工程复核。候选必须当前 head CI 通过并由前台
另一工程角色复核，重点检查版本标记原子性、旧版本拒绝、治理/模型
校验延续和原未知预约保留。本记录不升级 PR #22 的真实验收结论。

原 schema 3 自动记录必须使用更新后的发布入口；无法追溯修补任意旧
安装器或直接执行的旧二进制。schema 4 后代码回退只能选择兼容候选，
不能声称可回退至任意历史版本。没有 NAS 服务切换、真实业务数据迁移
或新增真实模型调用；完整产品构建/部署、真实业务及持续运行分别验收。
