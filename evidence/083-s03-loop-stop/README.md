# 083：自动循环的终止修正（未知即停 + 轮次跟随预算）（U-067 / 在线 #22）

2026-11-08 06:54–07:25。修掉 082 之后暴露的一个真实缺陷：**某一回合结果未知时，`run_loop` 会继续再调一次模型**，既违反 R-05（未知先核对、不重放），也可能在未知态下多花一次调用。同时把轮次上限从固定 3 改为**跟随该工作剩余调用预算**。

## 本轮用户可验证结果

- **未知即停**：`run_step` 返回 `model_outcome: unknown`（通道失败、已保留预约）时，`run_loop` 立刻停止，聚合回执为 `status: unknown`、`model_outcome: unknown`、`turns: 0`，并保留那 1 次预约；**不会发起第二次模型调用**。
- **轮次跟随预算**：循环轮次 = `min(3, 该工作剩余调用数)`。示例：`max_calls=2` 的工作即使模型每次都只要求工具，也只执行 2 个回合（`turns=2`），不会超出授权额度。
- 预算已用尽时 `run_loop` 直接拒绝（"该工作的调用上限已用尽"），不发起调用。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-loop-stop.txt` | 真实 RED：① 通道失败后循环仍在继续（步进数 >1）；② `max_calls=2` 的工作被跑了 3 回合 |
| `green-loop-stop.txt` | 29 项 `test_core_work` 通过（含上述两例与既有 27 项） |
| `regression-loop-stop.txt` | 相关回归（work/governance×2/models/console/workspace/documents/creation/isolation） |
| `management-check.txt` | `npm run check:management` |

过程中修掉自己一处测试夹具错误：新用例忘了先 `prepare_materials()`（宿主未登记资料目录），导致步骤被正确拒绝——是测试漏准备，不是产品问题。

## 所有权与边界

- `ai_union/application/work.py`：`run_loop` 在启动时读取该工作剩余预算并据此确定 `turn_cap`；每回合后检查 `model_outcome`，未知即停并原样上报；聚合回执带 `model_outcome`（仅未知时）。
- 领域规则未改（`budget()`/`reserve_step`/`fail_step` 复用），仍然"未知保留预约、核对后才释放"。

## 未完成 / 下一步

1. **真实通道接线 + 有界真实验收**（唯一实质阻塞，需网络/宿主通道）：OpenCode Go ≤2 次调用、≤1024 输出 tokens、仅合成资料；届时 `turn_cap` 自然收敛到 2。
2. 未知步进是否阻断整个工作的后续派发（当前允许其他步进继续，属局部恢复；与 S06 一并定）。
3. 用量并入 AU 资源账（当前为步进级记录）。

因此本卡仍 `doing`；本轮真实模型调用 **0**。
