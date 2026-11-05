# S05：有效治理、撤权与责任交接契约

日期：2026-11-05。依据为 Main Chapter V1 D-04/C-02/X-02(a)、PRD F01/F03/F07/F09/F20、ADR-0005/0006 和本目录 S05；用户已授权完整 U-069 / 在线 #24。此处冻结编码契约，完成状态和证据以主账为准。

## 1. 用户结果与能力边界

核心账户能够准备并采用可执行的本地治理程序，查看初始根、当前治理者、最终决定方、保留事项、失能程序和生效期限。当前治理者按旧有效规则修订；另一核心账户自行确认接班。一个或多个明确的人类责任成员可承担内部记录工作，授予有限授权、再委托、提交内容、采用及交接同一 Work。正常与被撤销的行为经过同一生产命令边界。

本片 profile 为 `local_governance.v1`：单一当前治理者兼最终决定方，支持预先采用的超时继任或超时退出。单主体可选退出，不强制增加第二成员。人类 Member、登录 principal、责任绑定和本地提交尝试分别记录；本片不创建 AI Execution，不伪造 Agent Definition。未来 AI Execution 必须由 S03 绑定实际定义版本。

`local_governance` 激活只允许明确的内部 `record_memory` 行动。`autonomous_business`、真实资源使用、模型/工具派发及外部承诺仍为 false；启用这些能力仍需 S02/S03 及各自适用资源授权。服务端拒绝其请求，不仅在 UI 隐藏。现有五字段 Charter 中本片只执行 `board_can_amend`、`record_memory` 的允许/撤销及结构校验；其他操作/工具尚未激活，自然语言正文不隐式授权。

## 2. 身份、当前权威与兼容

- Identity 仍是唯一认证所有者。`POST /api/auth/register` 在已设置宿主账户后登记普通核心参与者，参数与 setup 相同；独立密码、恢复码与随机稳定 principal。普通账户 role 为 `core`，legacy 范围为空，platform_admin 为 false。注册不授予任何 AU 权限。
- 初始 owner 保留原 legacy 权限；auth schema 2 区分 `account_kind=owner|core`。只能有一个 owner，username/principal 唯一。正常登录、改密及找回密码保留 principal。
- 原 auth 0/1 必须在服务停止后用既有升级器显式升级；记录输入版本、备份和收据。所有旧会话失效，原 principal、创建 payload/receipt 保留。回退只允许升级后尚未写入；返回实际输入 schema。不得在读取或启动时升级旧库。
- `reset_owner` 只删除 owner 及其会话；普通参与者不受影响。新 owner principal 不接管旧 AU。
- auth schema 2 同时保存逐账号登录失败窗口；一个参与者成功登录/恢复只清除自己的窗口，不能重置另一个账号的失败次数。全局限流继续保留。owner 重置只清理 owner 对应窗口。
- AU `governance_root` 始终表示不可变创建者/初始治理者；当前权威为 `governance.current_principal_id`。Catalog 只定位，当前治理者、有效责任成员、被提名接收者、指定恢复主体按 AU 当前记录取得必要读取权。撤销后不因原 creator 再获读取权。
- 创建回执始终只属于原 creator；治理命令回执只属于原提交 principal，即使其后来失去 AU 权限仍可查询自己的原回执。宿主 ticket、同名新账户和 platform_admin 不替代任何核心主体。
- legacy Engine/CLI/runner/workspace/model-service 的所有既有 profile 隔离继续拒绝 V1，包括已经激活本地治理的 AU。保留 S01 全部正确回归。

## 3. 采用、事务与持久事实

S01 的 schema 1 准备态仍按原契约创建和只读重开。只有成功的显式 `adopt_governance` 命令可将该 AU 升至 schema 2；先用原创建意图完整校验目录、身份、正文、资源及采用记录，再开始 AU 的写事务。首次采用要求初始治理者及旧 Charter 的 `board_can_amend=true`，不得用新规则授权自身采用。已通过身份、支持范围及输入校验的初次命令若因旧规则或版本拒绝，仍在 schema 1 保存 `governance_commands` 中的原拒绝回执；AU 状态、原 Charter 和创建采用记录不变。读取验证这些可选回执但不建表、不升级；同 ID 改内容不能利用拒绝后重试重新采用。

`governance_origin` 原样保留初始 state/Charter 字节；原 `creation_adoptions`、初始 Charter、catalog payload/receipt 不改。schema 2 当前 state 与每次成功命令对应的版本化审计快照可靠关联，连续版本/摘要链及最终快照与当前内容必须一致；不可将任意修改后的 state 当作有效治理。验证是本地完整性检查，不声称能抵御有权修改整个数据库及程序的宿主。

一个 AU SQLite 事务同时保存当前状态、Charter 新版本、采用依据、授权/责任处置、审计和命令回执。失败不得留下半生效权限。普通身份登记先在 catalog 完成；AU 采用时在保持认证数据库事务期间重验账户和目标主体存在，不宣称跨数据库全局提交。所有新身份/路径必须在 AU 写入前检查。

