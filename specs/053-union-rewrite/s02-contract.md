# S02：核心模型配置、有限授权与真实工具往返

2026-11-06。U-072 / 在线 #21；用户授权完整交付。依据 [PRD](../../docs/PRD.md) F04/F12/F16/F18、[Chapter](../../docs/UNION_CHARTER_v1.0.md) P-07/A-03/K-03/K-04、D-01/D-04/R-01–R-07/X-02(a) 及 ADR-0005/0006。契约不等于已实现；状态只在主账。

## 用户结果

现有 React `/models?organization=<AU>`：保存合法连接 → 明确授权有限调用及只读资料 → 选择一份文本资料发起接入验证 → 看到模型调用工具、实际读取资料、工具结果返回模型后的文字及费用依据 → 可采用连接为默认。保存、测试、采用分别操作；采用不强制收费探测。准备态/失效治理给出具体下一步。

验证拥有真实 Work、责任 Member/绑定、有限 Mandate、`core.model_check` Agent Definition v1 和独立 Execution/attempt。系统完成两次推理和工具接力。责任成员可为发起者对应的人类成员；不将 S05 local_submission 改名成 AI Execution，也不声称已完成 S03 任意目标自主工作或 S04 反馈成果。

首个 profile 为 `openai_compatible` 文本/客户端工具，经固定 modeld/OpenCode 单次流传输；同时支持宿主已授予本 AU 的 `modeld_grant`。其他原生 profile、媒体、托管工具、自动换账号/重试、任意宿主文件/命令及持续运行不启用，由 S09/S03/S06 承接。真实 profile 须单独实际验收。

## 权威、凭据与持久化

- 核心认证绑定稳定 principal；当前有效 AU 治理者配置连接、资源和验证工作，不要求 platform_admin。登录、显示名、宿主访问不产生 AU 权力。
- API Key 只进入 modeld 私有存储。AU 命令保存脱敏参数/摘要，不保存秘密正文；模型、回执、浏览器缓存和公共日志不含 Key。不搜取其他 harness 的认证。
- API 账号与 grant 在 modeld 的同一事务建立，固定原请求、AU、主体、端点、模型；变更端点不得沿用旧秘密。核心用户不能枚举/授予宿主全部账号。预授 `modeld_grant` 仍校验 AU/model/revision/撤销状态。
- GovernanceStore 仍是 AU state/Charter/版本审计/命令回执的唯一写入者。模型领域/应用使用同一 AU 事务；模型适配器只写私有请求正文、资料和工具回执。
- 首次成功的显式模型配置/资源授权，或按旧程序采用含 `read_document` 的章程，将 schema 2 升为 3，保留原创建及 schema 2 审计、责任、回执。新工具不进入 schema 1 的原创建；schema 1 先通过 S05 采用治理。拒绝/失败不初始化模型表或升级，去掉新工具也不降回旧 schema。读取不初始化、不升级、不调用模型。`model_access.resource_grant` 与不可变创建 `resources` 计划分开。
- 保存意图先落 AU，再调用 modeld；两个数据库无全局事务。unknown 查询原 registration/grant，不重复 POST、不删除远端账户假装回滚、不按名称关联、不覆盖已改变的连接。网络等待在认证/AU 事务之外。

## core.models.v1 接口

沿既有认证、同源和 Host/Origin 校验：

| 接口 | 语义 |
| --- | --- |
| `GET /api/v1/models?organization_id=...` | 当前 AU 的连接、资源、验证/attempt、能力及恢复状态；无 Key、native opaque 或宿主路径 |
| `POST /api/v1/models/commands` | `{id, organization_id, base_version, kind, data}`；base_version 为当前 AU 版本 |
| `GET /api/v1/models/receipts?organization_id=...&id=...` | 查原命令；原提交者失去 AU 读取权后仍可查询自己的回执 |

命令回执沿 S05：id/kind/organization_id/base_version/version/actor_principal_id/status/effect/message；外部操作受理成功不代表推理完成，回执附 operation_id/check_id，结果由模型投影提供。格式错误 400、无权 403、同 ID 内容冲突 409、存储暂不可用 503。合法领域/版本拒绝保存原回执。服务不可用不回退 legacy Engine。

| kind | data / 行为 |
| --- | --- |
| `save_connection` | connection_id、expected_revision（新建 0）、name、profile、model、max_output_tokens；API 另有 base_url/api_key，grant 另有 grant_ref/grant_revision。保存不推理、不切默认 |
| `reconcile_connection` | operation_id；只查原注册/grant，当前权威与原预期连接 revision 有效才完成原保存 |
| `set_connection` | connection_id、expected_revision、enabled、make_default；启停增加 revision；默认只采用有效连接；保留旧记录 |
| `grant_model_resources` | max_calls、allow_unknown_cost、reason；不得超过创建计划或低于已用/预约；变更增加 resource revision |
| `start_model_check` | connection_id、expected_revision、binding_id（null 明确由当前治理者本人承担并建立小 AU 绑定）、document_name、document_text；固定两次调用、一个只读工具，不接受宿主路径 |
| `reconcile_model_check` | check_id；核对原 attempt，授权仍有效时可继续尚未派发的下一步，不重发未知 attempt |
| `cancel_model_check` | check_id、reason；停止后续步骤并请求模型服务取消；未决费用保留，不宣称远端取消/退款 |

## 准入、行动和事实采用

