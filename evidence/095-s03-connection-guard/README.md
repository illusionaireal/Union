# 095：自动执行前重验模型连接（U-067 / S03，补边界缺口）

2026-11-08 13:24–13:50。审查处置要求"权威状态在动作与结果接受边界重验"。本轮修掉一个真实缺口：**`run_step` 只校验连接是否存在于 Agent 定义里，却不校验它在执行时刻是否仍启用的默认连接**——于是模型连接被停用后仍会发起自动执行。

## 缺口与修复

**修复前**：`start_work` 时会校验连接 revision 与默认状态；但之后治理者把连接停用或改默认，`run_step` 依旧放行（真机上等于用已停用的通道发起调用）。

**修复后**（`ai_union/domain/work.py` 的 `step_plan`）：

1. 该工作引用的模型连接必须**存在**（"该工作引用的模型连接不存在；请重新配置"）；
2. 必须**启用**（"该工作的模型连接已停用；请先启用或重新采用有效连接"）；
3. 必须是**当前采用的默认连接**（"须先采用该工作的模型连接为默认连接，才能继续执行"）。

同时 `ai_union/application/work.py` 把计划阶段的拒绝**转成回执**（与其他拒绝一致）：调用方拿到 `status: rejected` + 原因，可重放同一请求 ID，且**不产生步进、不占调用预算**。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-guard.txt` | 真实 RED：连接停用后 `run_step` 仍 `succeeded` |
| `green-guard.txt` | 35 项 `test_core_work` 通过：连接停用后 `run_step` 被拒、`steps`/`results` 均为空 |
| `regression.txt` | 相关回归（work×2 / adapter×2 / models / console / governance / creation） |
| `management-check.txt` | `npm run check:management` |

过程中一次 409：守卫在计划阶段被抛成 HTTP 409，而本卡语义要求"拒绝也要留回执"，已改为经 `reject_step` 记录（回执可重放，不落事实）。

## 边界

- 只改 `domain/work.py` 与 `application/work.py`；未改模型连接命令、未改章程/资源、未动他人文件。
- 真实模型调用 **0**；本轮全部为本机受控测试。

## 下一步

真实有界验收仍阻塞在宿主 modeld（产物 + 私有配置 + 上游凭据），见 [093](../093-modeld-local-prereq/README.md)；看板同步待网络，见 [094](../094-board-sync-pending/README.md)。
