# U-092 / #46：原执行恢复契约与实施计划

2026-11-26冻结，源码基线e29fb49。用户明确授权完成#74/#75/#76及必需#46/#47/#66；#46保留原历史后由codex-home交接至zbook-codex，version6/progress已读回。原候选输入缺失和失败证据保留；不认定缺文件为产品RED。独立基线见 evidence/U-092/resume-baseline-review-20261126.md。

## 一个用户结果

在原Work的恢复入口，以当前合法主体/治理权限核对并接回同一attempt、责任、定义/授权和已保存上下文；网络已派发则只查原modeld请求，确定未派发的准备请求才可以发送一次。原Work/Member/Mandate/Definition/attempt/command/request与预约不换ID，未知不释放、不重放。两次恢复争用只产生一个有效所有者，旧worker不能继续调用、工具执行或采用。

本卡负责原执行恢复和执行所有权；#47负责持续输入，#76负责持久完整业务意图、后台自动推进/采用/交付及不借浏览器token。此片正常恢复命令仍须当前会话，不能因此声称#76持续授权已实现。

## 公开命令与读取

沿原五字段POST /api/v1/work/commands，新增 `recover_work`，data严格为 `{work_id, attempt_id, reason}`。actor从当前核心session取得，base_version在接受事务校验；仅当前有效治理者可发起，所有定义、Member/Binding/Mandate、章程/政策、模型连接/grant和资料权限按原规则验证。客户端不能提交host_instance、owner或epoch。回执沿原governance receipts，重复请求返回原回执，异参/跨主体拒绝；已经被后续恢复替代的请求重放不能重新取得所有权。

新Work投影给出当前attempt的恢复资格和明确原因、原执行归属和等待依据；不返回私有请求/正文/令牌。当前实例已有活动执行时不能恢复并行副本。原Work页面的按钮消费此合同，查原ID与已确认/unknown边界继续原命令owner；缺权限时只读事实而不显示可执行资格。内核片不挂载第二控制台，界面由协调者在kernel采用后接入并一起验收。

## 唯一事实与恢复顺序

GovernanceStore继续唯一AU事务/审计写者。新增窄私有adapter在调用方SQLite cx内保存完整dispatch请求快照、摘要和完整模型观察事实，不新增数据库/第二账/队列。引用/owner epoch与当前步骤保存在原Work记录；私有正文不进入公开回执。旧host_instance作为初始执行历史保留，另记当前执行owner `{instance, epoch}`，严格整数epoch不得与modeld wire的generation参数对象混淆。

1. 当前host持有原console.lock且非stopping/closed，接受恢复与owner变化同AU事务关联。只在原owner已不属于当前有效host且无本host活动worker时接管；同host新恢复请求不能夺回当前owner。重复原请求只读原回执。
2. 新派发在预约事务中保存实际package/messages/tools、context_scope、connection、materials binding及原命令和摘要。若transport能给出modeld body，保存其精确body及canonical SHA-256（JSON对象按key排序、无空白、UTF-8），与modeld已公开request_digest匹配；不能用command摘要代替模型输入摘要。
3. 新请求明确 `prepared→dispatching→observed/adopted`。持久dispatching在POST之前提交并重验owner/current授权；prepared可在恢复后发送原快照一次。dispatching/unknown/旧记录无法证明未派发时只GET原request；404不证明未执行，保留原预约。既有lookup用量接口兼容，新增取得完整原结果的窄lookup能力必须核对AU/原request/digest和action_authorized。
4. 完整模型事实（消息、usage、摘要）先持久保存，记录adoption_pending；当前有效owner按原step/attempt、连接、scope和当前资格采用，工具提议仅在该owner内调用。已经保存的tool/assistant轮次从WorkContextStore继续，不重新读取变化后的资料代替原结果。原事实可保存但资格不符则不采用、不发新调用；失败历史和发生过的用量保留。
5. 网络、lookup和等待在AU事务之外；采用仍复用WorkService现有step/loop及规则，提取窄采用helper而非复制另一套结果/工具实现。恢复已观察但未采用事实，与正常完成路径共用同一helper。旧worker在POST前、工具执行和结果采用检查owner epoch及host关闭状态，不能覆盖新采用。
6. Console关闭先阻止新的Work接受/派发，释放console.lock之后旧worker仍不得新POST/工具/采用；原已派发结果未知保持本地预约，可由当前owner核对。不能把本地关闭当远端取消。关闭前未提交的命令不留下新意图；已提交未发送保留prepared及原预约供恢复。A未知不挡独立B。

若新持久字段会被旧schema4代码忽略并绕过owner/fencing，则成功显式采用新机制才升AU schema5，read不迁移；更新现有schema支持/安装兼容声明及回归，旧安装候选不兼容必须拒绝。无真实数据库迁移。老记录无法证明输入digest时保持只读核对/不可采用，不静默兼容成可重派。

## 必要性与边界

现有reconcile_automatic仅用量not_adoptable，active_attempt拒绝旧host，进程内active集合和关闭无Work fence；配置/文档不能补足。ArchitectureReviewRequired: yes；前置ADR-0008冻结当前所有者内恢复，ADR-0005方向保持。新增adapter/domain/application窄职责，WorkService仅接线与原采用路径提取；不追加通用Runtime、Engine、租约服务或新浏览器loop。按原Core路径，不复活legacy派发、S02账户借用或私有平台绕权。

## 两个可并行任务及顺序集成

TDD Route: strict，用户/AGENTS明确要求；原相关40项基线已通过，真正缺口需新行为RED。预计#46完整结果6–8小时，kernel+UI是同一用户结果，不各自关闭卡；若出现独立结果或范围超8h，先在线复评。

- 任务A（协调者当前checkout）：完成独立#75成果阅读及浏览器/全量验收，与恢复backend文件无重叠。
- 任务B（独立#46 checkout的kernel实施者）：按本合同新增真实HTTP/SQLite故障用例并观察RED，最小实现owner/close fence、原请求快照/原模型事实/同attempt恢复、摘要lookup及schema兼容。文件责任限 `ai_union/application/{work,work_dispatch,work_recovery}.py`、`ai_union/domain/{work,work_recovery,governance}.py`、`ai_union/adapters/work_execution_store.py`、`ai_union/console.py`、`ai_union/work_transport.py`、受影响release兼容声明和对应测试/局部AGENTS。不要修改前端、管理主账/在线/Git/协调者过程记录。report只证明kernel，不宣称卡done。
- kernel后独立规格审查，再独立工程质量/权限/身份/计量审查；有缺口修复复审。协调者只提交task-owned文件、在#75采用后顺序整合kernel，接入原Work恢复UI/HTTP及实际浏览器并跑必要组合全量；完整#46验收才done。
- #47随后在该恢复合同上冻结持久input/cursor与原下一step快照，不反向创建第二loop；#66完整资源贯通另验；最终#76在全部真实前置满足后实现持久业务意图。

## 验收反例

原工具阶段已提交后重启，原attempt及配对消息连续；prepared未POST/dispatching响应丢失/已观察未采用三个中断边界；两个恢复者竞争和被替代请求重放不增加epoch；旧worker迟到/Console关闭不得新行动；模型/资料/治理撤权拒绝后续采用但保留调用/预约；跨AU/主体、快照/digest篡改、回滚失败、GET404均明确拒绝或unknown，读取零写入/零POST。实际HTTP/SQLite和受控modeld完成一条正常恢复链及失败链，固定npm/Python全量、受影响browser与独立复核。真实模型调用0、无部署/迁移；旧失败和原字段/ID保留。
