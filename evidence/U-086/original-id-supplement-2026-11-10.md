# U-086 / #40：按 B 口径对原 ID 记录的逐项补证映射（2026-11-10，含记录级核对）

本文件把协调者 2026-11-10 在 #22 评论336 / 留言#138 的 B 口径，逐条对照**已入库的原 ID 记录**。
约束：不新增模型请求、不把缺失用量补 0、不发明历史；未记录的一律保留未证。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 记录来源（本轮实际打开的原始文件）

- `evidence/127-u086-real-interrupt-exit/snapshot-after-restart-final-head.json`（6643 B，重启后 Core 快照，
  `protocol core.work.v1`、work `work-exit` v15）
- `evidence/127-u086-real-interrupt-exit/checks-final-head.json`（13 项通过 + 1 条非产品错误文本）
- `evidence/127-u086-real-interrupt-exit/snapshot-before-restart.json`（117 B，只有 `unsupported_capability` 错误）
- 复核侧记录：`final-interrupt-review.md`、`strict-download-review.md`、`evidence/U-085/2026-11-09-source-review.md`

## 记录级事实（本轮读出的关键字段）

- 完成步（`work-exit#s1`，seq=1）：`status=used`、reason「模型步进已完成」、`command_id 83c0dc54-…-t1`、
  `command_sha256 d9d4118a…`、`model_request_id work-3f86df9f…`、usage **438/43**。
- 被取消步（`work-exit#s2`，seq=2）：`status=unknown`、`model_outcome=unknown`、reason 含
  **`work_step_interrupted`**、`cancel_requested_at 2026-11-09T01:50:53Z`、`cancel_requested_by 真实中断验收：等待期请求停止`、
  `command_id …-t2`、`command_sha256 f374444a…`、`model_request_id work-cd9ac3da…`（= 检查项中的 line-end id）。
- 身份/上下文（同一记录内）：`principal_id b92a8d7a-…`、`connection-a`（`grant-388a10f8bca9` rev 1、
  `deepseek-v4.1-flash`、max_output 1024）、`context_scope`={au `org-7f718c…`、binding-page v1、def-page v1、
  ma-page v1}、`host_instance service-c912d6af…`、`policy_version 2`、`charter_version 2`。
- work 级：`budget {max_calls 3, used 1, reserved 1}`、`cost_status unknown`、`usage 438/43`、`steps 2`、
  `tool_calls 1`（`read_document brief.md` 70 B sha `9f95ee6b…`）、`attempts 1`（`work-exit#a1`，`stale=true`、
  outcome null）、`delivered_at null`、`result_ids []`。
- 取消回执（`checks-final-head.json` 检查项内）：`cancel_accepted=true`、`actor_principal_id b92a8d7a-…`、
  `base_version 13`、`cancel_connection{grant_ref grant-388a10f8bca9…}`。
- 前快照：**不存在**——`snapshot-before-restart.json` 仅 117 B 的 `unsupported_capability`（准备态未启用）。

## 逐项判定（在记录级事实之后更新）

| # | B 口径要求 | 更新后判定 | 依据 |
| --- | --- | --- | --- |
| 1 | 被取消原请求**确有输出 events** | **仍未记录**（不可补造） | 该记录无 events 数组、无输出正文，只有 `model_outcome=unknown` 与 reason；`final-interrupt-review.md:37,71-75` 亦指出 driver 只等预约、不保存输出事件 |
| 2 | cancel command/模型请求/主体/AU 与 GET 回执一致 | **记录齐备、断言未绑定** | 身份与 ID 两侧都在（步级 principal/connection/context_scope/command_id+sha/model_request_id；回执 actor_principal_id/base_version/cancel_connection）；但 `final-interrupt-review.md:38` 证明现有断言可被异构 AU/命令/attempt/step/请求通过，缺少「提交的 cancel command ID 与回执逐项相等」的显式核对 |
| 3 | 受理 / modeld interrupted / 远端未知 | **三分均有记录** | 受理：`cancel_requested_at/by` + 回执 `cancel_accepted=true`；中断：`model_outcome=unknown` + reason `work_step_interrupted`；远端未知：`cost_status=unknown`、未推断 0（`:54-62` 口径一致） |
| 4 | 同一运行前后核对 unknown 预约/已知用量 | **前侧缺失，仍不成立** | 前快照仅 117 B 的 `unsupported_capability`；后侧事实完整（reserved=1/used=1/cost unknown/usage 438/43），但无前侧即非「同运行前后」；`final-interrupt-review.md:64-69` 同结论 |
| 5 | 重启后原命令查询/重放新增派发 0 | **状态侧成立、行为侧未证** | 重启后快照：attempts=1、steps=2、budget used=1、`attempt_ids []`、`delivered_at null` → 未见新增派发；但 `final-interrupt-review.md:74-75` 指出重启本身不证明「原命令重放」行为 |
| 6 | 源码/服务/运行身份绑定 | **已记录可核对** | 作者 `1e490d0`、host 修复 `d3823e8`、driver+4 证据输入 SHA256 一致（`final-interrupt-review.md:3-24`）；本轮另确认 work 级 principal/connection/grant/host_instance/mandate 绑定 |

## 结论

1. 本轮把结论从「多数未记录」细化为：**第 3、6 项已有记录支撑**；**第 2 项记录齐备但缺绑定断言**；
   **第 5 项状态侧成立、行为侧未证**；**第 1、4 项确认无法从现有记录补出**（前快照缺失、输出 events 从未捕获）。
2. 因此 #40 真实出口仍不成立，#22 不能据此关闭；可关闭的只是「记录核对」这一层工作。
3. 要补齐第 1、2、4 项：需用户授权的有界真实运行（捕获输出 events、保存完整 cancel/GET 回执并做 ID 逐项相等、
   同运行前后快照），或由作者提供其历史运行中这些记录（若从未捕获则继续标未证）。

## 方法与边界

只读打开上述已入库文件与字段；未运行真实请求、未改动产品/驱动/主机/数据库/他人工作；新真实模型调用 0。
