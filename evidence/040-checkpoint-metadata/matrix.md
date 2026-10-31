# 040 当前观察契约与证据

| 情形 | 当前值/证据 | 边界 |
| --- | --- | --- |
| 无本人run/匹配session/旧库无session表 | false/not_available，既有会话归属及交接测试保留 | 不借他人会话 |
| 固定路径在lstat时明确缺失 | false；不建harness/文件 | 不保证随后仍缺失 |
| 存在DELETE/WAL/空/损坏/其他thread或namespace的库 | null；不读取头/内容、checkpoint connect0 | 不表示无检查点；本实现无true生产来源 |
| 元数据权限/I/O错误、目录/符号链接/非目录父项 | null，确定性错误注入；私有错误不进响应 | 不用exists吞权限错误为false |
| 旧非WAL观察与路径替换 | 两项有效red；green移除原内容open与connect入口 | connect钩子未触发是入口移除，不称实际切换已执行 |
| HTTP同ID跨AU | A存在库None/B缺库False，正确AU/run/session、限域权限和全JSON私有哨兵保留 | 不以mock true冒充生产证据 |
| 真实SDK会话续接 | Harness/session revisions原有回归保留 | 当前实现不改真实写入/恢复及权限 |

新checkpoint文件观察只调用lstat，SQLite row查询被删除；原SQLite authorizer测试由完全禁止原文件open/原库connect的更强断言替代。三态协议中的true/requires_validation仅兼容旧来源和前端fixture，本生产投影不提供true。存在文件的paused/failed候选为unknown；unknown/reconciled仍requires_reconciliation，running/completed仍not_available。

组织库与文件系统不是原子快照；外部写入可以正常改变文件，不能从本次观察无连接推导任意并发全FS无变化。存在性信息不足、热配置、真实恢复/续拍、供应商迟到、实际浏览器与整体U-041未验。
