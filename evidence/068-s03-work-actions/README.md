# 068：S03.3d 工作页执行/采用操作（U-067 / 在线 #22）

2026-11-08 05:20–05:45。上一轮把成果读出来了，这一轮补上**用户能在页面上真正推进工作**的动作：开始执行、预约调用、采用成果。**仍未调用模型**，U-067 保持 `doing`。

## 本轮用户可验证结果

「AI 工作（V1）」面板每张工作下方新增操作区：

- **开始执行** → `start_attempt {work_id}`；
- **预约一次调用** → `reserve_step {work_id}`；
- **采用成果** → 仅对 `candidate` 成果显示，`adopt_result {work_id, result_id}`；
- 所有请求都带 `organization_id`、当前 `base_version`（来自 `GET /api/v1/work` 的 `version`）与唯一请求 id；成功后自动刷新面板，失败显示「操作未完成：<原因>」，成功后显示「操作已记录：<服务端消息>」。
- 只读边界不变：不提供提交正文、不改章程、不改资源的入口；按钮无权限时由服务端 400/403 拒绝并把原因显示出来。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-work-actions.txt` | 真实 RED：先移除操作区 → 找不到「开始执行」（1 失败 / 4 通过） |
| `green-work-actions.txt` | 恢复后 5 项通过（含新用例：开始执行 → 断言 `start_attempt` + `organization_id` + `base_version`；采用成果 → 断言 `adopt_result` 的 data；并断言成功提示出现） |
| `frontend-check.txt` | `npm run check:console` 退出 0：**20 文件 / 199 项前端测试** + `tsc --noEmit` + `vite build` |

第一次 RED 的日志因证据目录尚未创建而丢失，已重做并保留；测试本身在实现之后写成，这点如实记录（与 065 相同的偏差类型）。

## 所有权与边界

- `web/console/src/api/client.ts`：新增 `api.coreWorkCommand(body)`（同源 POST `/api/v1/work/commands`，5 秒超时与既有 `request` 一致；超时不重试）。
- `web/console/src/features/work/WorkPanel.tsx`：操作区 + 成功/失败提示 + `invalidateQueries` 刷新；不使用 `window.prompt/confirm`。
- 后端未改动——本轮只补 UI 入口，命令语义与校验沿用 062–067 已交付的实现。

## 未完成 / 下一步

1. **S03.2e（关键阻塞）**：真实模型循环 infer → tool_call → 回执 → 二次推理 → `submit_result`；需要可用模型连接与有限额度。
2. **S03.3e**：成果提交表单（在页面里提交候选正文/来源，供人工复核或未来 AI 产出使用）。
3. **S03.4**：按 Work/写目标隔离与恢复；总览的目标/资料/限额表单。

因此本卡仍 `doing`。
