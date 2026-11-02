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

- **未做**真实浏览器认领与截图验收、并发压测、NAS 重启后的窗口复测；UI 变更只覆盖类型检查、单元/组件测试与构建，不等于浏览器验收。
- 领取窗口从“账号为空”持续到有人认领为止，这是用户确认的产品选择；宿主重置会重新打开窗口。
- 既有一次性票据仍可换取 `platform_admin` 会话（本轮之前已存在），账号建立后是否停发票据留给后续任务；匿名认领无来源审计。
- 真实模型调用 0；订阅最终登录、组织持续运营、发布与长期运行验收不因本批改变。
