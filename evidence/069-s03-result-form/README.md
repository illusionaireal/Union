# 069：S03.3e 成果提交表单 + 结束执行（U-067 / 在线 #22）

2026-11-08 05:44–06:15。两个子步骤，把工作页的操作补成**闭环**：能提交候选成果（带来源引用），能按明确类别结束一次执行。**仍未调用模型**，U-067 保持 `doing`。

## 子步骤 1：提交候选成果（表单）

「提交候选成果」折叠区，字段：

- **成果标题**、**成果正文**（textarea）；
- **来源回执**：复选框列表来自该工作当前的 `steps` 与 `tool_calls` 的 `step_ref`（如 `work-overview#s1`）；没有可引用回执时明确提示"先开始执行并读取资料"。
- 只有标题/正文非空且至少选一个来源时「提交成果」才可用；提交走 `submit_result`，客户端生成 `result-<时间戳>` 作为 `result_id`。
- 服务端仍执行既有校验（来源必须在本工作存在、正文 ≤32KB、必须持有进行中的 attempt），页面只是入口。

TDD：先加测试 → **RED**「Unable to find a label with the text of: 成果正文」（1 失败 / 5 通过，见 `red-result-form.txt`）→ 实现后 6 项通过（`green-result-form.txt`）。

## 子步骤 2：结束执行（按结果类别）

有 `running` attempt 时出现「结束结果」下拉（已交付 / 失败 / 停止 / 结果未知）与「结束执行」按钮，发送 `finish_attempt {work_id, attempt_id, outcome, reason}`；`unknown` 会让该执行进入未知状态并阻塞后续执行（沿用 063 的规则）。

TDD：先加测试 → **RED**「Unable to find a label with the text of: 结束结果」（`red-finish-attempt.txt`）→ 实现后 7 项通过（`green-finish-attempt.txt`）。

## 验证

`frontend-check.txt`：`npm run check:console` 退出 0 —— **20 文件 / 201 项前端测试** + `tsc --noEmit` + `vite build`。

被测系统真实模型调用 **0** 次；未部署、未迁移真实 AU。

## 所有权与边界

- `web/console/src/features/work/WorkPanel.tsx`：新增 `ResultForm`、`AttemptActions` 两个局部组件；全部动作走既有 `api.coreWorkCommand`，带当前 `base_version`，成功后刷新、失败显示原因。
- 页面仍不提供：改章程、改资源、删除成果、绕过 attempt 的执行入口。
- 两个子步骤共用同一组文件，因此合并为一个提交（未按"每步一个提交"拆分，已在证据中说明）。

## 未完成 / 下一步

1. **S03.2e（关键阻塞）**：真实模型循环 infer → tool_call → 回执 → 二次推理 → 自动 `submit_result`；需要可用模型连接与有限额度。
2. **S03.4**：按 Work/写目标隔离与恢复（多工作并行时的冲突与恢复语义）。
3. **S03.1 UI 补全**：总览的目标/资料/限额表单（目前创建 V1 工作仍需 API）。

因此本卡仍 `doing`。
