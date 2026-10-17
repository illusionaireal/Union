# 010 权限、资源与恢复独立复核

依据 AGENTS.md，权限与资源实现由另一工程角色 agent_protocol_review 只读复核。审查范围：bootstrap、Harness、普通消息传输、进度结算、Runner、工具往返探测。只使用真实 SDK 与本地 HTTP 替身，无真实模型调用。

## 发现与关闭

1. P1：历史连接 Key 可经二层 JSON 参数或普通正文进入 SDK 检查点；响应头 x-request-id 也可能进入公开 usage。修补：所有已保存连接版本的凭据在请求、解码后的消息和参数保存前检查；污染回执元数据丢弃，APIExecutor 默认覆盖 probe 和旧适配器。已用轮换 Key、Unicode 转义参数、正文和响应头复验。
2. P1：HTTP 已完成但本地成果校验或 SDK 工具异常时，数据库可能丢失已取得 token。修补：Harness 异常出口保留 usage；本地非预期异常为 known failed；超长正文及 StateBackend.write RuntimeError 注入复验，tokens 20/10 保留。
3. P1（最终增量）：畸形参数修正的进度结算若因在途修章被拒绝，异常可能逃出统一失败处理，留下 running/usage=null。修补：修正进度及已取得用量从 Harness 正常返回，在 Runner 原 try 中结算；拒绝进入统一 fail_run。定向复现确认仅一次 HTTP、run=failed、tokens 20/10 保留、recover=0。原始未解析参数不进入检查点或反馈。

## 独立边界验证

- 修章、交接、修改工作后均新建会话，不向下一次请求发送旧会话 canary。
- 撤销 create_work 后成立被拒绝，正式 members/positions/work 全为零，草案和失败调用用量保留。
- 工具检查点落盘后注入 unknown，未核对前 HTTP 数不增加；明确 abandon 后新会话不重放旧工具消息，可继续使用宿主草案。
- 成立依旧经过绑定身份、当前授权、原始版本及事务提交；草案不是正式成员。
- 一次实际模型调用一次预约，框架默认子 Agent 和自动摘要调用关闭。
- 工具探测分别预约两次调用，普通问候不能通过能力验证。
- 最终增量复验 run、watch、网页三入口的单步限制及连续参数错误停止；当前 Key 正文拒绝后也保留已取得 token。

最终复核结论：上述 P1 已关闭，当前权限、资源与恢复审查无剩余阻塞项。真实供应商、模型业务能力和质量验收另行记录。
