# 096：用量在工作与 AU 层可见（U-067 / S03，K-04 可见性）

2026-11-08 13:29–14:05。此前 `usage` 只落在**单个步进**上，工作层与 AU 层读取时看不到合计——章程 K-04 / F12 要求"总成本、失败与不确定性可见"。本轮补上只读汇总（不动记账规则、不估算金额）。

## 变更

- `ai_union/domain/work.py`：新增 `usage_total(work)`，把该工作所有步进的 `usage.input_tokens` / `output_tokens` 求和（只接受非负整数，脏值不计）；工作投影新增 `usage` 与 `cost_status: "unknown"`。
- `ai_union/application/work.py`：`read()` 汇总所有工作的用量，返回新增顶层 `usage` 与 `cost_status: "unknown"`。

**不做的事**：不把未知费用写成 0；不引入单价/汇率；不改记账与预算规则（预算仍是调用次数，`budget()` 未变）。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-rollup.txt` | 真实 RED：读取卡片时 `KeyError: 'usage'` |
| `green-rollup.txt` | 36 项 `test_core_work` 通过：`run_loop` 两个回合（6+1、9+4 tokens）后，工作层 `usage={input:15,output:5}`、AU 层同值、两层 `cost_status=unknown` |
| `regression.txt` | 相关回归（work×2 / adapter×2 / console / models / governance） |
| `management-check.txt` | `npm run check:management` |

## 兼容性

纯新增字段（`works[].usage`、`works[].cost_status`、顶层 `usage`、顶层 `cost_status`），既有字段与语义不变；前端未改动（未改 TS 类型也不影响运行）。

## 仍未验证

- 真实模型调用 **0**；真实 usage 仍需宿主 modeld 通道（见 [093](../093-modeld-local-prereq/README.md)）。
- 未把用量并入 AU 资源账（这属于后续 S06/资源切片，需要先冻结契约）。
