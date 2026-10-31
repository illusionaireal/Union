# Astra 规划：撤掉原库观察连接

2026-10-31 21:34起，基线dev@e0d04c7；实际GPT-6 Astra完成只读完整规划，未改文件。2026-11-01恢复继续收口。Sol执行。

039已实证DELETE预检后切WAL仍由观察SELECT创建sidecars；新锁不能约束外部SQLite或文件替换，锁本身也可能创建文件。独立观察元数据必须处理提交/崩溃窗口、删除/替换与陈旧性，简单bool会误报，不应在本轮顺带引入。

最高最小方案：_checkpoint保持签名，删除所有原检查点SQLite连接、头/内容读取、表/行查询，仅lstat固定harness及checkpoint路径。明确缺失False，存在/异常/符号链接/非目录父项/特殊目标None。无匹配session既有False保持；True协议和前端分支保留但当前实现不产生True。代价是DELETE也失去true与按会话查询的false。Harness写入、真实接续、锁和权限不变。

先红后绿：实际SDK写后转DELETE，禁止checkpoint connect/content open；路径替换在旧connect入口导致sidecars新增。green需connect/open0与稳定fixture全部文件hash/集合不变。保留WAL/DELETE/空/损坏、缺失/目录/符号链接、权限和OSError、会话状态矩阵、HTTP同ID跨AU A存在None/B缺失False及全响应隐私；用完全不打开替代SQL authorizer，不以mock true伪造可见度。

仅可声明“本checkpoint观察不因SQLite连接创建/修改sidecars”，不可扩大为外部并发文件不变或全HTTP无副作用/跨来源原子。新实现旧connect钩子不可达，不假装转换已执行。定向、全量Python/npm及独立复核；U-041不关闭U-042不扩大。下一步不自动重建true，确有消费者需求时再单列具有时间/有效范围的写入方证据方案。平台不预设组织业务岗位/流程，不请求真实provider/Docker/VPS或付费。
