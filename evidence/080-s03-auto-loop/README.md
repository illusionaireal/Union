# 080：S03.2e 自动循环驱动 `run_loop`（U-067 / 在线 #22）

2026-11-08 06:39–07:05。在 `run_step`（079）之上补上**循环驱动与终止语义**：自动连续调用模型，直到模型给出成果、或达到轮次上限、或某一步被拒绝。**仍未进行真实模型调用**（网络中断，transport 为测试替身）。

## 本轮用户可验证结果

`POST /api/v1/work/commands` 新增 `kind: run_loop`（`data: {work_id}`）：

- 循环最多 **3 个回合**，每回合调用一次 `run_step`（各自独立请求 id `…-t1/-t2/-t3`、各自独立回执、各自预约/结算一次调用）。
- 模型给出正文的那一回合结束循环，成果作为**候选成果**入账（来源=该回合工具回执）。
- 达到轮次上限仍未给出正文 → 循环结束，`result=false`，已产生的步进/工具回执全部保留（不伪造成果）。
- 某回合被拒绝（无通道、通道失败、不支持工具、参数非法、未绑定目录）→ 立即停止，聚合回执带该步的 `status`/`message`。
- 聚合回执字段：`turns`、`tool_calls`、`result`、`version`；**同一请求体重放返回原聚合回执**，不会重复调用模型。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-run-loop.txt` | 真实 RED：`run_loop` 不被支持（3 项失败） |
| `green-run-loop.txt` | 24 项 `test_core_work` 通过：① 工具回合→正文回合，`turns=2`、1 条工具回执、1 份候选成果、两步都 `used`；② 模型持续只调工具 → `turns=3`、`result=false`、3 步、0 成果；③ 无 transport → `rejected` 且含"通道"；④ 原请求体重放返回原回执 |
| `regression-loop.txt` | 相关回归（work/governance×2/models/console/workspace/documents/creation/isolation/entrypoints） |
| `management-check.txt` | `npm run check:management` |

过程中修掉自己一处测试错误：把"重放"写成了**重新生成带新 base_version 的请求**，于是自然是新请求而非重放；改为原样重发原请求体后通过（产品语义未变）。

## 所有权与边界

- `ai_union/domain/work.py`：新增 `run_loop` 输入形状；循环本身不新增领域规则，仍复用 `step_plan/apply_step/reserve_step/settle_step/submit_result`。
- `ai_union/application/work.py`：`run_loop` 只负责驱动与聚合；每回合仍走 `run_step` 的两阶段纪律（读阶段无锁、模型调用在事务外、写阶段单事务）；新增通用 `store_receipt()` 只落回执、不动 AU 事实（`changed=False`），`reject_step` 复用它。
- 轮次上限 3 是**实现边界**，不是宪章要求；后续按真实调用额度（2 次）会下调或由宿主配置。

## 未完成 / 下一步

1. **真实通道接线 + 有界真实验收**（唯一阻塞）：把宿主已授权的 OpenCode Go 订阅接成 `WorkService.transport`（授权：**≤2 次调用、每次 ≤1024 输出 tokens、仅合成公开资料**），运行一次 `run_loop`，记录用量/费用未知项与恢复结果。需要网络恢复。
2. **中断 unknown**：模型通道超时/中断时的核对语义（当前超时=拒绝且不落步进）。
3. 循环的观察与成本披露（每次调用的用途/用量入账）可随真实通道一并落地。

因此本卡仍 `doing`；本轮真实模型调用 **0**。
