# Runtime 设计独立复核：ARCHITECTURE §1、§8–10

2026-11-06；working-tree；HEAD c31bf0efac7e54565e3a5fce0d6becd807b12b5a。只读正式文件，报告写入 .union/s02-resume-audit/design-runtime-review.md；未修改代码/主账/Git/在线卡、未读取凭据、未调用真实模型。

基线：Main Chapter V1 的 D-01/D-05/A-02/R-01–R-07/K-04，PRD F02–F08/F12，ADR-0005 既定增量方向；按 requesting-code-review/code-reviewer.md 做咨询复核。复核期间主协调者更新了文档，因此下文把已读回修正与仍建议补充的措辞分开。原始运行证据为同目录 runtime.md 的源码核对及两个纯内存探针；本轮没有重跑产品测试。凭据探针仍 RED、没有真实模型验收，均按协调者提供的当前证据边界保留。

## 最终读回结论

最终独立读取的 docs/ARCHITECTURE.md SHA-256 为 1A7020410382165C9159CD676BCEDFE4FB989706D806FF30761B622CBC411DB3，HEAD 仍为 c31bf0efac7e54565e3a5fce0d6becd807b12b5a。关键设计问题均已有明确文字处置；没有发现阻断本次“设计说明交付”的遗留问题。该结论只针对新增 §1、§8–10，不是 S02 代码通过、真实可用、未来契约采用或整片完成结论。

§1:56 现已限定 API/modeld profile，并明确保留的 Codex CLI 子进程和 Docker 容器。源码对照为 executor.py:39/:61、workspace.py:140/:147。§9.2:213 现已明确共享调用、游标/采用、租约和多槽位策略都是后续方案，须对应契约及编码前 ADR 细化；§9.3:231 已明确 owner/generation/未过期共同检查、Runtime 续期/到期转换所有权和 S06 接管边界。无需现在重新批准技术栈或实施未来机制。

## 未解决项与非阻断建议

### §9.1–9.2 可再给两个 generation 标记不同类型

现有 wire 的 generation 是模型选项对象，包含 maxOutputTokens（services/modeld/src/journal.ts:31-35、:154-156）；拟议 ExecutionSpec.generation 是执行所有权代次。建议在 DTO 行加一个短注释，或将内部字段写作 ownership_generation，避免未来直接把 spec 展开进 modeld 请求。

新 step_ref、fact_id 和 owner/generation 都先保留为 AU 内部关联；现有 modeld v1 对字段集合做精确校验（journal.ts:146-149），不接受这些额外字段。若以后要传到服务边界，必须另冻协议版本。

分类：Minor；非阻断合同可读性建议。两个字段在现文的不同边界中可以区分，未发现实际 wire 已改错；现文已正确写明 id=run_id=attempt_id，无需改现有 wire。可在 S03 冻结 DTO 时补明，不是本次文档交付的阻断项。

尚未解决的工程事项仍是协调者保留的凭据 RED、中断用量/诊断、线程启动恢复及后续真实出口；本次没有修改或执行这些代码。S03 的 schema/AI Member/共享调用所有者及 S06 并发公平规则仍待其授权实施期冻结和行为验证，不能把文字方案记录为已运行能力。

## 已提出且已独立读回的修正

以下不再作为未解决发现。它们说明哪些设计风险已有明确处置，不意味着代码或运行行为已修复。

