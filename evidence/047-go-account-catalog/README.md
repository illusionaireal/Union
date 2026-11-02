# 047：展示 Go 订阅的工作区、额度与可用模型（U-059）

2026-11-03。用户要求：显示已连接账号与套餐信息，列出 Go 可用模型并可选。

## 实现

- 新增只读接口 `GET /api/subscription-account`（平台管理员）：从本机账号服务读取
  `/api/experimental/usage/limits`（工作区名、官方用量链接、滚动/每周/每月额度百分比、是否已达上限、重置时间）、
  `/api/integration/opencode`（已连接账号数量）、`/api/model`（模型目录）与 `/api/model/default`（官方默认模型）。
  只投影白名单字段：不返回 `settings`、`headers`、`baseURL` 或任何凭据。
- `/models` 的 OpenCode Go 卡片新增：工作区名、官方用量链接、已连接账号数、三个额度窗口、可用模型下拉选择；
  选中后显示上下文/输出上限/工具能力与是否为官方默认，并可复制模型 ID。
- 后端与前端各补测试。

## 验证

- `tests.test_subscriptions`：22 项通过（新增目录投影与权限用例）。
- 前端 `SubscriptionConnections.test.tsx`：8 项通过（新增工作区/额度/模型选择用例）。
- `npm run check` 通过（47 项前端），Python 全量 **404 项**通过。
- 部署后实际 Chrome 检查（自签证书仅测试放行）：卡片显示
  `工作区：Default · 官方用量 · 已连接 3 个账号`，
  `滚动 1%`、`每周 2%`、`每月 2%` 及各自重置时间，模型下拉 **30 个可用**（Iceman / Kimi K3.1 Pro / MiniMax M3.1 / Gemini 4 Argon / Claude Haiku 5.5 / GPT-6 Luna …）。截图见 `browser/go-account.png`。

## 边界与未实现

- **选择模型目前只在本页展示参数并可复制 ID，不写入任何配置**，也不会以订阅身份发起模型调用。当前版本的原生账号服务没有 OpenAI 兼容端点（`/v1/*` 返回网页），AI-UNION 的模型连接走的是 HTTP 适配器，两者尚未打通。
- 额度百分比来自官方账号服务，是订阅用量参考，不是 AI-UNION 的费用账本；本批未新增任何费用口径。
- 已连接 **3 个** opencode 账号（历次尝试累积），本轮不合并、不去重。
- 真实模型调用 0；授权成功与目录可见都不等于 Go 模型权限或 AU 执行能力已验证。
