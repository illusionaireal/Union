# U-086 / #40：按 B 口径对原 ID 记录的逐项补证映射（2026-11-10，含当前基线 evidence/134）

本文件把协调者 2026-11-10 在 #22 评论336 / 留言#138 的 B 口径，逐条对照**已入库的原 ID 记录**。
约束：不新增模型请求、不把缺失用量补 0、不发明历史；未记录的一律保留未证。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 记录来源（本轮实际打开）

- **最强基线（门控版）**：`evidence/139-u086-original-output-gate-exit/`
  - `checks.json`：**118 项通过、exit 0**、**单次真实派发** `deepseek-v4.1-flash`、nonce `UNION-EXIT22B-63e8bcc6`
  - 关键 checks（原文）：`original request text observed before cancel`、
    `original output events are ordered public text or tool observations`（cursor 分页，多次）、
    `original GET returns the delivered cancel receipt (identity match)`、
    `step settled as unknown (cost unknown)`、`an unknown settlement keeps the budget reserved`、
    `the settled step survives the rebuild as unknown`、`the settled step keeps its original identity across the rebuild`
  - `snapshot-after-restart.json`：`budget{max_calls 3, used 1, reserved 1}`、`usage{438,46}`、`cost_status unknown`、
    `steps 2`（`work-exit#s1` used / `work-exit#s2` **unknown**，`cancel_requested_at 2026-11-09T06:40:11Z`）、
    `attempts 1`、`tool_calls 1`、`delivered_result_id null`
  - `snapshot-before-restart.json`：仍为 117 B 的 `unsupported_capability`
- 其它真实运行：`evidence/134`（20/20 项，非门控版）、`evidence/138`（24/24 项）、`evidence/127`（13 项）
- 复核侧：`final-interrupt-review.md`、`strict-download-review.md`、`evidence/U-085/2026-11-09-source-review.md`


## 134 记录中的关键断言（原文摘录）

- `the cancelled request is this run's own in-flight request (distinct id, own attempt): work-2ea7bef8… / work-exit#a1`
- `cancel receipt identifies the same command/attempt/step/model request`
- `cancel receipt id matches the submitted cancel command`
- `original GET returns the delivered cancel receipt (identity match)`
- `step settled as unknown (cost unknown)` / `an unknown settlement keeps the budget reserved`
- `the settled step keeps its original identity across the rebuild`
- `the settle reason persists` / `an unresolved step keeps its original reservation after the rebuild`
- 取消回执身份：`actor_principal_id 0e9b9d18-…`、`base_version 13`、`cancel_accepted=true`、
  `cancel_connection{grant_ref grant-45dca659d88d…}`
- 前快照：`snapshot-before-restart.json` 仍为 117 B 的 `unsupported_capability`（准备态未启用）

## 逐项判定（以 134 为当前基线）

| # | B 口径要求 | 判定 | 依据 |
| --- | --- | --- | --- |
| 1 | 被取消原请求**确有输出 events** | **已满足（门控基线 139）** | 139 checks：`original request text observed before cancel` + `original output events are ordered public text or tool observations`（cursor 分页）；README 记录只保存哈希与 UTF-8 字节数、不存原文。138 之前版本只做到「能力探测 + ownEvents 计数」，139 为门控版完整观察 |
| 2 | cancel command/模型请求/主体/AU 与 GET 回执一致 | **已满足** | 139/134 均有：回执标识同一 command/attempt/step/model request、回执 id == 提交命令 id、同 run 原 GET 身份匹配（`final-interrupt-review.md:38` 的异构身份反例属修复前旧 driver） |
| 3 | 受理 / modeld interrupted / 远端未知 | **已满足** | 受理：`cancel_accepted=true` + 回执；中断：`model_outcome=unknown` + `work_step_interrupted`；远端未知：`cost_status=unknown`、用量未补 0（139 usage 438/46 仅为已知子集） |
| 4 | 同一运行前后核对 unknown 预约/已知用量 | **仍缺前侧** | 127/128/129/134/136/137/138/139 的 `snapshot-before-restart.json` **全部是 117 B 的 `unsupported_capability`**；后侧事实完整（`budget{3,1,1}`、`cost_status unknown`、原身份保持），但无前侧即非「同运行前后」 |
| 5 | 重启后原命令查询/重放新增派发 0 | **状态侧已满足，行为侧未单独断言** | 139：`unknown` 步以原 `step_ref/model_request_id/attempt_id` 存活、`reserved=1` 保持、整轮**单次真实派发**；但没有一条断言显式核对「以原命令重放查询时新增派发 = 0」 |
| 6 | 源码/服务/运行身份绑定 | **已满足** | `final-interrupt-review.md:3-24`（作者 1e490d0、host d3823e8、driver+4 输入 SHA256）；139/134 快照的 principal/connection/grant/host_instance/mandate/context_scope 一致可核对 |

## 结论（可直接用于关闭判定）

1. **已满足 4 项**：第 1（取消前观察到原请求自身公开文本/事件，门控版 139）、第 2（取消回执与提交命令/身份一致）、
   第 3（受理/中断/远端未知三分）、第 6（源码/服务/运行身份绑定）。
2. **部分成立 1 项**：第 5——重启后状态与预约保持、整轮单次派发成立，但缺「原命令重放新增派发 0」的显式断言。
3. **仍缺 1 项**：第 4——**同运行前快照从未存在**（8 个运行的 before 文件都是 117 B 的 `unsupported_capability`），
   且不可事后重建。
4. 因此**第 1/2/3/6 项的真实出口已有页面级真实证据**；#22 的关闭判定只剩两项由协调者裁决：
   （a）第 4 项是否属于**必须**（若必须，需用户授权的有界真实运行补拍前快照，或明确豁免并记录理由）；
   （b）第 5 项行为侧是否可由「单次派发 + 重启后无新增 attempt/预约保持」替代，或需一条重放计数断言。
   **不得**把第 4 项当作已验，也不得把第 5 项行为侧直接写成已验。


## 方法与边界

只读打开上述已入库文件与字段；未运行真实请求、未改动产品/驱动/主机/数据库/他人工作；新真实模型调用 0。
