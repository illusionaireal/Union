# 045：首次访问认领管理员（U-057）

2026-11-02。用户要求取消“必须从宿主链接设置管理员”的门槛：未设置账号时，第一个打开工作台的人即可设置管理员；设置失败或认领有误则由宿主重置。实现范围仅限控制台身份入口，未改组织、模型调用与部署权限模型。

## 变更

- `ai_union/identity.py`：匿名（无会话 cookie）且账号为空时允许设置管理员；账号唯一，设置成功后不能重复认领；匿名认领默认不授予平台管理，仅当宿主设置 `UNION_FIRST_CLAIM_PLATFORM_ADMIN=1` 时授予；带 cookie 但无效/过期的请求仍按会话错误处理，不落入匿名路径。
- `ai_union/server.py`：`/api/auth/status` 的 `can_setup` 与后端规则一致（未设置账号，且会话为空或无组织限制的 board）。
- `web/console/src/pages/Identity.tsx`：未设置账号时直接显示设置表单，已设置后显示登录页与恢复入口。
- `scripts/reset_owner.py`：宿主重置入口。先备份数据库（0600），只删除 `owner_account`/`login_sessions`/`login_limit`，不动组织、连接和订阅记录；缺表直接拒绝，占用/损坏给出明确错误。
- 文档同步：`docs/MODEL_ACCESS.md`、`docs/CONSOLE.md`、`docs/product-design.md`、`docs/FRONTEND.md`；主账 U-057。

## 验证（NAS，2026-11-02）

- `python -X utf8 -m unittest discover -v`：**401 项通过**（99.192s），含新增的匿名并发认领、过期 cookie、平台开关、重置脚本用例。
- `npm run check`：管理/历史/Node 检查、TypeScript、37 项前端、构建通过；产物 `index-XMoHdoib.js`。
- 独立只读复核：见[复核](../docs/reviews/2026-11-02-anonymous-first-claim.md)。复核提出的平台管理越权与重置脚本失败模式已修正。
- 部署：NAS checkout 快进到 `19c6dd2` 后应用本批改动，前端重建，`ai-union-console` 以 `UNION_FIRST_CLAIM_PLATFORM_ADMIN=1` 重建；`/api/auth/status` 返回 `configured:false, can_setup:true`，匿名 `POST /api/auth/setup` 的口令策略错误按预期返回 401 且未创建账号。

## 边界

- **未做**真实账号认领（会占用唯一管理员名额）与截图归档、并发压测、NAS 重启后的窗口复测；设置表单已用实际 Chrome 检查（见 `browser/identity-form.json`），但不等于真实认领验收。
- 领取窗口从“账号为空”持续到有人认领为止，这是用户确认的产品选择；宿主重置会重新打开窗口。
- 既有一次性票据仍可换取 `platform_admin` 会话（本轮之前已存在），账号建立后是否停发票据留给后续任务；匿名认领无来源审计。
- 真实模型调用 0；订阅最终登录、组织持续运营、发布与长期运行验收不因本批改变。

## 2026-11-02 补：登录/设置表单轮询重挂载修复

用户报告“输入密码时整个页面都刷新了”。用 Chrome（playwright-core，自签证书仅本次测试放行）实测确认：工作台每 4 秒轮询 `/api/session` 并拿到 401，`IdentityBoundary` 把工作台的 `loading` 当成身份加载状态，每次轮询都先渲染占位再渲染表单，表单被卸载重挂；11 秒内面板重挂 3 次，输入内容清空、焦点丢失——这就是用户看到的“刷新”。

修复：身份边界只依据 `/api/auth/status` 的首次读取决定是否显示占位，拿到数据后表单保持挂载；工作台轮询改为仅在读取成功后继续（匿名状态下不再每秒打 401）。新增 8 项组件测试，其中“后台刷新不丢输入”的回归用例已在旧组件上实际验证会失败。

修复后同一实测：11 秒内面板重挂 0 次，账号与密码输入保留、焦点留在原字段，401 从每轮一次降为首次一次；用 6 位密码点击提交时只触发浏览器长度校验，0 次 `POST /api/auth/setup`、0 次页面导航。
