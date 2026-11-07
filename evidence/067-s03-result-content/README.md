# 067：S03.3c 成果正文读取端点与下载（U-067 / 在线 #22）

2026-11-08 05:00–05:30（本轮 2 个子步骤，各自独立提交）。上一轮成果只有摘要、正文留在 AU 事务里；本轮补上"可打开、可下载"，并保持读时摘要校验。**仍未调用模型**，U-067 保持 `doing`。

## 子步骤 1：`GET /api/v1/work/results`（后端）

- 参数：`organization_id`、`id`（成果标识）。
- 返回 `{protocol:"core.work.v1", organization_id, result:{id,title,sha256,bytes,sources,status,adopted_at,…}, content}`。
- **读时重算摘要**：正文与登记的 `sha256` 不一致 → HTTP 409 `incompatible_state`，不返回正文（防止被篡改的成果当作正式成果读取）。
- 未知成果 → 400 `invalid_request`；其他 AU 的成果 → 非 200 且**不返回正文**。
- 授权沿用 `app.core_au`（当前登录主体与 AU 访问边界），不新增旁路。
- TDD：`red-s03.3c.txt`（真实 404「接口不存在」）→ `green-s03.3c.txt`（14 项 `test_core_work` 通过）；回归 `regression-s03.3c.txt` **157 项通过**（1 平台跳过）；`management-check.txt` 退出 0。

## 子步骤 2：工作页"下载"链接（前端）

- 「AI 工作（V1）」面板的成果行增加 `下载` 链接，指向同一端点（`organization_id` + `id`，`download` 属性保存为 `<result-id>.json`）。
- TDD：先撤掉链接 → `red-download-link.txt`（真实失败：找不到「下载」）→ 恢复 → `green-download-link.txt`（4 项通过）。
- `frontend-check.txt`：`npm run check:console` 退出 0，**20 文件 / 198 项前端测试** + `tsc` + `build`。

被测系统真实模型调用 **0** 次；未部署、未迁移真实 AU。

## 所有权与边界

- `ai_union/application/work.py`：新增 `result_content`——只读、重算摘要、错误码沿用既有 `CoreError` 语义（400/403/409），不写状态。
- `ai_union/server.py`：仅新增一条 GET 路由，沿用既有 query 参数与错误映射。
- `web/console/src/features/work/WorkPanel.tsx`：下载链接（同源 GET），无新增写操作。

## 未完成 / 下一步

1. **S03.2e（关键）**：真实模型循环 infer → tool_call → 回执 → 二次推理 → `submit_result`；需要可用模型连接与有限额度。
2. **S03.3d**：成果页（列表/详情/采用历史）与"已采用成果"的对外读取视图；当前只有工作页一行摘要。
3. **S03.4**：按 Work/写目标隔离与恢复；总览的目标/资料/限额表单。

因此本卡仍 `doing`。
