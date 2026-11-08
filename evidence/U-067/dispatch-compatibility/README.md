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

## 2026-11-08 完整安装包补验

上述缺少 modeld 构建的本地限制已补验，产品源码仍为 PR #25 的精确
`ede96fa519a32b22d278b7717931926c8e49aef6`。使用锁定 Node 24.19.0、
Bun 1.4.2、Python 依赖和 OpenCode `805a42f` 完成构建，归档 93 个文件，
声明 `source_state: committed`、AU schemas `[1,2,3,4]`。保留包 SHA-256：
`a254d7ac70501c04d9ae7e724f7be396e13716cbba74e9c32c2fb2b9feb1ebfd`。
ZIP 和原日志留在本机，仓库只保存可复现探针及脱敏结果。

- [modeld 安装结果](modeld-install-result.json)：复制后的完整构建可独立
  启动/重启，第二进程不能占用同一状态，固定上游及许可随包交付，4 项通过。
- [完整安装结果](installed-release-result.json)：真实 Python/React/modeld
  包在全新目录安装并启动两个服务；同源码两个版本名的采用与代码回退保留
  测试登录、最新测试数据及私有令牌，5 项通过。这不是历史版本的数据兼容结论。
- [安装后预约探针](installed-package-probe.py) 与
  [结果](installed-dispatch-result.json)：子进程确认产品模块来自安装目录，
  使用实际依赖预检和安装后的 CLI；普通 schema 3 先允许选择，显式预约后
  schema 4 使不兼容的 activate/rollback/run 均拒绝，数据库/catalog/指针
  字节不变。兼容候选重新选择后，同一身份/原请求经 HTTP 返回 unknown，
  原预约保留，0 次重派，安装目录仍通过摘要验证。
  负例使用相同可执行文件、刻意仅声明 schema 1–3 的清单，测试发布门禁；
  不冒充历史可执行版本。旧 `90d8b1f` 执行拒绝仍以此前跨版本探针为证。
- 原全量中的 `test_built_candidate_declares_durable_dispatch_support` 现在
  实际执行通过，不再因缺构建而跳过。此前 716 项/10 跳过的全量历史保留；
  本次未重跑已通过的其余 Python 用例，没有把新结果改写为一次新全量。

首次构建在全历史克隆上因 Git 默认把 diff 索引缩写到 10 位、锁定补丁为
7 位而停止；仅在构建进程设置 `core.abbrev=7` 后，原完整补丁比对通过，
没有放宽校验或改宿主/系统配置。首次安装预约探针将 attempt 建在停服前，
新服务实例正常拒绝派发；改为停服/选择完成后创建 attempt，探针通过。
这些环境/夹具失败的原日志保留，不算产品 RED 或新增产品修复。

复现：先按 `ops/release/README.md` 构建及 pack，再运行
`python -B evidence/U-067/dispatch-compatibility/installed-package-probe.py --archive <zip> --bun <bun-1.4.2> --output <result.json>`。
同源码安装脚本为 `scripts/check_release_install.py`，modeld 安装脚本为
`scripts/check_model_service_install.py`；全部只使用临时数据和模型替身。
本次 0 次真实推理、0 个真实账号、无 NAS 切换或业务数据迁移。候选独立
工程复核仍待前台完成；补验和原 head 的 14/14 CI 不代替新 head 检查。
