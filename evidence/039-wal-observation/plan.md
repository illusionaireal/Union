# Astra 规划：已观察WAL分支保守只读

2026-10-31 20:34起，基线dev@7c6c63c。GPT-6 Astra只读核对并用临时实际SDK/SQLite探测，完整规划返回；未改代码/文档/公司。Sol复现后实施最小修复，不扩U-042。

实证：WAL sidecars预检通过后，在connect入口关闭最后writer；writer正常checkpoint/删除sidecars后，观察SELECT重新创建空wal和32768字节shm，返回true。对DELETE头先检查、在connect前外部切WAL也有相同副作用。必须把writer.close的正常落盘与观察新增文件分开归因。

选择：读取header[18:20]含2即None，不对该WAL检查点调用SQLite；删除sidecar存在性预检。保留非WAL mode=ro/query_only/短超时/参数查询。不能用immutable忽略live WAL导致false，不复制整库、backup、改journal或新增协调/恢复协议。

这是接受可见度退让：当前SDK setup写WAL，通常SDK检查点将显示未知。只关闭已观察WAL分支窗口，**非WAL预检后切WAL/路径替换竞态仍未关闭**，不得称任意并发绝对零写入。

验证：保存修复前后阶段文件名/大小/hash；两项先红后绿。真实SDK live WAL含目标及不含会话均None，checkpoint connect0，文件含SHM hash不变；closed WAL也None。paused/failed恢复unknown，未知执行仍requires_reconciliation。非WAL正例显式仅fixture转DELETE，保留root/namespace/AU隔离、authorizer禁止正文读取及真实connect错误测试。HTTP保留真实WAL unknown场景与独立非WAL正例。定向checkpoint/HTTP/session revisions/Harness，全量Python/npm，独立复核。

平台不新增业务岗位、流程、权限或恢复能力；U-041保持blocked，WAL全部并发/跨库原子性、热配置、真实恢复、浏览器与完整验收另验。真实模型/Docker/VPS不调用；工程模型解析型号/token/费用未返回，保持未知。
