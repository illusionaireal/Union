# 028 验收覆盖矩阵（子集）

2026-10-31；测试文件[tests/test_runtime_http.py](../../tests/test_runtime_http.py)。以下只记录服务端/HTTP观察证据，不将每行标成整项PASS，也不替代实际浏览器A11。所有AU、成员、资源、回执和业务成果均为临时测试fixture；Server/HTTP、Engine持久化和SqliteSaver本地检查点是真实执行的依赖。

| 项 | 本轮证据 | 仍需证据 |
| --- | --- | --- |
| A01 | 同名成员/session跨AU不串读；同AU成员引用、run与检查点归属；same_member_session_ids...及state_chain... | 与A06完整接续边界共同验收；实际界面、完整单派发/长任务场景另验 |
| A02 | state_chain...经HTTP验证ready/依赖等待、暂停、活跃、unknown、idle/预算受限；重复GET预算和表内容不变 | 实际模型等待/运行、实际React界面不由本用例证明 |
| A03 | state_chain...活动owner退出后run未确认；既有test_runtime_location覆盖新owner不认领旧run | heartbeat时间过期、旧实例迟到回执专项；不把退出当时间过期 |
| A04 | legacy_unconfigured...旧库无session/workspace表仍不建表；unregistered/virtual_only，重复读不写业务数据 | WAL预检至连接竞态、跨库一致性；真实迁移/任意并发零文件写入不作承诺 |
| A05 | session_roles...限域board/observer与目录过滤；无/伪造/过期cookie401、跨AU403；forged...参数不扩权、写入403/未知命令409/路由404；same_member...完整JSON私有哨兵排除 | 宿主创建的全局会话按现有全AU授权读取，不等于普通成员权限；公共多租户身份系统未实现 |
| A06 | current_authority...工作区禁用/重绑、章程撤权、交接经HTTP反映当前许可，不借旧session；真实历史根checkpoint仍只提示requires_validation。既有Harness实际SDK章程变化回归 | 连接revision、工作区revision、任职变化分别执行新会话并验证旧消息不复用、历史保留；安全恢复未验 |
| A11/A12 | 本轮无新增通过声明 | Chromium实际桌面/窄屏/断网乱序；原公司真实主机、供应商、恢复和持续窗口 |

全部成功GET经read_stable三次读取，核对组织表定义与全部内容、预算、检查点文件集合及非SHM哈希；允许snapshot_sequence/采集时间变化。recover、派发、模型chat、Harness、容器、SDK setup/get_tuple设失败哨兵。checkpoint正文由真实SDK put构造，但session元数据是显式fixture，没有模型或容器执行。只读结论限定稳定本地fixture；SHM字节与并发WAL边界不隐瞒。

下一最小切片优先A06真实SDK会话隔离：分别改变连接revision、工作区revision、有效任职；验证新session/task_key、旧消息不进入后续请求、旧session/checkpoint/回执保留且当前权限重新检查。然后A03直接时间过期和旧owner迟到回执，不扩展托管控制。
