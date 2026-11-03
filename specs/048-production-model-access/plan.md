# 048 实现计划

唯一当前状态见`management/project.json`。先完成最短真实业务链，再扩大profile；所有切片属于同一正式模型服务，不另建演示系统。

## A：Go订阅真正驱动现有AU（衔接已有U-060）

先复用044已经明确的Go远端端点、受限组织头及目录创建连接工作；U-060不重复编号或覆盖。静态导出token在正式交付前接入动态续期，A的最终出口仍是实际员工工作与反馈。

1. 在实际部署机读取受管OpenCode版本和服务能力，定位当前有效账号/工作区；只读取脱敏元数据，不复制凭据到仓库。
2. 构建固定源码版本的模型服务，保留上游锁文件和许可；仅暴露内部协议，不启用OpenCode内置业务工具/完整Agent loop。
3. 打通integration→credential→remote provider config→model resolver→单次stream。桥接必须执行订阅必要hooks；严禁将4097直接当作`/v1/chat/completions`。
4. 实现宿主账号授权给AU的grant，持久化Go连接与默认/岗位绑定；账户状态、连接状态和最后真实运行状态分开显示。
5. 在`harness.py`增加`ModelServiceTransport`，沿用组织工具循环、checkpoint、预约和动作回执；模型服务返回工具调用，Python执行并回传工具结果。
6. 修改`SubscriptionConnections`的采用操作、`Models`的生效状态和任务详情流展示；刷新续接原请求。
7. 用原AU完成一个真实业务任务，保存成果，并让其处理一次反馈。这个结果未实现前不以登录、目录、普通对话或本地替身关闭A。

## B：统一原生API和订阅

按同一入口接通ChatGPT、OpenAI API、Anthropic、Gemini、GLM及Coding Plan、Kimi及Coding Plan、DeepSeek、OpenRouter、New API、自托管；云身份补Bedrock/Vertex/Azure。每种profile保存自己的实际端点、区域、model映射和认证方式，前端不要求用户猜参数。

落实完整Message/ContentPart/native envelope。保留Responses reasoning/encrypted项、Anthropic thinking/signature、Gemini thoughtSignature、工具配对、拒绝和usage；驱动负责wire映射。支持推理强度、输出预算、缓存及多模态资产。不能在Python桥接中再次压扁成旧Chat字典。

## C：持续运行与故障恢复

持久request/attempt/event/outbox；单次模型调用由Python独立预约。下层SDK透明重试关闭。实现认证刷新锁、凭据池、账号配额、冷却、队列公平性、已批准回退。原attempt查询与纯推理重新生成策略、迟到fencing和业务动作核对分别实现。

拆分connect/first-event/idle/task deadline；替换旧600秒总时限。加入上下文预算、压缩用途、资产上传及按需读取。成本沿用已有basis/版本/分摊，新增attempt去重及cache write/reasoning原始计数，重复推理费用不遗漏。

## D：正式发布与真实使用收口

与U-054一起完成固定构建、迁移、安装、升级、回滚、恢复。实际部署中完成本规格的账号/API/工具/反馈/重启链；U-002据真实结果更新。以同模型同账号同任务条件对照固定版本OpenCode/Hermes的接入完整性和开销，保存实际结果，不把目标数值填成实测值。

## 代码落点

下表为待实现文件/改动，不表示已创建模块。

| 落点 | 改动 |
| --- | --- |
| `services/modeld/` | 受管服务入口、认证/模型解析、单次stream、持久请求与事件、健康/版本 |
| `services/modeld/upstream.lock.json` | 固定上游commit、包版本、源码和补丁摘要、许可 |
| `services/modeld/patches/` | 最小集成补丁；显式账号解析、必要hooks与request隔离，不fork组织循环 |
| `ai_union/model_service.py` | 新内部协议客户端、submit/status/events/result/cancel与原请求核对 |
| `ai_union/model_api.py` | v2连接及grant引用、兼容读取、路由选择；旧直连路径迁移 |
| `ai_union/subscriptions.py` | 统一受管账号服务，新增AU采用/授权；白名单状态读取 |
| `ai_union/harness.py` | 单次调用转发、native envelope/checkpoint保留、工具返回 |
| `ai_union/engine.py`、`runner.py` | attempt预约/outbox、持久队列/迟到隔离；不扩大业务工具权限 |
| `ai_union/model_context.py`、`model_media.py`、`model_billing.py` | 语义压缩、资产引用、精确计量及归属 |
| `ai_union/server.py`、`console.py` | 同源采用命令与事件代理、按AU权限隔离 |
| `web/console/src/` | 账号模型采用、生效配置、流式任务详情、排队/恢复状态 |
| `scripts/start-console.mjs`、`ops/` | 受管服务生命周期、固定发布包、配置检查、迁移与回滚 |
| `docs/MODEL_ACCESS.md`、`docs/API_MODELS.md` | 真实使用入口，纠正过期协议描述 |

## 必须提前解决的集成约束

- OpenCode认证插件不是独立`@opencode/ai`包的一部分；完整源码构建与必要Core层依赖属于A，不留给用户解决。
- 同一上游账号的refresh token只能有一个刷新所有者；已有账号迁移必须处理原服务并存。
- 进程级active connection不得用来切换并发AU账号；采用显式作用域或隔离实例。
- Python数据库与模型服务数据库不能假装一个事务；提交前outbox、原ID查询、事件重放负责恢复。
- SDK自动重试和UNION备用重试不能同时开启；新的每次attempt必须在账本有预约。
- opaque原生状态不能跨供应商照搬；迁移或回退需要保留原始记录并建立明确的新分支。
- 新的纯推理重生成策略改变历史unknown行为，默认不追溯应用；权限与费用实现需独立工程复核。

实际开发不按预设“几天完成”承诺；每个切片以用户能完成上述真实操作作为出口，优先解决正在阻断它的具体问题。
