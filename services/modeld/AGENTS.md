# modeld 单次模型服务

继承根 AGENTS 与 Main Chapter V1。当前新增责任依据 `specs/053-union-rewrite/s02-contract.md`、ADR-0005 的 S02 编码前细化；048 Go 兼容路径保留。此模块只做账号凭据、AU/model grant 和单次传输，不拥有组织 Engine、治理、业务工具执行、费用台账或第二套 Agent loop。

- `api-accounts.ts` 拥有独立 API profile 的输入校验与私有/公开类型。API Key 只在 modeld 私有边界内使用，不回传响应、事件或日志。
- `journal.ts` 是 modeld 请求事实、grant 与 API 账号的唯一持久化写入者。API 保存与固定 grant 必须同库事务；原 registration 是恢复标识。不可双写、读时重建或复授撤销 grant。
- `kernel.ts` 复用固定上游的单次原生流；Go 账号解析/刷新保留上游所有权，API profile 不进入 Go 目录。消息、工具、原生上下文校验与流汇总由共享路径负责。增加 profile 不能引入隐式重试、备用、媒体降级、托管工具或通用循环。
- `server.ts` 拥有内部 HTTP 角色隔离、队列与派发装配。新 POST/派发校验当前 grant；原 AU/request 的迟到事实不以撤权/取消为由删除。`action_authorized=false` 的原结果仅供取证，不授权工具执行或结果采用。
- 原生上下文绑定 AU/account/model/upstream，原生工具提议、公开参数与工具结果保持配对。不能用显示名、宿主账号或 API 账号引用转移 AU 权威。
- 严格 TDD：先观察行为 RED，再最小 GREEN，保留 Go/native/auth 回归。HTTP/SQLite 与固定 SDK 回环验证角色、事务、同 ID 冲突、撤权、取消、工具/native、超时与不重试；测试只能使用临时目录及回环供应商，不读取真实凭据。
- 使用仓库固定 Node 与 Bun 1.4.2；按根开发流程运行 `test:model-service` / `build:model-service`。受控测试、实际供应商、用户验收和持续运行分别记录证据。变更 vendor 固定子模块与真实模型调用需各自范围依据。
