# 081：自动步进的用量与费用披露（U-067 / 在线 #22）

2026-11-08 06:44–07:10。`run_step`/`run_loop` 已能自动跑模型回合，但 transport 返回的 usage 之前被丢弃——这违反 K-04/F12（用量到资源账、未知费用不得伪造）。本轮补上：**每次自动步进记录模型用量，费用一律标 `unknown`，循环聚合同样披露**。

## 本轮用户可验证结果

- `run_step` 的步进记录新增 `usage`（`input_tokens`/`output_tokens`，来自 transport 的 usage）与 `cost_status: "unknown"`；回执同样带这两个字段，工作投影里可见。
- `run_loop` 的聚合回执新增 `usage`（各回合累加）与 `cost_status: "unknown"`。
- 没有真实计费能力时**绝不写 0 或估算金额**；只有 token 计数是宿主实际拿到的证据。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-usage.txt` | 真实 RED：2 项失败（步进无 `usage`/`cost_status`；循环回执无累加） |
| `green-usage.txt` | 26 项 `test_core_work` 通过：步进 `usage={input:12,output:5}` 且 `cost_status=unknown`；循环两回合累加 `{30,10}` |
| `regression-usage.txt` | 相关回归（work/governance×2/models/console/workspace/documents/creation/isolation） |
| `management-check.txt` | `npm run check:management` |

## 所有权与边界

- `ai_union/domain/work.py`：`apply_step` 把 usage 归一到整数 token 并固定在步进记录上，`cost_status` 恒为 `unknown`；`validate_state` 不额外强制（缺 usage 的历史步进仍可读）。
- `ai_union/application/work.py`：`run_step` 把 transport 的 usage 传入领域规则；`run_loop` 累加各回合用量并写进聚合回执。
- 未新增金额字段、未接入计费；费用未知时保持显式不确定，符合"未知不填 0"。

## 未完成 / 下一步

1. **真实通道接线 + 有界真实验收**（唯一实质阻塞，需网络）：把已授权的 OpenCode Go 订阅接成 `WorkService.transport`（≤2 次调用、每次 ≤1024 输出 tokens、仅合成公开资料），跑一次 `run_loop`，把真实 usage 记到步进上，并核对费用未知项。
2. **中断 unknown**：通道超时/中断的核对语义（当前超时=拒绝且不落步进）。
3. 用量到 AU 资源账的正式入账（当前是本卡步进级记录，尚未并入 `resources` 账）。

因此本卡仍 `doing`；本轮真实模型调用 **0**。
