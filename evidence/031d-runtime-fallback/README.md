# 运行期失败切换（M2b / U-051）

2026-11-01。范围：请求在**明确失败**后沿回退链切换连接；结果未知时绝不切换。

## 实际改动

| 文件 | 改动 |
| --- | --- |
| `ai_union/model_api.py` | `APIExecutor(..., fallbacks=())`；`_request` 改为重试循环，新增 `_attempt` 与 `_body_for`；`resolve_chain()`；`result()` 的 usage 记录 `fallback_from`/`connection_used`/`attempts` |
| `ai_union/console.py` | API 连接测试与 `start` 传入回退链 |
| `ai_union/harness.py` | Harness 传输层接收回退链 |
| `ai_union/cli.py` | CLI 执行入口传入回退链 |
| `tests/test_runtime_fallback.py` | 新增 6 项机制测试 |

## 切换规则

| 上游结果 | 是否切换 | 依据 |
| --- | --- | --- |
| 401 / 403 / 429 / 其它明确 4xx / 重定向 | 切换 | 请求被明确拒绝，未产生执行 |
| 5xx / 发送后断开 / 超时 | **不切换** | 结果未知，须核对原执行，避免二次计费与重复副作用 |
| 连接被拒（未发出） | 切换 | 明确未到达供应商 |
| 截止时间已到 | 不切换 | 时间预算已耗尽，切换只会延长不确定性 |

- 回退时**重建请求体**：仅替换 `model` 与输出上限字段，消息与工具定义不变，避免把主连接的工作包语义带错。
- 每次尝试记录 `connection_id`、`revision`、`unknown`、`code` 到 `attempts`，最终连接记 `connection_used`，起点记 `fallback_from`。
- 回退链来自 `execution_config.fallbacks`，不可用的条目在 `resolve_chain()` 中被跳过，不会因为一条陈旧配置使整链失效。

## 验证

- 6 项运行期回退测试全部通过（`fallback-tests.log`）。
- 全量 354 项，1 failure / 1 error，与 HEAD 基线一致，无新增失败（`full-suite.log`）。

## 未覆盖

- 每个角色各自的回退链未接入（当前链属于默认连接）；Harness 按工单切换连接时沿用默认链。
- 前端没有回退链入口。
- 未做独立权限复核；未做真实供应商的失败切换验收。