1. 当前治理有效，实际治理/后继主体存在；有效 Charter 明确允许 `read_document`。仅 V1 章程扩展此只读工具，legacy 校验/执行不因此接受它。
2. 验证 Work、不可再委托的 Mandate 和 Execution 同事务建立，绑定实际成员、Work/任职/目标/Charter/政策版本、连接/grant revision、resource revision、独立 Agent Definition 版本及指令/工具快照。普通推理不要求组织大 Schema。
3. 有显式有限调用 grant 且接受费用未知，整次验证在 AU 事务预留两次调用。已发出/unknown 的 attempt 不释放占用，失败仅释放尚未派发的后续次数。并发不得超额；每次真实网络尝试独立 request/attempt ID、用途 `connection_check`。
4. 推理派发、工具、第二次推理及结果接受均重验当前授权/必要版本。使用资格和原请求取证分开：撤权后仍核对已发生费用，但不能用迟到内容执行工具或采用结果。
5. 复用 `harness.test_tool_connection` 两阶段协议和 modeld 单次推理，提取共享消息/结果规则；legacy 调用者保留原 Engine 准入。新执行状态持久化，不新建第二套通用 Agent loop。
6. `read_document` 只读取此 Execution 已持久保存且摘要正确的文本；参数 document_id 精确匹配。输出正文、引用、本次校验码。校验码不预先给模型。工具 ID/完整参数/资料摘要/回执同事务保存；事件重放/重启不再次执行工具。
7. 第二轮为完整文字且包含实际工具校验码；仅文本、半个 JSON、未支持的工具/媒体/参数、不读取工具结果均不算通过。native 信息私有保留，按 AU/account/model/version 配对回放，不静默降级。
8. 每 attempt 保存原始用量和归一字段；缺失为 null。费用用明确币种及整数 minor unit 或 unknown；相同结果不重复入账，两次调用不错误合并，累计流用量不与最终量相加。S02 限次数/输出，不承诺供应商未提供的硬金额封顶。
9. 模型检查输出不直接成为 S03 正式业务成果。最近通过绑定具体 connection revision/profile/时间；编辑后旧结论不继续标为当前已验证。失败/unknown 保留 Work、责任、回执，不默认停其他独立工作。

## 恢复与兼容

进入 dispatching 前持久化原意图；进入后 POST 丢失、进程退出、modeld 重启只查原 ID。重启不自动恢复真实调用，页面显示原执行供核对/继续；治理、停用和取消入口仍可用。

modeld 对已完成或迟到结果保留事件、原结果和用量，受信 worker 可按原 AU/request 取证；撤 grant 仍阻止新/queued 派发，Python 决定能否使用结果。取消仅代表本地停止意图，已知用量不能因取消被删掉。

所有结果消费者包括 legacy ModelServiceTransport 必须尊重当前 grant 或明确的 `action_authorized: false`，不能因取证 GET 开放而返回可执行的撤权结果。M06 同时验证有效正常对照与 legacy 撤权反例。

S01 schema 1、S05 schema 2 和 legacy Engine/CLI/runner/模型保持原语义并拒绝 V1。现有候选 manifest 声明 schema 3；旧候选不兼容时采用/回滚/启动前拒绝。不执行真实 AU 迁移、部署、公开发布。

## 严格 TDD 和完整出口

TDD Route: Mode off / Decision strict / Authority explicit user/project request。真实缺口 RED → 最小 GREEN → REFACTOR；保留正确旧测试。

| 用例 | 行为验收 |
| --- | --- |
| M01 身份/配置 | 普通核心治理者保存/重启重开，保存调用 0；陌生主体、跨 AU、错目录、旧版本拒绝且不改目标 |
| M02 凭据/采用 | Key 仅 modeld；同 ID 改 Key/参数冲突；跨 AU/撤销 grant 拒绝；保存、测试、默认分开 |
| M03 保存 unknown | 原意图、远端保存丢回执、本地采用失败/连接已改；仅查原 registration、不重复 POST 或覆盖 |
| M04 责任/资源 | Member/Work/Mandate/定义完整；无 grant/只一额度/未接受未知费用拒绝；并发不超额 |
| M05 往返 | 实际 HTTP/modeld/工具 schema，实际读资料并带校验码回到第二轮，body/usage 可核对 |
| M06 撤权/版本 | 派发/工具/接受处改任职、Mandate、目标、Charter、连接/grant/资源；新动作拒绝，迟到费用仍保留；有效对照通过 |
| M07 原生/能力 | native 和工具配对保真；不支持的 profile/媒体/托管工具/参数明确拒绝 |
| M08 重复/恢复 | 重复命令/事件、迟到、两端重启、取消/查询；每 attempt 至多一次派发、每工具一次执行，unknown 不记零 |
| M09 用户闭环 | 实际浏览器保存→授权→往返→采用→刷新；断网/身份/实例/跨 AU 隔离、输入/焦点、键盘及 320/390/1024/1440 |
| M10 交付 | 固定工具链相关/npm/Python/modeld、实际安装 schema 3 兼容；指定授权 profile 真实往返，独立身份/持久化/费用复核 |

U-072/#21 仅在全部出口及指定真实 profile 通过后以 real 记录。账号/资源未落实时卡片仍未完成；受控测试不能替代真实验收。S03/S04/S06/S08/S09 分别承接任意目标、反馈、持续恢复、发布使用与其他 profile。
