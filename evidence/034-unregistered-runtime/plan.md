# GPT-6 Astra 规划：未登记部署的诚实投影

2026-10-31；基线dev@70e2c29。新上下文/root/astra_runtime_mode_plan，代理创建接口显式指定gpt-6-astra，只读实际源码后给完整局部计划，未改文件或宣称已执行测试。主实施为GPT-6.1 Sol；服务端解析型号、工程token/费用未由回执提供，保持未知。

核对ai_union/tests/web/ops/scripts没有持久runtime登记/绑定机制，只有投影字面值与类型/fixture。activity每秒临时文件加锁及5秒有效窗口证明宿主活性，observation按host_owner关联run；Console、CLI、service共用此机制，不含部署mode证据。

冻结最小契约：mode=unregistered、name=部署位置未登记；runtime_id/instance_id/observed_at继续null；capabilities=[]只表示没有已登记实例能力声明，不是否定工程能力。liveness及匹配running的active_run_id保留当前证据，派发算法不改；不把host身份、PID或读取时间冒作登记字段。

只改runtime_view的静态部署字段/注释，以及Resources局部部署/宿主活性中文映射。保留已有mode枚举及非本轮其他模式显示兼容；不复用将unknown译为执行待核对的通用执行标签。说明宿主活性不证明位置/托管，不加字段、注册、心跳、服务控制或权限，不改变组织业务结构。

先红后绿：旧库无登记、正式锁/活性和begin_work匹配、失去活性但running保留、新owner不认领旧run、有活性无run、paused/pause_requested/needs_review均保留；重复读取和重开Engine不建表或改变组织/事件/runs/预算。前端验证未登记的未知/确认活性和其他3个合法模式兼容。解释器本轮先核对旧路径失败，再重建固定依赖；跑全量Python/npm和独立局部复核。

不顺手统一顶层与runtime.dispatch_state：未暂停但有unknown、暂停且只有宿主活性无running时，两者算法存在差异，留下一契约切片。WAL TOCTOU、跨库非原子、实际Chromium、完整U-041与真实托管继续未验。本环境工程代理不等于AU成员、VPS或公司运营。
