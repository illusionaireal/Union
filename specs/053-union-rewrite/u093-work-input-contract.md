# U-093 / #47 原工作长执行新输入：契约与实施计划

2026-11-26；代码基线d04767f。用户已授权必需前置，#46以5513cf6完整七CI/普通Git采用并online v12 done；#47实际依赖全部done，user363认领v5/progress/revision1286。本文在行为代码前冻结，预计6–8小时有效工程，一个不可分割用户结果。若出现独立结果或超8小时先复评。Main Chapter V1 R-06/K-02/P-04、FRONTEND VJ05/UX04、ADR-0005/0008为上级；[ADR-0010](../../docs/decisions/0010-work-input-adoption.md)记录同源采用决定。TDD Route: strict，来源为用户AGENTS；不破坏正确代码制造RED。

## 用户结果及范围

用户在原Work运行、长等待、unknown或重启后补充要求；收到稳定输入回执，看到已收存、附入原请求、模型已观察、已正式采用的不同事实。下一原模型步骤按顺序获得当前合法输入，不重复消费/丢失或重放原请求。输入不授治理/工具/资金权限。接收不要求模型就绪、预算充足或当前host已接回attempt；已结束Work不隐式重开。原负责Member/Work/Mandate/Definition及执行ID保留，actor与负责Member分开。

本卡不实现成果反馈的result/version采用（#41）、条件唤醒/通用调度（#48）、原生profile实时注入（#52）或持久业务运行身份（#76）。profile的long_job_new_input仍unsupported直至原owner验收；这里是Core原步骤边界输入。真实模型、部署、迁移、长期业务没有新增授权。

## 公开合同

- 原五字段POST `/api/v1/work/commands`，kind=`append_work_input`，data严格为`{work_id,input_id,content,reason}`。input_id为有界引用，前端生成`input-<32hex>`；身份来自当前Core session，客户端不得提供actor/source/owner/epoch。content非空UTF-8文本，拒绝NUL/孤立代理字符，最多65536 UTF-8字节；reason沿已有10000字符边界。最多100个输入/Work、累计8MiB私有正文；合成上下文不超过现有4MiB，wire不超过8MiB，超限明确拒绝，保留原记录、不截断正文。
- 输入身份为`(au_id,work_id,input_id)`；正文、初始actor/source不变。同主体同ID同正文返回原事实，不增加seq/消费；异文/冒用主体冲突。重复原command先返回原回执，异参仍冲突。新command复用已存在input时保留原reason/source，不暗改来源。正文经U120模式归一为content_sha256后写commands/audit；回执只含标准身份/版本、work_id和input元数据，不含正文。
- `GET /api/v1/work`增加`access.can_append_input`；它仅表示当前合法governor的低影响收存资格，不依赖can_start、模型/预算或执行恢复资格。`access.can_read_inputs`独立表示现有正文GET的当前governor只读资格，不能以收存不可用/已退出/预算不足推断历史正文不可读。每个Work投影`input_seq`/`input_cursor`/`inputs`/`input_summary`。旧无输入Work投影空数组/0，读取零建表、零升级。
- input元数据包含`id,seq,sha256,bytes,source_kind:'requirement',actor_principal_id,received_at,reason,source_scope,status`。source_scope记录当时Member/Binding/Definition/Mandate及其版本/章程政策版本，不隐式改成新来源。status严格为`received|attached|observed|consumed`；保留attachments历史与关联step_ref/model_request_id/request_sha256、observed/consumed的原step依据。input_summary分别计数四状态和pending；pending为未consumed。input_cursor仅证明按序成功采用的连续前缀，不能跨过未处理输入。
- `GET /api/v1/work/inputs?organization_id=...&work_id=...&id=...`只读同一AU/Work/input正文，返回`{protocol:'core.work-input.v1',organization_id,work_id,input,content}`。只有当前合法governor可读，正文须与元数据UTF-8 SHA一致；missing/跨Work/跨AU不回退查别的input。原回执查询沿governance receipts，查询不执行/消费/修复输入。

## 唯一写者、顺序与故障

GovernanceStore继续唯一AU事务/回执/审计写者。WorkInputStore只在调用方cx保存不可变私有正文，元数据/seq/责任来源与接收回执同事务；read不建表。不建立第二输入队列、聊天页或loop。接收资格和行动资格分别校验；低影响接收可在治理暂不可执行时保留要求，后续附入/采用仍必须当前有效治理、责任、模型/资料权限。

