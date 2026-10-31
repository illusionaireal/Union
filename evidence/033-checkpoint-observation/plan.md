# GPT-6 Astra 有界规划

2026-10-31；基线dev@c120a6c。新上下文/root/astra_checkpoint_plan通过创建接口显式指定gpt-6-astra。本轮模型已恢复响应并完成源码核查、完整契约/验收及WAL后续澄清；不是沿用上轮未完成规划或替换模型后冒称Astra。

计划选择“检查点存在性与接续提示纠偏”。原_session仅按paused/running/failed推断has_checkpoint，并在paused时输出possible，两个结论均缺独立依据。改为boolean|null：固定本AU检查点数据库、根namespace/thread记录存在true，确定缺失false，无法核查null；不读正文。必须同步去掉possible，按run/session实际状态保守给not_available/requires_validation/requires_reconciliation/unknown。

落点为runtime_view私有元数据读取与_session、observation传当前受信engine.root、前端类型及单行三态文案；不改Harness恢复、授权、派发、托管或组织业务结构。测试用正式Engine与真实安装SDK的本地checkpoint fixture，不调用供应商。候选会话的历史记录存在不等于当前task_key/权限仍有效。

Astra明确禁止SqliteSaver.get_tuple/get_state/setup：本地实现会建表并读取/反序列化正文。采用URI mode=ro、query_only、短超时、参数SELECT 1，不用immutable忽略WAL；旧库/文件缺失不创建目录或表，错误不泄露路径/异常文本。

实施探测发现已关闭的WAL库即使mode=ro也可能补建sidecars。Astra后续认可：仅读前20字节格式元数据，WAL且既有-wal/-shm缺任一直接null，不开SQLite；live writer场景验证真实WAL记录可见，closed SDK场景验证unknown且无新文件。Astra特别指出预检到连接存在TOCTOU，不得宣称任意并发下绝对零文件；若要该绝对保证必须另行解决读写协调，不能扩大本切片或为追求true改journal模式。

验收包括：会话状态与存在性解耦；root namespace、不同thread/AU、交接隔离；未知/核对后/inflight执行优先级；坏库/兼容/读取错误；真实SDK WAL与已关闭库；重复读取/重开Engine的业务状态、预算、事件和文件集合；SQLite authorizer拒绝正文列；前端三态；全量Python/npm及独立复核。U-041保持blocked，部署与完整观察/浏览器门槛不关闭。

规划代理未改文件，规划不是实施通过声明。主实施为GPT-6.1 Sol；服务端解析型号、工程token/费用未由回执提供，保持未知。此工程分工不是AU成员自治或真实公司运行。
