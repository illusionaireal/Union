# 103：重启恢复的实际序列（受控、离线实测）

2026-11-08 17:40–18:00。为 #22 第 6 项「中断/未知原请求核对与**重启恢复**」补证据：在已 rebase 到 `bbe8068` 的树上（含 PR #21/#23 的派发与回执实现）实测"宿主重启后如何恢复"，而不是只引用 modeld 源码。

## 实测到的恢复门禁（按出现顺序，均为真实回执文本）

| 步骤 | 调用 | 结果 |
| --- | --- | --- |
| 0 | 造一个未知结果步进（`failing_transport`） | 回执 `model_outcome=unknown`，`budget.reserved=1`，步进 `unknown` |
| 1 | 重启 Console（同一根目录，新实例） | 旧 attempt 的 `host_instance` 仍是旧实例、`stale=true`；步进仍 `unknown` |
| 2 | 直接用旧 attempt 继续 `run_step` | **拒绝**："该工作没有进行中的执行"（stale 不能续跑） |
| 3 | `finish_attempt(outcome=unknown)` | 成功；attempt → `unknown` |
| 4 | 立刻 `start_attempt` | **拒绝**："该工作已有进行中或结果未知的执行；请先结束它" |
| 5 | `reconcile_step(released)` | 成功；步进 → `released`，`reserved` 归零 |
| 6 | 再次 `start_attempt` | **拒绝**："该工作已有未决模型请求；请先核对原请求" |
| 7 | 未决派发意图 | 必须用**原请求 id** 再发一次 `run_step` 取回 pending 回执（`work_dispatch_prepare` 事件存在 → 不重新派发） |
| 8 | 旧 attempt 再 `finish_attempt(outcome=stopped)` | 成功；attempt → `closed` |
| 9 | `start_attempt` + 新 `run_step` | 才能继续 |

## 结论

- 产品**不会**在重启后静默续跑或静默重放：stale attempt 被拒绝，未决派发意图要求"用原请求核对"，两条门禁都不是靠文档约定，而是回执里可见的拒绝。
- 恢复不是"一次 reconcile 就完"，而是**三步**：结束旧 attempt（unknown）→ 核对步进（released）→ 用原请求 id 取回 pending 回执 → 关闭旧 attempt（stopped）。这条序列此前没有写在任何证据里，属于本次实测得到的新事实。
- 第 7 步的"原请求 id"是客户端自己发出的 id；服务端不猜测、不代选，符合"未知外部结果需原请求查找/核对"。

## 未完成与边界

- 含第 7 步的**完整绿灯测试尚未写成**：需要在同一测试里复用固定 request id 驱动 run_step→pending→reconcile→close→new attempt，本轮预算到点，未及收尾；已回滚克隆里的半成品测试，不留在产品分支。
- 全过程为受控替身（`failing_transport`），**未发真实模型调用**；真实中断证据另见 [100](../100-s03-real-interrupt/README.md)。
