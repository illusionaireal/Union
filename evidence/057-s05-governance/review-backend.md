# S05 后端独立工程复核

复核日期：2026-11-05。最终实现快照记录时间：2026-11-05T12:29:13Z。

**结论：本次后端范围内没有未关闭的 P1/P2 发现。** 初次检查发现的 1 项 P1、6 项 P2 均已在规则或存储所有者处修复；最终独立运行 75 项相关测试全部通过。可继续进行切片集成验收。本意见不授予 U-069 完成、合并、发布、迁移真实数据或启动业务的权限。

## 范围与依据

- 复核者：独立工程角色 `s05_code_review`；未实现修复，未操作 Git、主账或在线卡片，只按协调者后续授权写入本报告。
- Git 范围：working-tree；base/实际 HEAD 为 `d9ff5ad23201ee0813707a00f65a0b0d9012a3ee`，分支 `rewrite/charter-v1`，head 为下方哈希记录的工作区实现。
- 需求权威：[Main Chapter V1](../../docs/UNION_CHARTER_v1.0.md) D-04、C-02、X-02(a)，[PRD](../../docs/PRD.md) F07/F09/F20，[ADR-0005](../../docs/decisions/0005-au-runtime-boundaries.md)、[ADR-0006](../../docs/decisions/0006-charter-policy-adoption.md) S05 编码前细化，[S05 契约](../../specs/053-union-rewrite/s05-contract.md)及 [plan §9](../../specs/053-union-rewrite/plan.md)。同时核对当前术语、S01 契约及实际模块 AGENTS。
- 实现范围：Identity/身份升级，creation 的授权定位调整，governance 应用与存储，纯治理和责任规则，Console/HTTP 装配，owner 重置和发布器兼容检查；相应身份、创建及 `test_governance*.py` 测试。
- 不包含前端实现/浏览器验收，以及任务开始前已有的根 AGENTS、`.gitignore`、`package.json`、管理脚本/README、子模块和其他历史文件变化。

术语与边界保持一致：初始治理根不等于当前治理者；Member 不等于登录 principal；本地人类提交不等于 AI Execution。未观察到本片开启模型派发、资源使用、外部承诺或业务自治。

## 发现与闭合证据

以下均为 **Implementation Drift**，不以扩大产品范围或改写需求来消除反例。

