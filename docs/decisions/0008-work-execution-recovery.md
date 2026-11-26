# ADR-0008：在原AU事务中恢复同一次Work执行

2026-11-26，设计采用，尚未实现/运行采用。依据用户明确授权接续#46/#47/#66以完成#76、Main Chapter V1 R-01–R-08/K-02/P-04、FRONTEND§4.2、ADR-0005及[恢复契约](../../specs/053-union-rewrite/u092-work-recovery-contract.md)。原候选ADR-0009未在基线找到，不覆盖其可能存在的历史。

选择GovernanceStore原事务内的owner/epoch、完整请求快照和原模型观察事实；WorkService复用现有step/loop及唯一采用路径。旧host_instance/原Work/attempt/request/预约和已发生计量保留。准备/派发边界明确持久；只有可证明prepared未发送的请求可原ID发送，unknown与dispatching只lookup原ID/摘要。旧worker在调用/工具/采用边界失权，不把关闭当远端取消。

继续手工finish/start会丢同一次执行身份；放宽host_instance检查会允许迟到worker竞争；另起恢复Engine/队列会重复事实和派发。窄私有表增加有界请求/事实存储成本，但与授权/owner/预约同SQLite事务关联，比跨文件快照简化失败窗口。新机制若不能被旧schema4可靠识别，显式采用升schema5及安装兼容拒绝，read不升级。

本卡不创建长期借用浏览器token的执行身份；#76的合法持久业务意图须另在同一所有者内冻结并验证正常退出与真正撤权。输入/cursor由#47负责，条件唤醒和profile原生能力保留原owner。详细接口和文件归属以恢复契约为准；工程、真实和持续分别验收，真实调用/迁移/部署不因ADR授权。
