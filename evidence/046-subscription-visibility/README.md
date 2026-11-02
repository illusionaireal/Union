# 046：订阅授权结果在刷新后保持可见（U-058）

2026-11-02。用户报告：在 OpenCode 官方页面完成授权后，AI-UNION 前端没有变化，刷新也没有。

## 现场核查

- 服务端回执：`subscription_commands` 中本次 `authorize_go` 于 `2026-11-02T13:49:11Z`（本地 21:49:11）状态为 `succeeded`，消息“账号授权已保存”。轮询线程正常结束，不是授权失败。
- 原生服务：`GET /api/integration` 中 `opencode` 有 3 个 oauth 连接（此前两次尝试已各留下一个），因此卡片在此之前就显示“认证已保存”。
- 结论：授权本身成功；用户看不到变化，是因为**唯一会变化的回执面板只在当前浏览器会话里可见**——回执 id 存在 `sessionStorage`，键里含 `service_instance` 与 `session_scope`，换会话、换标签或服务重启后就取不到；而成功的回执又不会进入 `pending` 列表。卡片状态本身没有可观察的“最近成功时间”，所以“已连接”与“刚刚连上”看起来完全一样。

## 变更

- `ai_union/subscriptions.py`：`/api/subscriptions` 的 `providers[]` 增加 `last_success`（该供应商最近一次成功授权的 `created_at`，只投影时间，不含回执正文、URL、设备码或凭据）。
- `web/console/src/pages/SubscriptionConnections.tsx`：卡片显示“· 最近授权 <本地时间>”，刷新后仍能看到授权落地的证据。
- 测试：后端新增“成功后刷新可见、unknown 不改写”用例；前端新增“刷新后仍显示最近授权”组件用例。

## 验证

- Python `tests.test_subscriptions`：20 项通过（含新增用例）。
- 前端 `SubscriptionConnections.test.tsx`：7 项通过（含新增用例）。
- 部署后实际 Chrome 检查（自签证书仅测试放行）：`/models` 的 OpenCode Go 卡片显示
  `认证已保存 · 模型能力未验证 · 最近授权 2026/11/2 21:49:11`，与数据库回执时间一致。

## 边界

- 没有复现用户当时的标签/会话状态，因此不能断言“当时页面一定没有刷新过”；本批只保证结果在刷新后可见。
- 重复授权会累积多个原生连接（当前 3 个），本轮不合并、不去重；是否限制重复连接留给后续任务。
- 真实模型调用仍为 0；授权成功不等于 Go 模型权限、AU 绑定或组织执行能力已验证。
