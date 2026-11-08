# 082：通道失败＝结果未知（保留预约 + 显式核对）（U-067 / 在线 #22）

2026-11-08 06:49–07:20。按 R-05「外部结果未知必须先核对、不得盲目重放」补上自动执行的**中断语义**：模型通道失败时不再当成"什么都没发生"，而是**留下一次已预约、结果未知的步进**，等宿主核对。

## 本轮用户可验证结果

`run_step` 遇到通道异常（超时/连接中断）时：

- 回执：`status: succeeded`（记录这件事本身成功）、**`model_outcome: "unknown"`**、`step` 指向新步进、`cost_status: "unknown"`、消息说明"已保留该次调用预约等待核对，不自动重放"。
- 工作状态：新增一条 `status: "unknown"` 的步进；**调用预算保留**（`budget.reserved` +1），不会被静默退回。
- 新增 `POST /api/v1/work/commands`：`kind: reconcile_step`（`data: {work_id, step_id, status, reason}`）——只有 `unknown` 步进需要核对，核对结果必须是 `used` / `released` / `failed`，必须写依据；`released` 才会把预算退回。

## 为什么回执是 succeeded 而不是 unknown

`governance_store.read_in` 有一条硬不变量：**只有 `succeeded` 回执才能伴随状态变更**（否则报"治理回执与有效状态不一致"）。保留一次未知预约本身是成功的状态变更，所以回执 `status: succeeded`，而把"模型结果未知"作为独立字段 `model_outcome` 表达——语义分开，不靠改状态糊过去。这也是本轮先踩坑后修正的地方（见下）。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-unknown.txt` | 真实 RED：通道失败被当成"未产生事实"，没有未知步进、预算未保留、无 `reconcile_step` |
| `green-unknown.txt` | 27 项 `test_core_work` 通过：通道失败→`model_outcome=unknown` + `step.status=unknown` + `budget.reserved=1`；`reconcile_step(released)` 后 `budget.reserved=0` |
| `regression-unknown.txt` | 相关回归（work/governance×3/models/console/workspace/documents/creation/isolation） |
| `management-check.txt` | `npm run check:management` |

**过程中踩到并修正的两处**（如实记录）：

1. 最初用 `receipt.status = "unknown"` 且改状态 → 触发治理不变量"治理回执与有效状态不一致"（服务端拒绝、测试端连接中断）。改为 `succeeded` + `model_outcome`。
2. 最初放宽 `settle_step` 允许对 `unknown` 再结算，撞上既有测试断言（未知步进不可改判）。改为**新增显式 `reconcile_step`**，`settle_step` 语义保持不变。

## 所有权与边界

- `ai_union/domain/work.py`：`fail_step()`（预约后立即标记 unknown、保留预算）、`reconcile_step()`（只处理 unknown，必须写依据）、`run_step`/`reconcile_step` 输入形状；`settle_step` 仍只接受 `reserved`。
- `ai_union/application/work.py`：通道异常走 `unknown_step()`（单事务：记未知步进 + succeeded 回执 + `model_outcome`）；`reconcile_step` 命令走既有命令框架。
- 未引入自动重放、未把未知当成功、未动预算上限。

## 未完成 / 下一步

1. **真实通道接线 + 有界真实验收**（唯一实质阻塞，需网络/宿主通道）：OpenCode Go ≤2 次调用、≤1024 输出 tokens、仅合成资料。
2. 未知步进对**工作推进**的阻塞策略：当前允许其他步进继续（局部恢复），是否要把"该工作有未知步进"作为派发阻断，留给 S06 的恢复语义一起定。
3. 用量并入 AU 资源账（当前为步进级记录）。

因此本卡仍 `doing`；本轮真实模型调用 **0**。
