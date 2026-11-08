# 105：重启恢复不变量（绿灯测试）

2026-11-08 17:30–18:00。把 [103](../103-s03-restart-recovery/README.md) 实测到的门禁写成**可通过的自动化测试**，只断言确定无疑的不变量，**不**固化 [104](../104-s03-reconcile-semantics/README.md) 里仍在待确认的"释放"语义。

## 测试：`test_restart_blocks_silent_resume_and_only_the_original_request_is_looked_up`

在 `tests/test_core_work.py`（基于 `bbe8068`，含 PR #21/#23）：

1. `run_step` 通道失败 → 回执 `model_outcome=unknown`、`budget.reserved=1`；
2. 重启 Console（同根目录）→ 旧 attempt `stale=true`；
3. 直接继续 `run_step` → **拒绝**（"该工作没有进行中的执行"），不产生新事实；
4. `finish_attempt(unknown)` 后立刻 `start_attempt` → **拒绝**（"进行中或结果未知的执行"）；
5. `finish_attempt(stopped)` 后 `start_attempt` → 成功；
6. 新 `run_step`（新 id）→ **拒绝**（"已有未决模型请求；请先核对原请求"）；
7. **原样重发原请求**（同一 id、同一 payload）→ 返回 pending 回执（`model_outcome=unknown`）；
8. 断言故障通道的 `calls` 始终为空——**拒绝与查询都没有重新派发**。

## TDD 过程（三次 RED 都是真实观察）

| 迭代 | 观察到的失败 | 修正 |
| --- | --- | --- |
| 1 | `KeyError: 'receipt'`：pending 路径直接返回回执，不再包一层 | 兼容两种形状 |
| 2 | `id_conflict`："请求标识已用于不同参数" | 必须**原样重发**原请求（同 id、同 payload），不能改 base_version |
| 3 | 通过 | — |

第 2 条本身是有价值的发现：**"用原请求 id 查询"必须原样重发**，否则库层会以 id 冲突拒绝——这既是防重放保护，也说明调用方必须保存原始请求。

## 未覆盖（挂起）

- 预约的**释放/结算**路径未断言（[104](../104-s03-reconcile-semantics/README.md)：`reconcile_step` 返回 succeeded 但预约仍在，待后台/协调者明确语义后再补）；
- 全程受控替身，无真实模型调用。

## 全量复核（本分支，含本测试）

```
Ran 715 tests in 427.305s
OK (skipped=10)
```

`python-full.txt` 为原始日志；分支 `dsh/s03-real-acceptance` 基于 `bbe8068`，只新增测试与证据，无产品代码改动。