1. 现有下一run_step构造完整plan时，按seq选择当前合法且可容纳的未处理前缀；正文缺失/摘要变化/来源资格不能确认在预约前拒绝。原上下文、input user messages、input_refs、完整wire快照和attachment在原dispatch.prepare预约事务可靠关联，失败全部回滚。已附入unknown输入保持原step，不附入另一请求；既定已派发wire不因后到输入改变。
2. 观察仅表示原模型处理过该请求。正式consumed、连续input_cursor与成功adopt_turn/保存`input user messages + assistant/tools`同AU事务提交。采用/保存失败、关闭/旧epoch/false行动资格不得消费；私有观察/用量和attachment保留。恢复复用U092原sealed请求/观察/唯一采用路径，不重复插user消息或换输入正文。明确未执行并可再附入时保留原attachment历史，仍需新当前授权调用，不把unknown当未执行。
3. 输入可能在两原步骤之间增加AU版本。可信内部下一步意图在原预约边界从当前状态生成，可靠绑定原loop/next-child ID，并复核当前scope/owner/授权；不得泛化忽略公开base_version或更改已保存原请求。不能仅因正常append把原loop永久固化为stopped。避免新Plan/transport建立窗口将刚接受的输入漏到错误步骤。
4. 来源版本保留且当前附入/采用重新核对责任及有效授权；旧owner不得消费，交接不能隐式改旧来源或按文字扩大Mandate。来源不再适用时明确保留pending/需核对，不能丢弃或悄悄作为新来源。新的合法执行所有者接续同责任时允许原输入按当前合同恢复。
5. sealed之后到达的输入留给后续原步骤；最后一轮/预算耗尽/停止仍明确显示pending与负责者，不增加预算或新Work。结果标注实际采用输入的cursor/依据，不宣称后到输入已被该结果回应；本卡不把输入消费当需求已经实现。automatic result-attempt close及deliver不能吞掉pending输入；手工明确停止保留未处理历史。

## schema与兼容

首次成功append显式采用schema6，因为旧schema5代码会忽略输入采用约束。保留2/3/4/5已有行为与旧记录；后续dispatch/loop/recover保持较高schema。新循环的子步进绑定到原父命令，旧循环继续按原严格版本工作。发行预检按私有正文、附件、上下文及父子绑定等实际特征拒绝不支持schema6的候选，即使当前没有输入、父循环仍保留schema5。读取不升级、不双写或迁移真实数据。

## 两个独立实现任务和顺序集成

协调者独占Git/在线/账本、本文/ADR/架构/过程/发布工作流及最终验收。复用既有clean checkout，不创建新worktree。

- A backend/kernel，94bd `codex/u093-input-kernel-20261126`：拥有新增`ai_union/{domain/work_inputs.py,application/work_inputs.py,adapters/work_input_store.py}`及既有work.py/work_dispatch.py/work_recovery.py/work_context_store.py/work_execution_store.py、受影响governance/model_access/core store/server/release Python与对应AGENTS/Python行为/兼容测试。不得改前端、CI、管理/在线/Git、协调契约/ADR。基线target先GREEN，新行为真实RED后最小GREEN，再恢复/权限/原loop/context/兼容回归；冻结生产后规格审查再工程质量/身份复审。只报告kernel，不关闭整卡。
- B frontend，5be7 `codex/u093-input-integration-20261126`：拥有api client/types/core-boundary、原Work页接入/命令恢复hook、新`WorkInputs.tsx`及DOM测试和`u093-work-input-browser.cjs`。按本文固定API/状态/作用域消费，不编辑Python、管理/Git/本文。正文/草稿在身份/AU/Work/权限变化时清除；unknown仅存原ID/digest元数据，重启查原请求不重POST；已知直接拒绝和未知分开。键盘与五宽验证，不另造页面/浏览器调度。先DOM真实RED后GREEN，实际browser由协调者顺序整合后跑。
- 协调者顺序整合kernel，接受规格/质量修复并冻结，然后npm/Python全量、受影响实际Chrome及modeld/SQLite/HTTP验收；准确候选七CI普通Git采用/readback和在线完整#47 done。之后再#76。任一子任务完成不代替整卡或74/75/76整体完成。

必测正常/RED：模型held时收存返回；两步之间按序一次消费；无模型/预算/恢复资格仍可收存；同ID重复/异文/跨actor/AU/Work；append丢响应和重启原查询；snapshot/attachment/context提交崩溃回滚；unknown/404零重POST；完成观察但撤权/旧owner/关闭/采用失败不消费；合法原请求恢复恰一次消费和工具配对；来源变更；最后一轮pending/预算耗尽/已结束Work；正文界限/篡改/只读零写；schema6经配置/派发/恢复不降级、旧安装拒绝。全部fixture明确受控，真实0，原失败保留。