命令请求形状：`{id, organization_id, base_version, kind, data}`。请求 ID 为有界标识，base_version 为当前非负整数。接口为 `POST /api/v1/governance/commands`，查询为 `GET /api/v1/governance/receipts?organization_id=…&id=…`。成功或有权请求的规则拒绝保存原回执；不支持/格式/无权请求不得获取他人的内容。查原 ID 先核对原提交主体，再比较完整 payload；相同请求只返回原回执，不重验旧规则、不重复采用。相同 ID 不同 payload 为 `id_conflict`。

新命令版本冲突为拒绝回执，保留输入，读回后由用户决定新请求。I/O/连接不确定为 `storage_unavailable`；客户端保存原 ID，仅查询，不自动重发。当前状态/当前权限与 receipt 历史是两种读取。所有错误不含宿主路径或凭据。

## 4. 本地治理程序

治理配置由以下受支持字段组成：

```text
profile: local_governance.v1
final_decision_principal_id: 当前治理者的稳定 principal
reserved_matters: [charter, goal, resources, appointments, mandates, dissolution]
unavailability:
  mode: successor_after_timeout | exit_after_timeout
  timeout_seconds: 整数 60..2678400
  successor_principal_id: 已登记的其他 principal（仅 successor 模式）
```

上述保留事项全部属于当前治理者；少项、未知项、重复项、未知程序/字段/布尔伪整数均拒绝。未来多人治理/任意条款语言另行 profile，不以兼容字段猜测。

| 命令 | 采用依据及持久结果 |
| --- | --- |
| `adopt_governance` | schema 1 的受信初始主体按旧规则采用配置；schema 2/本地治理 prepared，尚未激活 |
| `configure_governance` | 当前治理者且旧 Charter 允许修订；替换配置并提高 policy_version，撤销旧恢复确认/提名，回到 prepared |
| `acknowledge_recovery` | 被指定后继者自行确认当前 policy_version；只接受恢复职责，不立即取得普通治理权 |
| `activate_governance` | 当前治理者、完整有效配置、后继确认（适用时）；置 active 并持久化服务器期限；保持业务自治/资源未启用 |
| `renew_governance` | 有效期限内当前治理者显式续期；不在浏览/一般操作时偷偷续期 |
| `nominate_governor` | 当前有效治理者指定另一已登记主体及依据；提名绑定当前 policy_version，可取消或替换 |
| `accept_governance` | 当前被提名人自行确认，提名和旧政策仍有效；切换 current/final，撤销提名/恢复确认、提高 policy_version，回到 prepared，由新治理者确认后续可执行程序 |
| `recover_governance` | 预先确认的后继主体、原有效期限已过、程序/政策未变化；按已采用程序接班，不要求失能者在线批准；原根不变，旧授权版本失效，回到 prepared |
| `exit_governance` | 当前治理者可主动退出；或任何已有读取权的主体在 `exit_after_timeout` 期限到达后将旧规则决定的退出落账；无新治理权 |
| `amend_charter` | 当前治理者及旧 `board_can_amend` 允许；完整校验新五字段及依据，新增 Charter 版本并提高 policy_version；新文本不能自授权 |
| `set_goal` | 当前治理者更新目标及依据，增加 goal_version；旧目标下的尝试不能被采用 |

到期检查在每个行动和接受边界即时求值，不依赖后台调度或物化状态。退出模式到期后不能续期/恢复为 active，等待落账期间同样拒绝业务；继任模式到期后仅允许已指定恢复或退出。读操作只展示有效状态和期限，不做写修复。失能/退出保留原 Work、责任主体、未知/在途尝试和已采用内容，不声称远程取消。S06 未来可调用同一受控用例落账，不拥有另一套规则。

激活、续期、行动和结果采用均重新验证当前治理者及适用后继账号仍存在。schema 2 投影的 `readiness_gaps` 明示缺失主体；原 active 配置不可用时显示 `governance_status=unavailable` 并关闭本地提交能力。仍具治理权的主体可显式重新配置或退出，不把只读投影当作修复。

## 5. 小 AU 责任用例与撤权

责任用例仅为真实内部文字记录，所有调用显式触发，不自动形成组织、运行模型或调度循环。