| 优先级 / 范围 | 实测反例及影响 | 修复所有者与最终证据 | 状态 |
| --- | --- | --- | --- |
| P1 / both | 首个 `appoint` 的 `member_id=null` 获得 200/succeeded，随后 AU 读取变成 409/incompatible_state；JSON 将字典键变为字符串，破坏持久身份。 | [应用输入校验](../../ai_union/application/governance.py#L79)仅允许明确可空的 `parent_id`；[存储边界](../../ai_union/adapters/governance_store.py#L117)重验状态及序列化一致性。`test_nonnullable_object_ids_are_rejected_before_any_persistent_change` 通过；复核者另用全新、成员为空的 AU 重跑原反例：400/invalid_request、AU 无写入、读取仍为 200。合法空 parent 根授权继续成功。 | 已关闭 |
| P2 / both | 有效 Member 被提名为治理者后，同一有效授权的新行动由成功变成 403；successor 与 nominee 重合时恢复入口也可能被遮蔽。 | [治理规则](../../ai_union/domain/governance.py#L76)把显示角色与独立成员资格分开，[责任规则](../../ai_union/domain/responsibility.py#L43)组合权限。`test_governance_nomination_does_not_replace_an_independent_member_mandate` 和 `test_successor_member_and_nominee_rights_compose_without_shadowing` 通过，包含超时恢复可见性及实际接班。 | 已关闭 |
| P2 / both | 第二次修章后单独篡改历史 Charter，或修改原命令 reason，当前读取仍成功；原请求重放反而产生 id_conflict。 | [完整性验证](../../ai_union/adapters/governance_store.py#L27)校验完整原请求/回执摘要，将命令摘要关联审计，并逐条核对历史 Charter 与采用快照。`test_historical_charter_corruption_is_rejected_even_after_a_later_amendment`、`test_command_payload_and_receipt_corruption_are_detected_before_read_or_replay` 通过；合法修订、原回执与去重回归保留。 | 已关闭 |
| P2 / both | 原 owner 已将治理交给另一账户；其账户随后被 reset 删除，新治理者却因旧主体不能认证而无法交接原 Work。 | [责任交接](../../ai_union/domain/responsibility.py#L168)验证原责任记录及有效目标，不要求离任来源账户继续存在。`test_handoff_of_outstanding_responsibility_does_not_require_the_lost_subject_account` 与正常交接/已交付归属保留测试通过。目标身份和新行动校验仍保留。 | 已关闭 |
| P2 / requirements | 7 次错误 owner 登录后，普通参与者合法登录清掉全局失败计数；第 8 次 owner 猜测重新从 1 计数，可反复绕过原保护。 | [Identity](../../ai_union/identity.py#L135)增加按规范化用户名的失败桶，同时保留全局桶；其他账户成功不清除目标账户失败。`test_other_account_login_cannot_clear_target_account_failure_throttle` 和 `test_successful_login_clears_only_its_own_failed_attempts` 通过。新增表纳入 schema 校验、写入版本及显式升级；owner 重置按用户名清理该表。 | 已关闭 |
| P2 / both | 指定后继者确认后，其 owner 账户被删除；当前核心治理者仍可激活一个已没有可认证后继者的程序。 | [有效目标规则](../../ai_union/domain/governance.py#L151)在激活、续期及本地行动/接受边界重验；[只读投影](../../ai_union/application/governance.py#L26)说明实际缺口并保留修复入口。`test_activation_revalidates_the_preconfirmed_successor_account` 和 `test_lost_successor_identity_blocks_actions_until_current_governor_reconfigures` 通过；当前治理者明确改为可用退出程序后仍能激活。 | 已关闭 |
| P2 / both | schema 1 首次采用的版本冲突不保存拒绝回执；查询原 ID 为 403，改 payload 后复用该 ID 却成功。 | [应用顺序](../../ai_union/application/governance.py#L70)和[单一回执所有者](../../ai_union/adapters/governance_store.py#L83)为明确、已授权但被规则拒绝的请求保存回执，不采用 schema 2。`test_initial_version_rejection_retains_original_receipt_without_adopting_schema_two` 通过。复核者另验证旧 Charter 禁止采用的情形：原 state/schema 保持不变，重启后可查同一拒绝回执，原请求重放返回相同回执。 | 已关闭 |

中间修复曾出现 `appointment` 辅助函数被同名局部变量遮蔽，导致两项交接 HTTP 断开。该问题已通过 `active_appointment` 命名修正；下面的最终独立测试包含这两项并全部通过。早期名称含 `green` 的中间日志不能代替最终结果。

## 最终独立验证

在 Windows/PowerShell 中使用项目 `.venv`，执行：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m unittest tests.test_core_participants tests.test_identity tests.test_identity_upgrade tests.test_identity_release tests.test_core_creation tests.test_governance tests.test_governance_succession tests.test_governance_responsibility tests.test_governance_persistence tests.test_governance_release -q
```

实际终端结果：

```text
Ran 75 tests in 72.948s

OK
exit_code: 0
```

这组测试覆盖稳定身份/独立账户、旧身份显式升级和回退、S01 创建/重开、旧规则修订、可信接班与超时退出、授权祖先/任职/Work/目标/Charter/policy 的变化、提交与采用两边界、保留迟到事实、责任交接、数据库失败回滚、原 ID 查询/冲突、当前访问与原提交者回执分离，以及安装选择时的 AU schema 门禁。

复核者还执行了独立临时 HTTP/SQLite 探针，未新增测试源码或修改实际服务数据：

| 探针 | 实际结果 |
| --- | --- |
| 普通核心账户创建自己的 AU 后找回密码 | 200；principal 不变、role=core、platform_admin=false；旧会话 401，自己的 AU 200，无关 owner AU 403。 |
| 修复后的空成员 AU 接收 null Member ID | 400/invalid_request；数据库逻辑内容不变；AU 仍可读。 |
| 初始旧 Charter 禁止修订时尝试采用新治理 | 持久 rejected；schema 仍为 1、初始 state 不变；服务重启后查询 200，原请求重放回执一致。 |

协调者的 [52 项最终选定回归](green-backend-reviewed.txt)提供旁证；本报告的最终判断使用上述独立 75 项及原反例复跑。前期缺口记录见 [历史完整性 RED](red-g08.txt)、[角色/交接 RED](red-review-roles.txt)、[身份 RED](red-review-identity.txt)、[初始回执 RED](red-review-initial-receipt.txt)、[空标识 RED](red-review-null-identifiers.txt)。

## 架构与兼容判断

当前 AU 的权威来自经过原创建连续性与审计验证的 AU 状态。Catalog 的原 creator 仅保留原创建回执归属，已经退出当前治理授权判断。原创建 payload/receipt、初始 root 和 Charter 保持独立；治理移交不会恢复原创建者的普通权限。

治理和责任规则不依赖 SQLite、HTTP、Harness 或平台账户。当前状态、Charter 版本、审计与命令回执由同一治理存储事务采用；身份数据库事务覆盖目标身份重验，但没有声称跨库全局提交。读取不迁移，unknown 不自动重派，旧 Engine/CLI/runner 入口仍拒绝 V1。

未发现需要另增事实所有者、兼容 fallback 或新 ADR 才能解释的后端实现方向。保留 legacy profile 是已声明的兼容范围；本片没有把它变成新 AU 的治理定义。

## 尚未覆盖的证据与残余风险

- 本次不包含 G10 前端、实际浏览器、键盘/小屏、预检取消或乱序响应复核。API 行为通过不代表用户闭环已经完成。
- 发布器的实际 schema 门禁已独立运行，但 `test_governance_release` 使用受控候选及替换的依赖 preflight。完整打包、安装后真实模块导入和运行路径由协调者继续验证；不能从这三项门禁测试推断真实安装包已经可用。工作区新模块还需进入精确的发行输入。
- 本次未运行全仓 `npm run check`、Python 全量 discover、Aegis 检查或真实服务/宿主/模型验收；最终切片交付仍需协调者执行相应门槛。
- 完整性验证是本地损坏/不一致检测，不抵御同时改写数据库、摘要链及程序的宿主。只读检查与临时故障注入不证明真实治理或持续运行。

后端受控工程复核置信度：**B**。已检查范围中的已知 P1/P2 均闭合；上述跨界证据不由本报告替代。后续若修改下列实现，应核对差异并重验受影响范围。

## 最终实现快照 SHA-256

```text
ai_union/identity.py aabaf2d035815a46f0fd09de5f08801764c9959109294c1f8edf25ec914c412b
ai_union/identity_schema.py 95d67de1ddeea9d4378304fb0ff7cd891af40fa36ddfad7811bc7aa8a82d152a
ai_union/application/creation.py 4ecc3f7c1bc7c6e45b89f1271b68e28e1353cda56863423c1a426973d8e72273
ai_union/application/governance.py 7f19d9c204ae3930960fc9fed8b02464221cb976e80e9685fb23f0d949879a78
ai_union/adapters/creation_catalog.py 13f28e48f5cdaca1629178e3d558183c922d1f359a3923ae47b2c84e2bf4d072
ai_union/adapters/core_au_store.py 06bd46f8c8e0b44dcc853bbebe2f2e67329fc6255fc0dac74aac6ee1bc17f0a8
ai_union/adapters/governance_store.py 2c7bb2de065dae08d73f6088aef6759bee3aae301c05a4dea16b9fd3990507c6
ai_union/domain/governance.py e35ccdaf144e15e3169e2d96fbd93e9f22d6ce5aa4360bc335ef261659f841da
ai_union/domain/responsibility.py ff9c3c99530d1a66e5a97a392843969a24c0178d34f3ca9f75c9e63b258cba36
ai_union/console.py 2752043f09b110537d80747c7b96c1a7c616e3a2bac3149c2fa73bf4e3c6a602
ai_union/server.py 02ce6713e29e0a5dcf80ca48b88120998c4de5adfbf8fb7d8ecb414b5a993a1c
scripts/reset_owner.py 3f9733564f2dae722210f3998b3bec3310deb5cd0ebe2e515f67525145493fb7
scripts/release_package.py 0f7fc6cd7634699e2c0693fd7594eebd49894bb6d0b75e06f340f99729dd6dbd
```
