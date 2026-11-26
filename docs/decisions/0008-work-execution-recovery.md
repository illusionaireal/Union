# ADR-0008：在原AU事务中恢复同一次Work执行

2026-11-26，设计采用，尚未实现/运行采用。依据用户明确授权接续#46/#47/#66以完成#76、Main Chapter V1 R-01–R-08/K-02/P-04、FRONTEND§4.2、ADR-0005及[恢复契约](../../specs/053-union-rewrite/u092-work-recovery-contract.md)。原候选ADR-0009未在基线找到，不覆盖其可能存在的历史。

选择GovernanceStore原事务内的owner/epoch、完整请求快照和原模型观察事实；WorkService复用现有step/loop及唯一采用路径。旧host_instance/原Work/attempt/request/预约和已发生计量保留。准备/派发边界明确持久；只有可证明prepared未发送的请求可原ID发送，unknown与dispatching只lookup原ID/摘要。旧worker在调用/工具/采用边界失权，不把关闭当远端取消。

继续手工finish/start会丢同一次执行身份；放宽host_instance检查会允许迟到worker竞争；另起恢复Engine/队列会重复事实和派发。窄私有表增加有界请求/事实存储成本，但与授权/owner/预约同SQLite事务关联，比跨文件快照简化失败窗口。新机制若不能被旧schema4可靠识别，显式采用升schema5及安装兼容拒绝，read不升级。

2026-11-26落实补充：当前owner在没有活动worker/恢复且有原sealed未决请求/未完loop时，可通过同一recover_work显式核对并继续，epoch保持；重复命令只读原回执。网络等待不占AU、catalog或全局mutex；最后派发准入之后已开始的原调用跨关闭仍须核对其真实远端结果，迟到worker不能结算新owner预约或采用。采用在工具/上下文保存后再次检查host/epoch。

完整已完成观察包括撤权消息，先在私有表保留，false行动授权不因后来授权改变。该保留取代旧“所有私有存储都无撤权正文”的规则；公开state/回执/审计、模型上下文、工具与成果仍禁止使用。采用前GET原modeld请求核对当前实际grant/连接和原wire摘要，已有观察不被GET的新正文替换。查询失败保留观察与预约，原usage不丢失。本补充是私有证据保留与行动权限分离，不提供正文读取端点或授权回退。

摘要落实采用实际journal canonical的UTF-16键排序和JS binary64最短十进制规则，保留原body而不改写输入。Python核心无Node运行依赖，实际Node源oracle验证浮点/53位整数/Unicode边界。wire限制8 MiB、64层、文本键与可编码UTF-8；不支持的非有限数值、孤立代理字符、循环等在提交预约前明确拒绝，不以另一摘要算法回退。

本卡不创建长期借用浏览器token的执行身份；#76的合法持久业务意图须另在同一所有者内冻结并验证正常退出与真正撤权。输入/cursor由#47负责，条件唤醒和profile原生能力保留原owner。详细接口和文件归属以恢复契约为准；工程、真实和持续分别验收，真实调用/迁移/部署不因ADR授权。
