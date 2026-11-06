# 053：Chapter V1 垂直切片与验收

本文件只定义范围、依赖和实施顺序，当前任务状态以[主账](../../management/project.json)为准。[PRD v1.0](../../docs/PRD.md)与[40条追踪](charter-traceability.md)是需求输入；在线12张V1卡通过[Kanban映射](../../management/KANBAN.md)关联同一U任务。用户要求撤下的18张旧建议卡已归档，不再参与活动看板或新切片依赖。

## 1. 需求覆盖与主账

| 切片 | 需求与条款重点 | 正式任务 / 验收边界 |
| --- | --- | --- |
| S00 | N01；全部40条覆盖及X-02(e) | U-065；文档/契约/Git交接 |
| S01 | F01/F03/F09/F11/P15/F17；D-01/A-01/A-04/R-01/R-02/X-02(a) | U-066；准备态与兼容，不关闭自治/发布 |
| S02 | F04/F12/F16/F18；P-07/A-03/K-03/K-04 | U-072；本片受控调用及选定profile真实往返分别取证 |
| S03 | F02/F03/F04/F06/F10/F18；P-02/P-04/P-05/P-08/D-01/D-02/R-07/R-08 | U-067；单Agent真实交付与需要时的团队依赖分别验证 |
| S04 | F03/F05/F06/F10/F11/P15；D-03/K-01/R-02 | U-068；真实成果、反馈和第二次交付 |
| S05 | F01/F03/F07/F09/F20；D-04/C-02/X-02(a) | U-069；完整受控治理工程在业务前；真实治理/交接另验 |
| S06 | F04/F06/F08/F11/F12/F20；R-01–R-08 | U-070；受控恢复和指定真实窗口分别取证 |
| S07 | F10/F11/F18/F19/F22；P-06/P-08/S-01/S-02/S-04/X-01/X-02(d) | U-073；授权内试用、真实效果与保留/撤回 |
| S08 | F17/F20/N05；P-07/S-03 | U-074；独立安装、维护与持续使用 |
| S09 | F04/F10/F12/F16；A-03/R-06/K-02–K-04 | U-075；逐profile声明范围与真实证据 |
| S10 | F07/F12/F20/F21/F22；C-01–C-05/D-05 | U-076；双AU承诺、递归与重组分阶段真实验收 |
| S11 | F17/F22/P15/N04；P-07/A-01/A-04/K-03/X-01 | U-071；核心与可选平台/外部管理的公开接入 |

F11/P15及N02/N03/N04适用于所有涉及界面、授权、状态和恢复的切片，不是最后一片补齐。P13已退役，P14小说基准独立保留；两个成员是团队场景，不是AU普遍资格。

上述12个任务直接拥有V1需求和验收，只依赖这批切片。下文提到的旧spec、U编号、源码或测试只供查找可复用实现和历史差距；旧公司、供应商、主机排期不成为新需求前置，也不以旧任务的完成状态代替V1验收。

## 2. 共同实施协议

认领前核对主账、在线负责人/version、实际HEAD和既有修改。每片先固定用户结果、DTO、身份/版本、错误、事务/副作用/恢复、兼容和退役，再选具体文件并同步必要AGENTS。使用严格TDD，有意义RED→最小GREEN→REFACTOR；现有正确行为先保留回归。

旧调用者、新所有者和生产者/消费者成对核查；共享Schema和事务顺序集成。每片包含必要的UI/API/应用/持久化/测试，不先按横向技术层开一堆脱节任务。权限/费用采用独立复核，真实模型/主机按现有授权和有限资源另验。

## S00：统一规范、架构与下一实施契约

- 用户结果：下一开发者从main V1出发，不需要猜章程来源或沿用旧产品定义。
- 文件：PRD、ARCHITECTURE、ADR-0004/0005/0006、053目录、当前AGENTS/入口、Kanban映射及管理记录。
- 验收：main原文字节/40条/子条款覆盖、冲突处置、S01精确契约、独立审阅、检查、提交推送；[spec](spec.md) C01–C07。没有运行时代码。

## S01：核心身份下创建治理明确的AU并重开

- 用户结果：核心登录→准备目标/治理根/Charter/资源计划→创建准备态AU→刷新/重启后重新打开同一组织；旧记录及回执保留。
- 顺序：先旧创建/回执/目录完整性，再稳定core principal及显式身份升级，最后V1创建/读取和准备态防绕过。具体DTO、函数、错误、事务和验收以[s01-contract](s01-contract.md)为准；内部第一步只是部分交付，不关闭U-066。
- 落点：`identity.py`、`console.py`、`server.py`、`engine.py`及实际迁出的创建/治理所有者；React `features/commands`、身份入口与API类型；局部AGENTS随真实模块建立。
- RED：错误目录映射、同ID改内容、伪造principal、重建同名账户冒领旧AU、跨AU、写入中断、登记失败后的原回执、prepared状态通过legacy入口启动/写入。有效原请求和已有旧行为保持成功。
- 验证：`test_console`、`test_mechanisms`、`test_au_contract`、`test_http`、`test_identity_http`及新增有意义principal/治理行为；实际浏览器创建/刷新/登录重开/保留输入/明确准备态。
- 出口：全S01契约通过，未绑定/未激活不启动业务；不宣称完整F09、真实筹建或V1发布已完成。
- 实施证据：[056](../../evidence/056-s01-core-creation/README.md)映射完整 T01–T12，原 S01a 保留在 055；任务完成状态与下一认领仍以主账为准。

