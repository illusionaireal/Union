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

## 2026-11-06 续接：错误、原事件用量与启动恢复

本节在修复前固定原 M02/M08/M09 的字段与行为，不新增通用调度器或后台自动重试。

- `operations[]`、`checks[]` 和 `attempts[]` 可附 `diagnostic: {code, next_step} | null`；原 `message` 是固定或受控领域说明。旧 schema 3 记录缺少该字段时按 null 读取，不作读时迁移。前端显示说明和下一步，不能从错误文本推断远端是否执行。
- 安全分类至少区分 `worker_start_failed`、`model_service_unavailable`、`model_service_authentication_failed`、`provider_authentication_failed`、`model_not_found`、`provider_rate_limited`、`provider_unavailable`、`provider_request_rejected`、`provider_result_unconfirmed`、`authorization_changed`、`invalid_model_result`、`original_request_missing`。modeld 只返回固定错误代码；核心不公开供应商错误正文、HTTP 头、密钥、地址或宿主路径。未知类别降为“结果待核对”，不猜成密钥错误或零费用。
- modeld 的原事件保持 `{request_id, seq, type, payload, created_at}`；Kernel 将所支持协议的已观测用量投影为 `type=usage`，payload 与最终 `result.usage` 使用同一组归一字段。真实 SDK 事件仍称 `native_event`，不把合成投影冒充原生事件。核心按原 attempt 查询、校验并保存递增 seq；相同 seq 不重复采用，内容冲突拒绝。已收集的原事件保存在现有私有 attempt 结果中，正常页只投影归一用量，不暴露原生内容。
- 单次 attempt 内使用最近有效累计用量；最终 `result.usage` 的已知字段优先，不能把流中累计值与最终值相加。字段缺失仍为 null；仅明确币种和整数 minor unit 能形成已知费用，SDK 的无币种浮点 cost 不能推断为金额。用量附 `basis: result | events | unknown` 和 `observed_through_seq`，取消、撤权、中断和重启均保留已经观察到的事实。
- 轮询期间已取得的事实应在继续等待前保存。后续事件查询失败或本地停止时，显示原执行待核对及已知用量；不重新 POST。原结果完整且当前授权有效，才可执行资料工具或采用回应。
- 后台线程创建或启动失败，释放进程内运行登记及未启动线程引用，并把原作业记录为待核对、给出下一步；已经保存的命令回执和原 Work/attempt 标识保留。之后显式核对可继续尚未派发的原验证，重复点击不产生并行派发。正常线程结束仍由原 finally 清理。

用户在本次续接中选择当前 Codex 作为真实验证来源。先核对其已授权连接及协议，再通过同一 S02 模型/工具链取证；独立开发子代理的回复不替代产品验收。若当前连接需要额外协议适配，先冻结最小接口及原生配对要求后实现，不扩大到其他供应商或自主业务。

## 2026-11-06 Codex 所选 Responses 连接：编码前冻结

用户已选择使用本机当前 Codex 连接。只读取该选中配置及对应 API Key，将其通过 modeld 私有管理入口登记为此验收 AU 的固定资源；不扫描其他认证库，不记录真实端点或密钥。当前选择为 `gpt-6-astra`、`wire_api=responses`、`reasoning_effort=max`。真实验收按已提出的两次推理、每次最多 512 输出 tokens 执行；不自动重试，供应商没有报告的金额保持 unknown，不声称有硬金额封顶。

- modeld 的 API registration 可显式增加 `wire_api: chat_completions | responses`；仅 Responses 可增加 `reasoning_effort: none | minimal | low | medium | high | xhigh | max`。旧请求不含新字段，仍严格表示原 Chat Completions 行为；不得按地址、模型名或失败结果切换协议。协议和设置进入原 registration 摘要，同 ID 修改任何设置返回 409。
- 原 API 账号、grant 和摘要仍由 Journal 同一事务拥有。旧记录/回执的字节语义及字段保持；新显式设置保存在该行的 nullable `options` JSON，原记录不重写。首次成功的显式协议登记才在同一事务增加列并将 modeld SQLite `user_version` 从 0 升至 1；拒绝、读取、启动和失败事务不升级。版本 1 不降回 0。代码可读 0/1，未知版本启动拒绝，先检查再恢复请求。
- 受支持发布器的 manifest 声明 `modeld_schemas=[0,1]`。未声明的旧候选仅支持 0；安装采用、启动和回退前只读检查 modeld 私有库版本。已有版本 1 时拒绝旧候选并保留代码指针、身份、grant、未决请求和费用，不自动迁移或降级。直接绕过受支持发布器运行任意旧代码不属于此保证。此次只在隔离验收目录使用新登记，不迁移真实业务数据。
- modeld 对 Responses 登记回执明确返回 `profile=openai_responses` 及显式设置；旧 Chat 回执形状保持。核心沿现有 `modeld_grant` 保存精确 grant/model/revision，页面无需新增通用协议配置表单；直接填写 API 的既有 profile 继续表示 Chat Completions。
- Kernel 通过固定 SDK 的 `openai.configure(...).responses(model_id)`、显式 `providerOptions.reasoningEffort` 进入原 `inferStream`，保留原生 reasoning/encrypted/tool item 与工具回执配对。一个 attempt 只派发一个 HTTP 流，无第二套 Agent loop、协议 fallback 或自动重试。原 account/AU/model/upstream 绑定不改变。
- 原生用量与安全错误沿本节前的共同归一合同。供应商明确的 401/403、404、429 和 5xx 分别投影为固定诊断代码；派发后失败仍不推断远端零费用。`requested_model` 与未证实的 `actual_model` 分开。

验证同时包含旧 Chat/Go 正常对照、协议/设置冲突、版本 0/1 重开与回退阻断、真实 SDK Responses 回环两阶段和不重试、保密/原生/用量/授权反例，以及最终安装后的用户指定真实连接。合同冻结不代表这些出口已经通过。

## 2026-11-06 工程取证与剩余出口

实现、严格 TDD、独立复核、实际浏览器及隔离安装结果见 [058](../../evidence/058-s02-model-tools/README.md)。所选 Codex 连接只派发一次请求即被拒绝认证；无可采用回答、无资料工具执行，原未知用量和请求在重启后保持。直连与宿主代理的只读认证检查均为 HTTP 401。M10 成功真实往返尚未通过，本段不改变 M01–M10 或降低整卡验收条件；修复连接及新增有界调用授权后继续，不重放原 unknown attempt。

## 2026-11-06 用户改选真实验收资源

用户针对上述续接条件提供了本机兼容 API 及 `group/deepseek-v4.1-flash-free` 模型，作为剩余 M10 的新选定资源。沿已提出的两次推理、每次最多 512 输出 tokens、费用缺失保持 unknown 的范围执行。复用现有 `openai_compatible` / Chat Completions，不更改产品协议或增加回退；端点和凭据只留宿主私有配置。此前 Codex 请求及其身份、责任、用量、资源占用和失败证据继续保留，不能把新连接成功改写为旧连接通过。

原私有验收脚本未保存临时核心账号的登录或恢复秘密，因此不伪造该主体会话、不重置其 AU。新一轮通过正常注册和创建接口建立明确命名的验收 AU，目标与证据引用原失败 AU；同时核对原事实不变及两轮总请求数。该测试主体仅承担此次接入检查，不属于业务迁移或新增自主业务。此资源选择不降低原 M01–M10 出口，也不验收其他 profile 或持续运行。
