# 039 覆盖与明确剩余风险

| 场景 | 本轮证据 | 结论范围 |
| --- | --- | --- |
| WAL预检后最后writer关闭 | [race-before](race-before.json)：writer关闭后主库正常落盘，随后观察新增wal/shm；两项red回归 | 实际SQLite 3.53.1/SDK受控复现；不是公司或真实模型运行 |
| 已识别WAL的观察 | [race-after](race-after.json)：None、connect0、无新增文件；新增回归文件集合与含SHM全部hash不变 | 该分支不进入SQLite，不再依赖sidecar门槛 |
| WAL存在/缺失会话 | 有真实SDK目标根行仍unknown，missing-session也unknown，不猜false | 存在性可见度有意退让 |
| 非WAL正例/隔离/正文 | 仅fixture的实际SDK写后转DELETE；thread/namespace/AU隔离、authorizer拒checkpoint/metadata/writes正文、mode=ro与connect错误仍覆盖 | 不是修改生产Harness journal模式；不宣称所有非WAL并发安全 |
| HTTP | 同ID跨AU显式非WAL true/false正例；当前授权变化场景保持真实WAL，has_checkpoint=None/resume_state=unknown | 保留资料边界和隔离证据，不把unknown当无检查点/可安全恢复 |
| DELETE预检后外部切WAL | race-after仍返回true，观察仍可新增wal/shm | **已实证、未修复的剩余竞态**；不是推测或已通过项 |
| 路径替换、跨库、真实恢复 | 本轮未闭合 | U-041不关闭，真实模型/容器/主机/浏览器验收不提升 |

生产变更只在runtime_view._checkpoint增加WAL早退并删除原sidecar预检；无immutable、复制、backup、SDK setup/get_tuple、journal更改或新授权。三态接口不变，普通SDK WAL现在通常展示“检查点状态未知”。historical033 live WAL可见的受控结果是当时行为，当前以039契约为准。
