# 065：S03.3a 工作页展示 V1 工作（U-067 / 在线 #22）

2026-11-08 00:55–01:10。本轮做用户能看到的一步：把已经存在的 V1 工作事实（负责成员、有效授权、调用预算、执行尝试、工具回执、授权资料是否就绪）搬上工作页，而不是只在 API 里。**仍未调用模型**，U-067 保持 `doing`。

## 本轮用户可验证结果

工作页（Tasks）在选择了一个 `core_v1` AU 时，列表上方新增「AI 工作（V1）」面板：

- 每张 V1 工作显示：标题与目标、负责成员与职责、**有效授权动作**（`mandate.actions`，失效会标注）、**调用预算**（`used 已用 · reserved 已预约 · 上限 max`）、**执行状态**（执行中 / 结果未知待核对 / 本轮已结束 / 尚未开始）、**最近工具回执**（`read_document @ work-overview#1 · sha256 abcdef…` 或“N 份资料”）、**授权资料**（引用 + 宿主是否就绪 + 可读份数）。
- 空态说明「尚未登记 V1 工作」；读取失败有可重试提示；旧版工作列表保持原样。

## 严格 TDD 记录（含一处流程偏差，如实记录）

| 日志 | 内容 |
| --- | --- |
| `frontend-check.txt` | `npm run check:console` 退出 0：**20 个测试文件 / 197 项前端测试**通过，`tsc --noEmit` 与 `vite build` 通过 |
| `management-check.txt` | `npm run check:management` 退出 0 |

偏差：`WorkPanel.tsx` 与它的 3 项单元测试是**同时写成**的，因此没有为组件本身观察到 RED。为补上真实 RED，随后新增了页面级集成测试 `src/pages/Tasks.test.tsx`，先把挂载行临时撤掉运行 → **真实失败**（TL 找不到「项目概览」），恢复挂载后 → 通过。这条记录不掩盖偏差：组件单元行为缺一次前置 RED。

首次运行还暴露一个真实类型错误（`CoreWork` 导入未使用，`error TS6196`），已修；页面测试首次失败是缺少 Router 上下文（`useUrlState` 用到 `useSearchParams`），属测试夹具问题，改用 `MemoryRouter` 后通过。

## 所有权与边界

- `web/console/src/features/work/WorkPanel.tsx`（新）：只读展示，不提供任何写操作按钮；数据来自 `GET /api/v1/work`。
- `web/console/src/api/types.ts`、`api/client.ts`：新增 `CoreWork`/`CoreWorkItem`/`CoreWorkAttempt`/`CoreWorkStep`/`CoreWorkToolCall`/`CoreWorkBudget` 类型与 `api.coreWork(id)`。
- `web/console/src/pages/Tasks.tsx`：仅在存在 `core` AU 时挂载面板，旧版列表与筛选不变。

## 未完成 / 下一步

1. **S03.2e**：`step` 与真实模型请求配对（infer → tool_call → 回执 → 二次推理；失败/超时按 `unknown` 结算并核对，不重放）——这是把“AI 真读资料并产出”补齐的关键，需要模型连接与有限额度。
2. **S03.3b**：成果正文/来源保存与采用，成果页展示、下载、刷新持久。
3. **S03.4**：按 Work/写目标隔离与恢复；总览的目标/资料/限额表单。

因此本卡仍 `doing`。
