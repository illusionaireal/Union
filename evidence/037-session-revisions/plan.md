# Astra 规划：A06 实际 SDK 会话边界

2026-10-31，14:35起只读规划，基线dev@6ed3470。规划者实际请求GPT-6 Astra并完成返回；Sol执行。规划没有运行测试或改文件。18:36恢复时分支/基线未变，本轮沿用已冻结计划；不另造产品目标。

优先补U-041 / 028 A06：源码会话键已含连接revision、工作区revision和任职/工作版本，现有SDK回归仅证明章程切换与普通续接，源码字段不是行为证据。默认只加tests/test_session_revisions.py，有实际生产行为失败才最小修复。不提前做U-042托管，也不预设组织岗位/流程。

| 最小用例 | 必需证据 |
| --- | --- |
| 同版本对照 | 实际SDK write_file留下私有哨兵，run=continued、session=paused；重开Engine/Executor后同session/task_key续接，实际HTTP请求含旧草稿 |
| 连接revision | 正式api_connection只变同一连接revision，其他会话绑定字段不变；新session/task_key、新请求与新SDK历史无旧哨兵 |
| 工作区revision | 正式workspace.configure只变revision；同工作/任职/章程等不变，新session隔离 |
| 正式交接 | 正式handoff会同时改变member/assignment/work_version，验证整体交接隔离和新包归属；不宣称单独证明assignment hash字段 |
| 禁用连接 | 锁内factory新解析拒绝，请求/预算/run/session/checkpoint无新增；不证明已有Executor的连接快照热撤销 |
| 禁用工作区 | 新请求不提供workspace工具，替身故意返回该工具仍不得执行容器或新增命令回执/成果；文本请求及用量可以发生 |
| 在途岗位撤权 | HTTP响应回调经正式update_position仅撤workspace权限，保留produce_artifact；已提供的工具仍在执行前拒绝，容器0次，用量保留 |

正向先留可续接paused会话，不能用completed会话天然换新制造通过。核对旧完整session row、旧run/用量、非空workspace命令回执、旧thread的checkpoint/writes不变；新会话仍允许往同库写，不能比较整库字节不变。使用真实SDK读取历史，不手填session/task_key/checkpoint，不patch graph/saver/授权。

连接/workspace用例不能再次调用自动configure/bind的executor helper，且各只改变目标revision。每次后续派发只增一次请求和预算。真实部分是Engine、Runner、DeepAgents/LangGraph/SQLiteSaver及回环HTTP，模型内容和容器是明确替身，没有真实供应商、Docker或公司运行。

先定向、相关回归、全量Python与npm、独立复核。结论只可为该A06受控子集；已有Executor热更新、在途配置竞态、所有授权组合、真实供应商/容器/恢复、WAL并发/跨库一致性、A03及实际浏览器/U-041整体继续未验。工程模型解析型号、token、费用无回执，保持未知。
