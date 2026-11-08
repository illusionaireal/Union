# 104：重启恢复实测发现的语义问题（复核发现，供 #22/#23/#24 处理）

2026-11-08 17:20–18:10。为 #22 第 6 项补"重启恢复"绿灯测试时，在 `bbe8068`（含 PR #21/#23）上实测到一条**回执语义与调用者预期不一致**的行为。这不是我的代码，故按"复核发现"上报，不擅自改他人实现。

## 实测序列与回执（受控替身，无真实调用）

1. `run_step`（通道失败）→ 回执 `model_outcome=unknown`，`budget={max_calls:4, reserved:1, used:0}`，步进 `unknown`。
2. 重启 Console（同一根目录）。
3. 旧 attempt：`host_instance`=旧实例、`stale=true`；继续 `run_step` → 拒绝："该工作没有进行中的执行"。
4. `finish_attempt(outcome=unknown)` → 成功。
5. `reconcile_step(status=released)` → **回执 `status=succeeded`**，但 **消息是"原模型请求仍未确认；保留预约，不重新派发"**，且**步进仍为 `unknown`、`budget.reserved` 仍为 1**。
6. `finish_attempt(outcome=stopped)` → 成功；`start_attempt` 成功。
7. 新 `run_step` → 拒绝："该工作已有未决模型请求；请先核对原请求"。
8. 用**原请求 id** 再发 `run_step` → 返回 pending 回执（`model_outcome=unknown`，不重新派发）。

## 问题（建议）

**`reconcile_step` 在"原请求未确认"时返回 `succeeded` 却不改变任何状态。** 调用者（含未来 UI）会据此认为"已释放预约"，但实际 `reserved` 仍为 1、步进仍 `unknown`。建议二选一：

- (a) 回执改为 `status=rejected`（或 `outcome=kept_pending`）并给出确认原请求的下一步（例如 modeld 的 `GET /v1/requests/<id>` 状态、或 `cancel` 结果如何记账）；
- (b) 保持 `succeeded`，但增加 `effect=kept_pending` + `reservation: {reserved: 1}` 字段，让调用者无需二次读取即可知道预约未释放。

同时请明确**未决派发意图由哪个命令结算**：实测中 `reconcile_step` 之后 `reserved` 仍为 1，若没有任何命令能结算它，等于预算永久占用（重启后尤其危险）。这是 #22 第 6 项"重启恢复"能否闭环的关键。

## 边界

- 受控替身、无真实模型调用；真实调用累计仍为 2/2。
- 我没有改动 `ai_union/` 的产品代码，也没有把半成品测试留在分支；本轮只提交本证据。
- 绿灯测试待上述语义确定后再补：它必须断言"取消/确认后预约确实归零"，否则只是把不确定行为固定下来。
