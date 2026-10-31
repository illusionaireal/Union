# GPT-6 Astra 已确认的规划决策

2026-10-31；基线dev@d428e87。规划代理/root/astra_dispatch_plan通过创建接口显式指定gpt-6-astra，只读核对后实际返回以下核心决定与后续消费者决定；本文件由Sol按实到消息整理，不将未收到的单独规划收口或未执行测试当作已交付。

统一优先级：任意unknown无论paused为何均needs_review；否则paused且存在持久running或host_activity.confirmed为pause_requested；否则paused为paused；最后enabled。activity覆盖dispatcher整个exclusive生命周期（run前后及watch等待），不能仅凭没有running宣告宿主已静止；owner mismatch只影响活性/active_run，不能消除持久running的暂停待核实。

snapshot只计算一次，然后将结果传runtime_view，避免两份公式漂移。保持字段/枚举，禁止改runner、Engine、真实调度/授权、next_step或成员状态。Resources本来读取两字段，无需新UI逻辑；pause_requested文案最小改为“暂停已请求，结束状态尚待确认”，不暗示已取消。

Astra另明确批准直接消费者corp.inspect_company的纯诊断修正：原非enabled就输出paused blocker会将unknown误报暂停，应使用实际engine.paused()；unresolved_execution按runs保持。真实prepare/serve/启动路径不改；公司诊断原本多源读取，不宣称原子快照。

Sol据此细化正式Engine/锁/活性、unknown/paused/持久running/owner mismatch、额度受限仍不把enabled当执行许可、临时公司诊断及两资源卡片同口径测试。先红后绿，全量Python/npm与独立工程复核后局部采用，不关闭U-041。旧解释器本轮核对失败，固定依赖已在新忽略目录恢复。

主实施GPT-6.1 Sol；规划和复核工程模型解析型号、token/费用未在回执中返回，保持未知。工程模型协作、fixture临时组织和本地SDK不算真实AU成员运行、VPS或自主经营，WAL竞态/跨库非原子、实际浏览器和完整U-041仍待验。