| 初读发现 | 最新文字的处置 | 仍需未来实现验证的反例 |
| --- | --- | --- |
| 模型事实已存、工具/成果采用尚未提交，没有恢复动作；“旧 generation 仅取证”可能使新 owner 也无法采用原结果 | §9.2:222、§9.3:240 已加入 fact_id/digest、adoption_pending、原阶段 cursor、稳定采用命令/原回执；旧 worker 无权采用，新有效 owner 经受信恢复重验原事实与当前资格 | 保存完整模型结果后、正式采用前崩溃：无需新增模型调用即可继续或明确 not_adopted；采用重复返回原回执且不重复结算/完成 |
| 上条初次修正写成“不再发模型/工具”，会连从未执行的工具提议也禁止 | §9.3:240 已区分未执行提议先写意图再执行、已有工具结果只查原回执、已开始/未知副作用先核对 | 第一次 tool_call 已存但工具未执行的恢复必须只执行一次；工具已执行但本地回执未知不能盲重放 |
| infer 只有 execution_ref/messages/tools，无法区分 SDK 节点重入和合法新一轮调用 | §9.2:220-225、§9.3:241 已加入稳定 step_ref、attempt ID/正文/digest 映射、核心持久游标及 SDK checkpoint 落后的补齐规则 | 核心事实已提交而 SDK checkpoint 尚未落盘：同一 step 只查原 attempt；相同正文的真正新 step 应独立准入/计量 |
| tick 与 infer 都写“资源预约”，存在父子预约重复扣 AU 额度的设计歧义 | §9.2:218/220、§9.3:233 已明确 Execution 父预约、子 attempt 分配不重复扣减；modeld 槽位不是第二份 AU 余额 | 两次实际调用准确计为两次；同一 step 重投不增预约；未派发部分释放、已派发 unknown 保留 |
| 旧调用者表只有 Console.__init__、runner.run/watch，遗漏实际网页及测试入口 | §9.3:229、§10:257 已补 Console.command/_execute/_job/_probe_job、cli.main，并说明网页 _job 直接 step、CLI run/watch、各自 probe/api-test | 旧网页/CLI/连接测试正常与 unknown 对照均保留；新 V1 不沿用旧全 AU gate/长期 runner.lock |
| CoreModelForms/CoreModelRecords 不是真实文件名 | §10:256 已改为 CoreModels/ModelFields/ModelCommandForm/ModelRecords/useModels/api/types | 文件映射与实际组件继续一致，不能用虚构名称掩盖具体改造责任 |
| 进程图注把所有 Agent 执行概括为 Python 内 SDK | §1:56 已限定 API/modeld，保留其他 legacy profile 的 Codex CLI / Docker 进程边界 | 真实安装及选定 profile 的部署另验；不能从静态图推断宿主当前已运行 |
| 租约/多槽位写成具体机制，未区分拟议方向与已冻结契约；只检查 generation 不足以表达过期 | §9.2:213 明示后续契约/编码前 ADR；§9.3:231 明确 owner/generation/未过期及 Runtime 续期/到期 owner | 后续按所选机制验证续期失败、到期接管、旧 owner 拒绝、原远端结果核对；不要求这次设计工作实施 |

源码对照点：

- S02 的原始稳定步骤是固定 stage 0/1，attempt ID 从 AU/check/stage 确定性派生（application/model_checks.py:105-110）；generalize 到 Harness 时必须保留等价语义。
- S02 observe 和 accept 是两个独立 AU 事务（application/model_checks.py:84-94）。模型事实与采用的间隙是真实存在的，需要恢复协议，不是抽象担忧。
- 当前 S02 工具回执以 check 和原 tool_call 关联，重复返回原结果（adapters/model_access_store.py:58-78）；未来通用工具调用至少以原 attempt + tool_call_id 定域。
- Console._execute:363 在 runner 前拒绝任何 unknown；Console._job:478 直接调 step；cli.main:143 调 run/watch；Console._probe_job:451-454 与 cli.main:174-177 分别走工具/普通连接测试。
- tests/test_core_model_recovery.py:74-105 描述原工具已提交后继续第二次推理的正常恢复用例；本轮只读取测试源码，没有把其历史状态写成当前通过。

## 当前/拟新增、所有权与故障隔离的核对范围

§8:141、§9.1:195、§9.2:213 现已清楚声明完整 V1 目标链未接通、S02 不调用 HarnessExecutor/runner、拟议接口目前不存在。没有发现仍把固定两阶段验证描述为已经拥有完整 V1 Harness 的具体句子，因此不建议再增加笼统免责声明。

当前 DTO 边界也已核对：

- modeld 仅验证 AU/grant/account/model，不拥有 Work/Member/Mandate/Definition 领域授权。
- S02 当前直接 ModelServiceClient；legacy ModelServiceTransport 仍构造 Engine。
- GovernanceStore 是采用后的 AU state/审计/回执提交者；私有 attempt/material/tool receipt 在同 AU 事务内写入。新 application/model_calls.py、core_harness.py、domain/work.py 都标为未来落点，没有提前删旧函数或新建空模块。
- §9.3 同时记录 Console/runner 的每 AU 阻塞和 modeld 的全服务 persistent_serial；S03 只承诺终态 unknown 的每 Work 隔离，并明确共享模型槽位等待；S06 才提独立槽位/公平性和故障反例。这样没有把“删掉一处 Python 条件”等同于端到端并发成立。

仍须在 S03 契约中冻结共享 Member/Binding/Work 表的类型与纯规则分工，避免 domain/responsibility.py 和 domain/work.py 为同一事实各持一套转换规则；这属于明确现有单一所有者如何扩展，不是预先设计第二份领域状态或暂停当前文档工作。

本复核为咨询意见，不采纳未来契约、不批准合入或运行。上表只证明文字风险已处置；原 runtime.md 的线程启动恢复缺陷、凭据 RED、实际模型/浏览器/安装验收边界不因本次文档修订改变。
