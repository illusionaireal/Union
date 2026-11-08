# 109：22-A 页面接入自动执行与原请求核对（DSH）

2026-11-08 22:50–23:00。看板 #22 的 **22-A** 要求「页面实际接入自动 run_loop 与原请求恢复，停止扩展手工记账入口」。此前工作面板只有手工动作（开始执行、预约一次调用、结束执行、提交成果等），**没有任何自动执行入口**。

## 变更（仅前端）

`web/console/src/features/work/WorkPanel.tsx` 新增 `AutoRunActions`，渲染在工作动作区：

1. **有进行中的执行尝试时**显示「自动执行（连续，最多 3 步）」→ `run_loop`（后端已有 turn cap，前端不重复限制）；
2. **存在 `unknown` 步进时**显示提示「存在未确认的原模型请求：work-xxx#s1，核对完成后才会记账为已用」+「核对原请求」按钮 → `reconcile_step{status:"used"}`。
   - 这里刻意**不提供"手工释放"**：按 codex-home 复核结论，未确认的原请求不可手工释放，只有确认完成才记账为 used。

没有新增任何手工记账入口（22-A 明确要求停止扩展），也未改动其它页面。

## 测试（严格 TDD：先写测试并观察失败）

`WorkPanel.test.tsx` 新增 2 项：
- `runs the automatic loop from the work panel when an execution is active`：点击「自动执行」→ 断言 `coreWorkCommand` 收到 `kind: 'run_loop', data: {work_id}`；
- `offers original-request reconciliation when a step outcome is unknown`：渲染 unknown 步进 → 断言提示文案出现，点击「核对原请求」→ `kind: 'reconcile_step'`、`step_id: 'work-overview#s1'`、`status: 'used'`。

第一次运行 `check:console` 失败于 `error TS2552: Cannot find name 'userEvent'`（该测试文件只用 `fireEvent`），改为 `fireEvent.click` 后通过——属真实 RED→GREEN。

## 验证

```
npm run check:console
 Test Files  21 passed (21)
      Tests  208 passed (208)   ← 原 206，+2
 ✓ built in 8.10s
```

`console-check.txt` 为完整日志。

## 边界与未做

- 未运行真实模型调用（本轮 0 次）；本项是 UI 接入，真实出口仍见 [108](../108-s03-real-exits/README.md) 的 22-B/22-C 失败记录；
- 未做浏览器级验收（`npm run test:workspace` 需要构建产物与 Chromium；如需我可补跑）；
- 未提交后端改动，未触碰他人文件。

## 追加验证（22:57）

| 检查 | 结果 |
| --- | --- |
| `npm run check`（管理/计划/node 测试/console） | **退出 0**：208 前端测试通过、构建成功 |
| `npm run test:workspace`（真实 Chromium 浏览器验收） | **71 项通过**，`real_model_calls: 0` |

日志：`npm-check.txt`、`browser-workspace.txt`。浏览器验收在工作面板上跑通既有用户流程，说明新增的自动执行/核对按钮没有破坏原有交互。
