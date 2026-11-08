# 101：验收脚本不能假通过（#22 评审项 7 的修正）

2026-11-08 16:44–17:15。看板 #22 升到 v11 后新增一项明确评审要求：

> 验收脚本不能假通过：拒绝零调用/零读取/零成果，原请求查询失败不得当作取消成功（PR #22 修正）

本轮据此把"验收证据必须真的证明交换过"变成**离线可测的守卫**，并加固中断脚本。

## 1. 新增 `acceptance_problems(work, receipt, max_output)`

`tests/test_core_work_real.py` 现在把判定抽成函数，返回问题列表；有界验收测试要求为空。规则：

| 规则 | 拒绝的情形 |
| --- | --- |
| 回执成功 | 非 `succeeded` |
| 至少一个回合 | `turns < 1` |
| **至少一次调用** | `budget.used < 1`（零调用不得通过） |
| 用量非零 | `input_tokens`/`output_tokens` 任一为 0 |
| 输出不超授权 | `output_tokens > max_output × 实际调用数` |
| 费用诚实 | `cost_status != "unknown"` |
| **至少读到资料** | 既无 `read_document`，也无 `list_documents` 且 `count > 0` |
| 读取须有摘要 | `read_document` 缺 `sha256`/`bytes` |
| **至少一份成果** | `results` 为空 |

## 2. 守卫本身的测试（`tests/test_core_work_acceptance_guard.py`）

离线、不花额度，6 项覆盖：真实形态数据无问题；**零调用**被拒；**零资料读取**被拒；**零成果**被拒；用量为 0 被拒；`cost_status` 非 unknown 被拒；`read_document` 缺摘要被拒。

| 日志 | 内容 |
| --- | --- |
| `red-guard.txt` | 真实 RED：函数尚不存在（导入失败） |
| `green-guard.txt` | 6 项通过 |

## 3. 中断脚本加固（评审要求"查询失败不得当作取消成功"）

- 取消前必须先用 `GET /v1/requests/<id>` **确认原请求真实存在**，再 `POST …/cancel`；
- 记录 `observed`/`cancelled` 两个事实，测试断言二者都为真——若 20 秒内没观察到请求，测试**失败**（以前会静默通过）；
- 该测试需要真实调用（1 次），**本轮未执行**：用户授权的真实调用额度（2 次）已在 099/100 用完，不能为验证脚本再花第三次。

## 4. 诚实边界

- 本轮改动**只涉及测试与证据**，不改产品；
- 099 那次真实运行的 `list_documents` 在投影里带 `count`（未打印到日志）；新守卫要求 `count > 0` 或存在 `read_document`，PR 复核时若重跑真实验收会自动被这条规则约束；
- 全量 Python 见 `python-full.txt`（含 2 个 expectedFailure：派发前持久化预约的并发/持久断言，等协调者裁定）。