## S02：合法模型配置到一次真实受控调用

精确请求、权限、存储、恢复与 M01–M10 验收以 [S02 契约](s02-contract.md)为准，执行顺序见 [plan §10](plan.md#10-2026-11-06完整-s02-模型与只读资料往返)。含指定真实 profile 出口，不能只以 controlled 关闭本卡。

用户先看 [U-072 操作说明](../../TASKS.md#u-072)。开发者的准确函数/组件、接口输入输出、完整流程与技术验收在本文件的 [U-072 开发附录](#u-072-development)，当前任务状态仍由唯一主账生成。[架构](../../docs/ARCHITECTURE.md#execution-contracts)明确当前有限验证与后续通用执行链。[058 工程验收](../../evidence/058-s02-model-tools/README.md)记录凭据、诊断、用量、启动恢复、浏览器及安装结果；所选 Codex 连接认证失败，成功真实往返仍未完成。此前 [设计核查](../../evidence/058-s02-model-tools/design-readback.md)保留其历史缺口。

- 用户结果：独立核心可配置合法模型/工具，保存/测试/采用和实际调用状态清楚；可选平台增强不成为必经前置。
- 复用：048、U-060/U-062，`model_api.py`、`model_service.py`、`subscriptions.py`、`harness.py`、`services/modeld/`和React模型页。modeld grant/revision仍是其授权边界。
- 正式任务U-072；前置为U-066和U-069整卡完成。配置与调用共同验收，发生真实AU调用前具备S05适用治理与资源条件；仅保存配置不调用模型。
- RED：失效grant、连接revision改变、同名跨AU、原生工具/流能力不足、重复请求/迟到；不得静默降级或第二遍执行工具。
- 验证：`test_model_service`、`test_model_api`、`test_role_binding`、`test_model_routing_integration`及相关模型浏览器；在本片证据记录实际往返与用途/费用来源，048仅作实现核查参考。

## S03：单Agent或团队承担责任并完成有依据的工作

- 用户结果：按目标建立最小适当结构，形成有责任与授权的真实工作；单Agent不被迫造第二成员，需要协作时成员能使用依赖成果。
- 前置：S01、S02调用契约及U-069完整受控治理工程。主账依赖整卡完成，不以S05内部一部分通过代替。旧成员形成机制复用；单成员合法性需要行为改动时先RED，不删除原两成员回归。
- 落点：拟新增 `application/work.py:WorkService`、`application/runtime.py:CoreRuntime` 和 V1 Work/AI Member/Definition 规则；从 `harness.py:HarnessExecutor` 提取可注入 SDK 驱动，从 S02 提取单次调用所有者。旧 `Engine`、`agent_protocol`、`runner` 作为迁出案例/兼容实现，不能直接作为 V1 准入。完整处置及 I/O 见 [模块表](../../docs/ARCHITECTURE.md#module-changes)。
- RED：无责任成员/Work/Mandate/定义版本的执行、失效身份、跨AU引用、无效草案、未授权工具、并发共享环境冲突。目标/结构探索有目的和成本；普通推理不被组织Schema束缚。
- 验证：`test_harness`、`test_agent_conversation`、`test_au_contract`、`test_workspace_harness`、`test_console`及实际工作台；单Agent真实交付与两成员真实依赖分别记录。

后续设计按下列可演示功能展开，开工前冻结契约，不改变当前主账依赖或认领：

| 子功能 | 入口与代码工作 | 完成后可操作的结果 |
| --- | --- | --- |
| S03.1 提交目标并承担工作 | 总览新增目标/资料/限额表单→`WorkService.command(start_work)`；同 AU 事务采用 AI Member/Definition/绑定、Work/Mandate 和意图；简单工作不用多造成员 | 选择一个 AU，输入目标后得到 work_id；工作页显示负责成员、有效授权、所用模型和待执行状态 |
| S03.2 Agent 使用授权资料 | 新 Runtime 选择工作→注入 Harness 的 infer/invoke_tool；宿主登记只读 root 引用、AU 范围授权、`list_documents/read_document`；step_ref/attempt/工具回执持久配对 | Agent 列出并实际读取授权目录资料，范围外路径/junction 拒绝；每次模型/工具结果可追踪，不借用 S02 的 connection_check 授权 |
| S03.3 首份成果可读且完成可核对 | Harness 返回候选→Runtime 重验→内容可靠保存后同 AU 登记/采用；复用 React Tasks/Artifacts，新增 V1 读取与摘要校验 | 用户能打开/下载带来源的项目概览，刷新仍在；不是只看到“已完成”文字。需要团队时下游实际使用已采用上游成果 |
| S03.4 局部隔离与原步骤继续 | 按 Work/写目标互斥，保留原 attempt；SDK checkpoint 落后按核心 cursor/step_ref 恢复，不新发原步骤 | A 终态 unknown 时有独立资源的 B 可继续；共享模型槽位不足时显示具体等待。永不返回请求下的有界并发和真实窗口由 S06 验收 |

只读目录是未来资料工具的具体方案，S02 上传/粘贴文本不能替代该演示。新存储/schema/工具范围与业务资源授权需随 S03 契约固定，当前不创建空模块或登记真实宿主目录。

## S04：正式成果、反馈与事实纠正产生下一次改变

- 用户结果：读到可校验成果，给出反馈，组织采用后续决定并完成变化；重大知识纠正有处置记录。
- 落点：沿 S03 的 WorkService/CoreRuntime、正式成果和 V1 投影，新增 `append_feedback/adopt_feedback` 与知识纠正；React Artifacts/Activity/Tasks 增加反馈/版本对比。旧 `engine.py`/`runner.py` 和020只作为迁出及历史用例，不让 V1 绕回旧写入者。
- RED：缺失/篡改成果、只自述完成、无来源反馈、重复事件、采用失败仍消费、纠正后旧结论继续指导依赖工作；不把所有已完成成果全局作废。
- 验证：`test_mechanisms`、`test_integration`、`test_http`、`test_diagnostics`和浏览器下载/反馈/后续回执；本片真实成果diff、质量和第二次交付另验。

| 子功能 | 准备写的完整链路 | 完成演示 |
| --- | --- | --- |
| S04.1 针对成果反馈 | 成果页提交 event_id/artifact_id/version/正文→持久事件及原回执；输入可在长工作运行中接收 | 刷新后反馈仍与原版本对应，重复提交不生成两份事件，收到不冒称已采用 |
| S04.2 采用反馈并交付第二版 | 采用决定、事件消费、后续 Work/执行意图同 AU 事务→原 Runtime/Harness→新成果 | 对第一版给一条具体修改意见，实际生成第二版；界面能比较变化、来源、质量和成本，不以“反馈已记录”结束 |
| S04.3 纠正已使用事实 | 知识引用记录依赖→受权纠正→只重开受影响 Work 并保存处置决定 | 错误资料被更正后，相应交付被修订，无关成果不全局作废 |

S03 已须交可读首份成果，S04 在此基础上实现反馈闭环；本表是未来功能拆分，未认领或实现。

## S05：治理准备、有效修订与责任交接

- 用户结果：知道谁有权决定、何时可启用资源和业务、失能如何处理；按旧有效程序修订并改变后续行为，交接不中断责任。
- 顺序：S01后完成适用的最终决定方/保留事项/失能恢复或退出、激活、修章、撤权和任职交接的受控工程；使用明确测试组织核验完整U-069，再开放S02/U-072和U-067。真实治理/交接等待V1实际工作后另取证，不能制造U-067与U-069依赖环。
- 落点：ADR-0006、治理/授权应用和规则所有者，`engine.py`/`workspace.py`的行动和接受点，工作包/授权版本、React准备/设置/成员/回执。
- RED：未绑定/失能无处置却激活、仅新文本自授权、未知规则假生效、旧任职/目标/范围撤销后仍行动、再委托不撤销、同名账户越权、部分采用失败。资源/承诺/长期运行义务不因分期略去。
- 验证：`test_mechanisms`、`test_au_contract`、工作区/身份/命令及迁移行为测试；独立权限复核。旧profile只按声明兼容，完整F09和真实治理分别验收。
- 具体生产命令、主体/版本、schema 与 G01–G10 见 [S05 契约](s05-contract.md)，实施与独立复核见 [057](../../evidence/057-s05-governance/README.md)。本地人类内部记录是受控撤权/交接用例，AI Execution、真实模型资源和实际业务治理保持各自后续出口。

## S06：局部恢复、持续监督与有目的的唤醒

- 用户结果：一个工作受阻时独立工作继续；重启后责任、等待和资源不丢；未知动作可核对，主动观察有依据。
- 落点：扩展 S03 CoreRuntime 的原执行/等待/资源记录；新增受限外部监督适配，修改 `services/modeld/src/server.ts:pump` 的容量选择及 Journal 队列状态；React 执行/资源/关注事项展示。旧 runner/lifecycle/failures 与028/048是案例输入，不复制成第二个 V1 调度器；现有心跳不是外部监督已实现的证据。
- RED：崩溃在提交与派发之间、重复/迟到回执、过期执行所有权、无关unknown阻塞独立工作、长作业丢新输入、统一短超时误杀、分层重试多次启动、共享环境冲突、资源变化未处理在途工作。
- 验证：`test_failures`、`test_lifecycle`、`test_runtime_http`、`test_dispatch_observation`、`test_model_service`及计量；监督在执行之外、受限权限和审计记录有反例；本片指定真实窗口另验。
- 观察仍遵守既有受限元数据边界，扩大资料面前核对能力审计；实现限制不是永久产品定义。

| 子功能 | 具体改变 | 完成演示 |
| --- | --- | --- |
| S06.1 独立工作继续 | Runtime 原 Work/环境占用与 modeld 有界请求槽位分别准入；按账号/连接公平选队，页面显示等待资源 | A 请求永不返回，独立槽位的 B 仍交付；同一写目标仍互斥，治理/停止/新输入入口保持响应 |
| S06.2 重启和未知核对 | Runtime 续期/到期处理、原 request 查询、采用待办与持久唤醒；不把超时等同远端未执行 | 提交后/派发后/结果保存后分别中断，重启按原步骤恢复，未知不重放、费用及责任不丢 |
| S06.3 长任务和有目的唤醒 | 输入事件、wait 对象/责任/唤醒条件/退避同源保存；独立受限监督只发可审计恢复/升级命令 | 长工作运行中收到新输入；条件达到后推进；没有目的/额度时不空转；受监督 Agent 不能改删监督记录 |
| S06.4 实际治理修订/撤权/交接窗口 | 在 S05 既有有效治理边界上检查 S03 AI 执行的行动和采用资格，保留原未完责任 | 真正工作进行中撤权或交接，旧执行不能继续行动/采用，新责任者能核对并接续；与普通故障分开取证 |

以上承接既有 F08/F20 与计划中的真实治理出口；在线/主账 U-070 尚需在其开工前按同一范围细化，不把本次文档更新当作未来卡已获授权或真实验收完成。

## S07：授权内改善工作并验证效果

- 用户结果：从实际效果发现问题，低影响可直接试用或按权限采用高影响改变；能够保留/撤回并解释证据，必要时申请或替换工具。
- 正式任务U-073；复用`support_requests.py`、`diagnostics.py`和[SELF_IMPROVEMENT](../../management/SELF_IMPROVEMENT.md)的适用机制。已有协议与V1冲突时以V1更新，外部工程代写不算自主改进。
- RED/验收：试用许可不等于有效；可区分实施/评估职责但不强制新增Agent；需要独立判断而条件不足保持候选；候选改评分/评级/删失败拒绝。重要改变有窗口/停止、总目标/成本评估并承担原责任；分类记录人工介入及涉及人的数据保护。
- 测试按实际机制选择`test_support_requests`、`test_diagnostics`等；真实问题→改变→前后结果另验。付费采购/支付另行授权。

## S08：交付独立、可维护的候选核心

- 用户结果：在无私有平台账户、仓库凭据、许可证服务环境中构建、安装、登录、连接模型工具并完成持续工作；升级/回滚/恢复可操作。
- 正式任务U-074；复用052和`ops/release/`，不建立第二套发布器。明确构建、环境、数据样本、预算、观察窗口和维护责任；不继承旧机器或公司排期。
- RED：缺依赖/私有服务被禁、损坏包、不兼容Schema、旧数据/身份错配、未知执行、迁移中断、被更新执行自改监督/升级、新旧双派发；不可逆改变有明确边界。
- 验证：`test_release_package`及干净环境实际构建/启动/备份恢复/已知可用版本；真实模型工具成果、反馈、局部故障、重启与持续运行分别记录；许可证和公开发布另定。

## S09：逐profile兑现原生模型能力

- 用户结果：所声明profile真实完成配置/认证、工具、原生内容/流式、续接与正确用途计量。
- 正式任务U-075，每个profile是完整独立切片，复用031/048的适用能力；不把API、订阅、网关、自托管、云身份统一压成一种兼容协议。
- 落点：模型服务及配置/媒体/上下文/费用适配、React能力声明。
- RED/验证：原生签名/加密项、工具配对、长上下文引用、刷新冲突、取消/恢复不支持、误去重与迟到；`test_model_protocols`、`test_model_context`、`test_model_media`、`test_model_billing`、`test_model_portability`、`test_model_service`及各profile真实往返。一个成功不外推全部支持。

## S10：两个AU履行承诺，并逐步支持递归与重组

- 用户结果：合作方经同构公开契约接受/履行/验收交付，组合AU对外保持同一契约；复杂能力按声明启用。
- 正式任务U-076，直接依据C-01–C-05分步完成双AU承诺→递归派生→责任/成员交接→拆分/合并/归属/退出；前置为S04/S05/S06/S11。旧U-028–U-031仅提供历史实现和差距参考，不继承其排期或完成状态。
- 落点：019公开投影与025委托契约、关系/承诺应用所有者、资源/撤权/事件协议、React协作与关注事项；数据结构在每段开工前冻结。
- RED：发送即当接受、争议静默履约、协作关系授治理权、子AU修章扩权、撤权无反馈、无限离线却承诺即时撤权、嵌套复制余额、失联丢责任、重组遗留访问权、重复派生/交付。
- 验证：同一合同测试运行于叶子/组合AU；授权投影含承诺、撤权范围、用量、unknown/partial而不泄内部会话；双边真实成果和失效/恢复/争议分别记录；平台或消息队列本身不赋予权限。

## S11：外部管理通过公开契约使用核心

- 用户结果：核心用户可直接使用；可选平台或管理工具通过同一版本化契约完成创建/查询/受控操作，不需要内部表或Python私有模块。
- 正式任务U-071，直接拥有P-07/A-04公开契约验收；从S01接口开始设计，在S03基本工作契约具备后整体交付，依赖U-066/U-067。其他用例逐一纳入，不为同一职责建立重复所有者。
- 落点：核心HTTP/应用/权限/审计边界、平台调用者、React API类型与契约测试；基础认证属于核心，商业客户/套餐/账单属于平台。
- RED：移除私有平台依赖后核心功能失效、客户端绕表/内部模块、平台身份代替AU权、协议/持久化/配置版本混用、观察泄露未授权资料。
- 验证：独立客户端黑盒合同测试、合法/越权/版本/重试/审计成对结果、当前React回归；旧调用者重绑后退出直接依赖，每个保留适配说明退役条件。

## 开发细节与完整验收依据

卡片正面先说明完成后能做什么、具体操作和演示；这里保留改写前的完整技术验收内容，供实现和复核使用。卡片和本附录共同约束交付，改写没有删除权限、恢复、兼容、真实验证等要求。

来源为提交 4c49d5d 的主账。以下包含当时的实现状态和证据说明，当前状态仍以 management/project.json 为准；不得把历史段落中的进展当成最新完成结论。详细源码与接口继续沿用现有架构及各片契约。

<a id="u-065-development"></a>

### U-065 开发说明

按用户指定的Main Chapter V1重建053 S00：固定原文/采用依据，覆盖40条及X子条款，纠正旧PRD/AGENTS冲突，重建PRD、架构/ADR、垂直切片；归档移出旧18张在线建议卡，建立12张V1卡且仅依赖新切片。固定S01三步整体的legacy完整性、稳定principal、治理根准备态及旧入口隔离/回执/迁移/TDD。独立评审、文档/管理/npm/Python检查及提交推送有证据；本卡范围为documentation，不实现运行时或升级真实能力。

<a id="u-066-development"></a>

### U-066 开发说明

按053 S01及Main V1，用严格TDD顺序完成S01a旧创建/原回执/目录完整性、S01b稳定core principal与显式身份/catalog升级及V1治理根准备态创建、S01c旧入口隔离与React/HTTP重开。三步全部通过才完成；保留legacy原请求/版本/unknown，不迁移旧AU、不借同名账号重置接管；prepared+resources planned无业务/资源副作用。精确DTO/错误/事务/兼容/T01–T12见s01-contract.md，权限和迁移独立复核；不关闭自治/完整F09/真实发布。

<a id="u-069-development"></a>

### U-069 开发说明

直接依据Main Chapter V1 D-04/C-02/X-02(a)、053 S05与ADR-0006，在S01后完整交付受控治理工程：初始根及适用最终决定方/保留事项/失能继任恢复退出、激活条件、旧程序修章、撤权传播、任职交接和历史连续。严格TDD覆盖未绑定/失能缺处置却启用、新文本自授权、旧身份/目标/范围失效、未知规则假生效及迁移失败；权限独立复核。全卡受控工程完成后U-067才可开工；真实工作中的治理修订/交接另取证，不与U-067构成互为前置。legacy_board只是明确兼容profile。

<a id="u-072-development"></a>

### U-072 开发说明

依据 Main Chapter V1、PRD F04/F12/F16/F18 和 [S02 契约](../../specs/053-union-rewrite/s02-contract.md)。依赖 U-066/U-069；在线 #21。原整卡目标及 M01–M10 保留，本次把开发内容展开为可实现、可演示的样板。状态以主账为准；本卡尚未完成。

### 1. 功能行为

| 功能 | 用户操作与系统响应 | 当前实现 / 剩余工作 |
| --- | --- | --- |
| 保存模型连接 | 核心账号进入 `/models?organization=<AU>`，输入名称、API 地址、Key、model、输出上限，预览后提交；保存成功后刷新仍在，推理次数为 0 | 工作树已接通异步保存和原回执；特殊字符 Key 的保密反例尚未修复 |
| 采用连接和启停 | 独立点击“设为默认”；采用不强制测试、不增加模型调用。停用/编辑后 revision 改变，旧验证不继续标为当前有效 | 工作树已有；默认绑定保存在本 AU。任意业务执行使用默认属于 U-067，不能据此声称已接通 |
| 授予有限调用 | 有效治理者在模型页授予有限次数并接受费用可能未知；不超过创建资源计划。没有足够的两次额度时拒绝整次验证 | 工作树已有资源 grant、预约和逐次计量；modeld 的 AU grant/revision 仍单独校验 |
| 授权和选择资料 | 在 AU 设置按有效程序允许 `read_document`，模型页选择一份文本或粘贴正文；后端只允许读取本次保存的资料 | 当前为 txt/md/csv/json 的单份提交文本，含摘要与校验码；不是宿主目录授权。用户示例中的目录登记、列目录和越界防护拟在 U-067 首份工作接入，明确未实现 |
| 验证真实工具往返 | 点击“验证工具往返”，建立本 AU 的责任 Member/绑定、Work、Mandate、固定 Definition v1；模型提出读资料，核心实际读取，再把原工具回执交回模型 | 工作树已有两次推理编排及完整工具配对；输出含实际工具校验码才通过。指定真实 profile 尚未验收；不算任意目标或正式业务成果 |
| 看到具体失败 | 有效连接成功；错误 Key、不存在的模型、网络失败分别显示脱敏分类、失败阶段和允许的下一步 | 目前多处归为通用 failed/unknown，缺分类 DTO、后端映射和页面展示；未知结果必须保留“核对原请求”，不能引导重发 |
| 查看结果、恢复原执行 | 页面展示输出、资料来源、两条 attempt、原始用量的安全摘要、费用来源/未知原因；刷新不丢失，核对原 ID，停止不声称远端已取消 | 正常结果已有；中断事件用量尚未完整进入核心投影，线程启动失败后原 check 的同进程恢复有缺陷；完整浏览器和安装出口待补 |

### 2. 代码变更

以下“已有”均指 `c31bf0e` 上的未提交 S02 工作树，不是已交付代码。HEAD 已有的身份、S01/S05、HTTP client、legacy Harness 和 modeld 单次推理继续复用。新代码的输入输出以第 3 节为准。

| 具体落点 | 已有可复用 / 已写代码 | 准备修改或新增 |
| --- | --- | --- |
| `web/console/src/pages/Models.tsx:Models`；`features/models/CoreModels.tsx:{CoreModels,ModelWorkspace}` | 既有路由；工作树按核心身份/AU 分流，保留原 legacy 模型入口 | 保持身份、AU、服务实例切换清理；完成真实浏览器切换/撤权反例 |
| `features/models/{ModelFields,ModelCommandForm,ModelPreview,useModels,requests,api,types}` | 新表单、预览、命令、4 秒只读轮询、原请求核对；Key 不入缓存 | 新增诊断与用量来源 DTO/状态；恢复动作按结果确定性显示，POST 不自动重试 |
| `features/models/ModelRecords.tsx:{ConnectionRecords,OperationRecords,CheckRecords}`；`models.css` / `workspace.css` | 连接默认/版本、异步操作、执行结果及逐次用量 | 展示错误类别和已观测用量/缺失原因；修复 1440px 状态文字可读性，再覆盖四宽度、键盘与焦点 |
| `ai_union/server.py:Handler.handle_api`；`console.py:Console.__init__` | 模型 GET、commands、receipts 窄接口与 ModelAccessService 装配，复用正常核心登录 | 只接新增 DTO/状态，业务规则不堆入 Console；V1 不调用 legacy start |
| `application/model_access.py:ModelAccessService.{command,save_connection,check_grant,spawn,read}` | 脱敏意图先落 AU、后台注册、当前授权、原保存核对 | 修 JSON 转义 Key 检查；`spawn` 启动抛错时清理未运行登记，保留持久意图，显式核对可恢复且正常同 key 不双启动；保存错误分类 |
| `domain/model_access.py:{validate_input,apply,occupied_calls}`；`domain/model_checks.py:{prepare,authority}` | 连接/资源 revision、明确两次额度、责任绑定、行动和结果接受处重验 | 保留纯规则所有者；诊断/用量新增字段先细化契约和状态验证，不放宽 legacy 或准备态权限 |
| `application/model_checks.py:ModelCheckRunner.{run,reserve,collect,observe,accept}`、`usage_from` | 两阶段、独立 attempt ID、先记模型事实/用量后重验采用资格 | 从原请求事件读取已观测用量，按 sequence/最终值去重并标明是否完整；保留 unknown 预约；映射脱敏错误、恢复原阶段 |
| `adapters/model_access_store.py:{reserve,observe,tool_result,tool_message,validate}`；`governance_store.py:{transaction,save}` | 前者写同 AU 的私有请求/资料/工具回执；后者唯一写 state/Charter/审计/命令回执 | 持久化安全的用量来源和诊断证据，完整性检查随字段更新；不新增第二账本、不读取时迁移 |
| `model_service.py:ModelServiceClient.call`；`tool_roundtrip.py:{complete_tool_call,complete_reply}` | 回环 HTTP 客户端和有界消息校验；旧 `harness.test_tool_connection` 复用后者 | Client 保留允许的下游错误码和阶段，不透传原始供应商正文；S02 继续不构造 `ModelServiceTransport`/Engine |
| `services/modeld/src/api-accounts.ts:validateAPIRegistration`；`journal.ts:Journal.{registerAPI,apiConnection,event}` | API 账号/grant 同库事务、原注册/请求和事件 | 公共字段按实际字符串检查 Key，覆盖引号/反斜杠；保存诊断/用量事实与公共安全投影分开 |
| `services/modeld/src/kernel.ts:Kernel.{inferAPI,inferStream}`；`server.ts:startService` 内 `pump` | 固定 SDK 单次流；组织工具留在核心；当前全服务串行 | 修输入、输出、工具参数和跨流分片 Key 泄露；分片未证明安全前不发布，完整性与用量不能丢；新增认证/模型/网络错误分类。并发槽位属于 U-070 |
| `tests/test_core_model*.py`、modeld `test/{api-connections,api-kernel,late-results}`、models 组件测试、`scripts/s02-models-browser.cjs`、发布检查 | 已有 Python/组件/HTTP 回环/schema 测试与部分浏览器脚本 | 先将已复现缺口变成有意义 RED，再最小修复；扩充现有浏览器脚本尾段/切换场景，实际安装最终候选并从安装目录运行；原正常对照和历史证据保留 |

编码前补入现有 S02 契约的具体字段：拟新增 `diagnostic={code,stage,recovery}`（`authentication_failed/model_not_found/network_unavailable/result_unconfirmed` 等白名单）；`recovery` 区分修正配置、核对原请求和检查授权。拟新增 `usage.observation={kind,sequence,complete,missing_reason}`，保留现有 `usage.source` 语义；有最终量采用最终量，只有事件累计量时不与最终量相加，缺失为 null。这些是待实现设计，不是当前 API 能力。

### 3. 完整流程与接口输入输出

运行进程与业务接缝见 [架构部署图](../../docs/ARCHITECTURE.md#runtime-deployment)和[接口表](../../docs/ARCHITECTURE.md#execution-contracts)。S02 不调用 `runner.step` 或 `HarnessExecutor.execute`。

| 边界 | 输入 | 输出 / 状态 |
| --- | --- | --- |
| 模型页读取 | `GET /api/v1/models?organization_id=<AU>`，会话 Cookie | `core.models.v1`、version、access、connections、resources、operations、checks；无 Key/宿主路径/native 私密正文 |
| 模型页命令 | `POST /api/v1/models/commands`：`{id,organization_id,base_version,kind,data}` | HTTP 200 `{receipt}`；`receipt.status='succeeded'` 只表示命令采用，异步操作另查 operation/check。格式/无权/同 ID 改内容/存储异常分别为 400/403/409/503 |
| 保存连接 data | 新建：`{connection_id,expected_revision:0,name,profile:'openai_compatible',base_url,api_key,model,max_output_tokens}`；编辑传当前 connection revision；`profile:'modeld_grant'` 移除 base_url/api_key，改用 grant_ref/grant_revision | AU 先存脱敏意图；API profile 向 modeld `POST /v1/api-connections` 注册同操作/主体/AU，预授 profile 查询既有 grant；核对原 grant/revision 后采用。注册响应丢失只 GET 原注册 |
| 有限授权 / 默认 | `grant_model_resources:{max_calls,allow_unknown_cost,reason}`；`set_connection:{connection_id,expected_revision,enabled,make_default}` | 同 AU 事务更新资源 grant 或实际默认；不发推理；旧版本领域拒绝保留回执 |
| 开始验证 data | `start_model_check:{connection_id,expected_revision,binding_id,document_name,document_text}`；binding_id=null 表示治理者本人承担 | 同 AU 事务保存 Work/Member/绑定/Mandate/固定 Definition、check、两次额度预约和私有资料，返回 check_id |
| 单次模型请求 | worker `POST /v1/requests`：id、au_id、run_id、connection/grant 与 revision、model_id、messages/tools/generation/deadlines | 当前 wire 要求 `id=run_id=attempt_id`，两轮各有不同 ID；GET 原 request 收集 state/action_authorized/result/error，原 events 单独取证 |
| 实际资料工具 | `read_document({document_id:check_id})`，唯一完整 tool_call | `ModelAccessStore.tool_result` 返回 document_id/name/content/sha256/challenge 并保存原工具回执；拒绝其他资料 ID、路径、多工具或半个 JSON |
| 第二次调用 / 展示 | 原 native 助手消息 + 对应 tool_call_id 的持久工具回执 | `complete_reply` 确认实际校验码，保存 output、两条 attempt/用量、该 revision 的 last_check；刷新 GET 显示同一结果 |
| 原请求恢复 | `GET /api/v1/models/receipts?organization_id=<AU>&id=<原命令ID>`；reconcile_connection / reconcile_model_check；cancel_model_check | 核对原注册/attempt，当前授权仍有效才推进未派发阶段；已派发未知不换 ID 重放。本地停止后保留已发生费用/预约 |

页面顺序：正常登录→选择 AU（必要时先完成 S05 治理）→保存连接→单独授予有限调用/资料工具→选择文本并预览→提交验证→第一轮模型提出读取→核心验证当前授权并读取持久资料→第二轮携原工具回执继续→模型页显示原输出/费用→独立采用默认→刷新重开。首次请求不含资料正文或 challenge；因此通过必须确实经过工具结果回传。

AU SQLite 内的 state、意图、资料和回执在同一事务提交；modeld 的账号/grant 在其另一数据库事务提交，不存在跨库全局事务。外部 I/O 前先存意图；unknown 保留原请求查询，不能用新 AU、新连接或新 Work 掩盖历史。撤权后的迟到事实可计费取证，不能继续工具/采用输出。

### 4. 完成演示与验收

| 操作入口与演示 | 必须看到的实际结果 | 覆盖 / 当前差距 |
| --- | --- | --- |
| 普通核心账号在模型页保存连接，刷新并重启再登录 | 同 AU/connection ID 和配置仍在；无 Key 回显/缓存/公共日志；保存推理次数为 0 | M01–M03；工作树受控证据已有，凭据四个反例未闭合 |
| 本地可控供应商分别返回成功、401、模型不存在、连接失败 | 四种可理解结果、脱敏阶段与恢复动作；无法确认受理的失败只能核对原请求 | M02/M08/M09；结构化错误待写，不能用通用 unknown 充当通过 |
| 不授权工具、仅给 1 次额度、跨 AU/失效 grant；再使用有效工具权限和至少 2 次额度 | 反例都在有副作用前拒绝；正常对照可进入完整往返；不超资源计划 | M04/M06；沿现有 Python/HTTP/浏览器补足证明 |
| 选择含已知内容的文本，点击验证 | 首轮只见资料 ID，模型要求工具后实际读出正文，第二轮回答含校验码；展示两个不同 attempt 及用途/用量 | M05/M07；真实 HTTP→modeld→固定 SDK→回环供应商已测，指定真实供应商/profile 另验 |
| 点击默认、编辑/停用、刷新 | 默认独立生效不增加调用；变更版本使旧验证失效；历史记录保留 | M01/M02/M09；浏览器后半程待完成 |
| 丢 POST 回执、两端重启、取消/撤权，以及线程 start 抛错后显式核对 | 原 ID 可追踪，不二次 POST/重复工具；当前权限阻止继续但用量保留；线程启动失败可在同进程恢复 | M03/M06/M08；线程恢复和中断事件用量缺陷待修 |
| 320/390/1024/1440 浏览器及键盘；切账号/AU/服务实例 | 无溢出、状态可读、输入/焦点可恢复；旧 AU 结果不串入新页 | M09；现有脚本在 1440 状态文字处失败，其余宽度及尾段不能记通过 |
| 构建最终候选，在独立临时安装目录启动并完成上述闭环、重启/兼容检查 | 安装后的真实模块可用，schema 3 可重开；不兼容旧候选在采用/回退前拒绝，原 ID/责任/unknown 保留 | M10；已有 14 项 schema/包规则测试不等于实际安装验收 |
| 使用用户指定的真实 profile、资料、调用次数与费用授权进行一次往返 | 实际供应商完成两次推理和一次工具接力；记录真实 attempt、结果、已知费用/未知原因，无额外推理 | M05/M10 的 real 出口；资源参数未落实，不执行或擅自找凭据 |
| 固定工具链检查、独立身份/持久化/费用复核和交付 | npm check、Python discover、modeld/浏览器/安装各自通过；检查最终提交及远端 SHA | 不能用受控测试、文档或子任务通过关闭整卡 |

当前证据和剩余缺口见 [058 核查](../../evidence/058-s02-model-tools/design-readback.md)。安全反例、结构化诊断、中断用量、启动恢复、完整浏览器、最终安装和指定真实 profile 均需闭合；U-072/#21 继续进行中，全部 M01–M10 和 real 出口通过才完成。S03/S04/S06 的设计仅承接后续，不改变卡片依赖或授权。

<a id="u-067-development"></a>

### U-067 开发说明

直接依据Main Chapter V1 P-02/P-04/P-05/P-08/D-01/D-02/R-07/R-08和053 S03，在S01、S02调用契约及U-069完整受控治理工程完成后，以严格TDD贯通单Agent合法路径和按目标形成的团队/依赖工作；Execution绑定责任Member、Work、Mandate与Agent Definition版本。复用Harness，不强制第二成员、行业岗位或固定层级；覆盖无效草案/跨AU/失效授权/工具与并发冲突。本片单Agent真实成果及需要协作时的真实依赖分别取证；旧公司/两成员基准不作为所有AU的准入门槛。

<a id="u-068-development"></a>

### U-068 开发说明

直接依据Main Chapter V1 D-03/K-01/R-02和053 S04，以严格TDD贯通成果登记/读取/下载、反馈来源、正式采用、后续任务与实际改变；重大知识纠正可追踪处理依赖结论和未完成工作。覆盖缺失或篡改成果、只自述完成、无来源反馈、重复事件、采用失败后误消费和迟到回执；复用既有成果/任务机制但不继承旧公司排期。受控工程与本片真实成果、质量反馈和第二次交付分别取证。

<a id="u-070-development"></a>

### U-070 开发说明

直接依据Main Chapter V1 R-01–R-08和053 S06，严格TDD贯通局部等待/恢复、独立监督、持久意图与新输入路径；覆盖一项unknown不阻断独立工作、有效执行所有权、并发共享环境/交付冲突、资源变化影响在途、重复迟到事件/分层重试。外部未知先查询，新推理另计量；主动观察有目的/预算/退避，路由监督评审按用途入账。受控机制与本片指定窗口内的真实恢复/持续责任分别取证，旧主机或公司任务不构成规范前置。

<a id="u-073-development"></a>

### U-073 开发说明

直接依据Main Chapter V1 P-06/P-08/S-01/S-02/S-04及PRD S07：真实工作效果触发问题与改变，低影响授权内试用留版本/检查/撤回，高影响按治理权限；试用许可和效果证明分开，实施/评估职责可区分不强制不同Agent，需要独立判断而条件不足保留候选。禁止改自己评分/评级/删失败；保留窗口/停止/总目标成本和五类人工介入。受控机制与真实自主效果分别验收，旧公司/管理工具卡不构成本片需求前置。

<a id="u-074-development"></a>

### U-074 开发说明

直接依据Main Chapter V1 P-07/S-03及PRD S08：无私有商业平台账户/仓库凭据/许可证服务的干净环境构建安装，核心认证/AU权限/审计及合法模型工具工作连续可用；指定构建/窗口内验证反馈后行动、局部故障、重启、额度、外部升级、兼容拒绝、备份恢复和不双派发。复用052只作实现参考，不继承旧机器/业务特例作为前置；实际环境/许可/发布授权分别明确，受控包检查不替代真实独立使用或持续证据。

<a id="u-075-development"></a>

### U-075 开发说明

直接依据Main Chapter V1 A-03/R-06/K-02–K-04及PRD S09，逐profile完成合法配置/认证、原生内容/流式、工具往返、长作业新输入与恢复、凭据单一所有者、正确用途/尝试计量；不支持明确报告，不以一个API/Go成功外推。以能力声明决定profile范围，031/048仅为复用与差距证据，不将旧供应商开发顺序当V1规范。每个profile工程与真实结果分别可追溯。

<a id="u-076-development"></a>

### U-076 开发说明

直接依据Main Chapter V1 C-01–C-05/D-05及PRD S10：双AU接受/履行/验收承诺并处理争议失联，再逐步交付递归派生、责任交接与重组退出；叶子/组合同一公开契约，治理/授权、协作、部署关系分开，授权投影包含撤权生效/用量/unknown/partial而不泄内部资料。验证离线边界、资源嵌套去重、再委托撤权、退出责任/资料/访问去向；旧025/U028–31只作历史实现参考，不继承旧公司的持续运行卡为规范前置。每段启用和真实出口单独声明。

<a id="u-071-development"></a>

### U-071 开发说明

按053 S11与Main V1 P-07/A-04，独立客户端经版本化公开契约完成创建/查询/受控操作；核心自带基础认证/AU权限/审计，不依赖私有商业平台账户/仓库凭据/许可证服务。逐用例重绑平台/管理调用者并退出内部表/私有模块旁路；协议/状态/Agent配置版本区分。合法/越权/版本/重复/审计黑盒及React回归通过；modeld选用时仍校验AU grant/revision，实际独立发布和真实模型成果在S08另验。
