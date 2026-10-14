# 实施方案

沿用 Python 标准库、SQLite 事务、现有进程锁和 command/session 协议。

1. `model_api.py` 提供连接配置校验、私有版本表和 API 执行器。配置与绑定由受信董事会管理，与状态版本和回执同事务；API Key 在命令持久化前替换为参数指纹。
2. 显式选择 `json_schema` 或 `json_object`，以及 `max_completion_tokens` 或 `max_tokens`；不自动降级或再次请求。普通 JSON 模式也由宿主完整验证协议。
3. HTTP 采用单请求、禁重定向、有界响应和整体截止时间。API 执行在后台线程，调用方到期后停止等待并标为 unknown；失效线程不得在连接返回后继续发送。
4. 固定连接元数据写入每次运行的执行依据，密钥不传给模型。API 用量沿用整数 token 与 unknown cost，并附来源及请求标识。回环服务标为 local_test。
5. `api_connection`、`api_binding`、`api_test` 命令和 `GET /api/model-connections` 供前端接入；`start.executor=api`。API 默认可配置，但实际调用必须明确接受未知费用与有限额度。
6. CLI 配置从 JSON 读非秘密字段，API Key 从环境变量或私有文件读取，不接受命令行明文参数。

参考（2026-10-13 核对）：https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create 与 https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat 。选 Chat Completions 是为了首轮兼容接入，不宣称兼容所有供应商或支持 Responses/Anthropic 原生协议。