| 命令 | 输入要点与受控结果 |
| --- | --- |
| `appoint` | 当前治理者登记 `member_id/principal_id/name` 和独立 `binding_id/duty`；成员为 human；绑定带版本/active，未自动授予 Work 权限 |
| `update_appointment` | 当前治理者修改具名职责并增加绑定版本；原绑定版本上的授权/尝试需重新授予 |
| `create_work` | 当前治理者给有效责任绑定创建 `work_id/title/instruction`；保存责任/版本/历史，初始 open |
| `update_work` | 当前治理者修改标题/指令或 open/stopped 及依据；增加 Work 版本，停止与范围变化约束下一动作/接受 |
| `grant_mandate` | 当前治理者给同一 Work 的有效绑定授予 `record_memory`；或受权成员以有效 parent_mandate 再委托；范围不得扩大、最多四层，父级允许再委托，所有祖先/任职版本持续有效 |
| `revoke_mandate` | 当前治理者撤销具名授权及依据；该授权和所有后代的新动作、已发出的尝试提交/接受均失效；不阻塞其他 Work 的有效授权 |
| `handoff_responsibility` | 当前治理者从旧绑定交到另一个有效绑定，保存依据/历史；旧绑定失效，所有未完成 Work 沿原 ID 改责任并升版本，旧尝试保留但不采用；已交付历史归属不改 |
| `begin_local_action` | 当前 actor 对应有效 Member/绑定/完整 Mandate 链、Work、Charter、policy、goal、期限；持久化本地 attempt 与这些版本，不产生外部副作用 |
| `submit_local_result` | 原 attempt actor 提交有界文字；存内容摘要、原尝试及当前授权判断。撤权/过期/旧范围的迟到内容仅保存为 not_adopted，回执 rejected，不能改变 Work/已采用成果 |
| `accept_local_result` | 当前治理者再次校验原尝试全部有效身份/版本/授权链；原 Work 必须仍 open。将 submitted 内容采用为持久内部结果并完成同一 Work；无权或过期拒绝，原内容保留 |

每个本地尝试携带 AU、Member、principal、binding/version、Work/version、Mandate 祖先链及版本、goal_version、charter_version、policy_version，明确 `kind=local_submission`，不是 AI Execution。治理者与 Member 的角色独立；移交治理不自动抹去其单独的成员职责，交接职责通过独立命令完成。

## 6. 用户界面与生产者/消费者

沿用 React 工作台，普通登录提供“登记核心参与者”，明确此举不取得任何 AU 权。治理页面区分初始根与当前治理者，展示实际能力、保留事项、期限、失能程序和原回执。按当前主体只显示其可用准备、确认、修订、续期、继任、退出及本地责任操作。目标 ID 由已知记录选择，确需输入 principal 时提供当前账号标识，姓名不能替代 UUID。

表单保持输入/焦点，提交前预览关键变更及旧版本；拒绝、失联、unknown、stale 和恢复查询显示在原表单。预检重新核对 principal、服务实例和 AU；身份变化/取消预检阻止 POST，迟到响应不能影响其他账户/AU。unknown 保留原 kind/ID，只提供查询；回执必须匹配原请求。当前用户失权时清除旧 AU 投影而保留本人可查的原回执。

验收含正常单主体准备/激活/文字提交/采用、第二主体自确认交接、旧主体拒绝、浏览器刷新/服务重启、320/390/1024/1440 和键盘。页面展示受控内部记录，不称其为 AI 自主业务成果。

## 7. 成对验收与执行顺序

| 编号 | 必须观察的行为 / 反例 |
| --- | --- |
| G01 | 普通核心参与者独立登录/恢复、无 legacy/platform/AU 权；owner 重置不删他人、不接管旧 AU；auth 0/1 显式升级/回退/失败不丢身份 |
| G02 | 合法首次采用和启用成功；缺最终方/保留事项/失能程序、未知规则、未确认后继拒绝；schema 1 读取/创建不升级 |
| G03 | 旧有效程序允许的修订改变同一行动；旧禁止新允许的自授权拒绝；原创建字节/ID/回执和所有 Charter 历史保留 |
| G04 | 正常提名/对方确认、超时受信继任/单主体超时退出；伪造/同名/宿主/过期提名拒绝；原治理权不复活、重启同一主体/责任 |
| G05 | 本地 Work→授权→尝试→内容→采用成功；无授权/跨 AU/旧 Member/绑定/目标/范围/停止/Charter/policy/期限拒绝；迟到不采用 |
| G06 | 有限 A→B→C 再委托成功且不扩权；撤父级/旧任职使 C 的新动作与旧结果采用失败，无关 Work 仍继续 |
| G07 | 原 Work 和必要内容沿责任交接继续；旧绑定失效、未完/在途/已完成历史保留；新责任明确获权后继续 |
| G08 | AU 采用/修订/交接任一步数据库故障无半状态；原请求去重、冲突、响应丢失按原 ID 恢复；当前访问和原回执权限分离 |
| G09 | schema/安装候选检查阻止旧代码打开已采用治理的库；原 identity/S01/legacy profile 行为保持；读取不迁移 |
| G10 | 实际浏览器用户闭环、权限/unknown/乱序/重启/小屏/键盘；固定工具链全量、独立身份/持久化/撤权复核 |

先 G01 的真实 RED→最小 GREEN，再 G02–G04、G05–G08 各行为 RED→GREEN→REFACTOR；共享事务/Schema 顺序集成。界面在冻结类型后可独立实施。已有正确测试不删改为制造 RED。最终 npm run check、Python unittest discover -v、相关安装/实际浏览器检查、Aegis bundle/check；仅完整受控工程和独立复核通过后关闭 U-069，真实业务中的治理另取证。
