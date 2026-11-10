# U-086 / #40：按 B 口径对原 ID 记录的逐项补证映射（2026-11-10，含当前基线 evidence/134）

本文件把协调者 2026-11-10 在 #22 评论336 / 留言#138 的 B 口径，逐条对照**已入库的原 ID 记录**。
约束：不新增模型请求、不把缺失用量补 0、不发明历史；未记录的一律保留未证。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 记录来源（本轮实际打开）

- **当前基线**：`evidence/134-u086-interrupt-final-verification/`（驱动重构 c836a91/d6a9bec 后复验）
  - `checks.json`：**20/20 通过**、`exit 0`、**单次真实派发**（`deepseek-v4.1-flash`）、nonce `UNION-EXIT22B-cb690ad0`
  - `run.txt`、`snapshot-after-restart.json`（6643 B）、`snapshot-before-restart.json`（117 B）
- 早期运行：`evidence/127-u086-real-interrupt-exit/`（13 项通过；同一 work `work-exit`）
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
| 1 | 被取消原请求**确有输出 events** | **仍缺**（不可补造） | 134/127 的 checks 与快照都只有 `model_outcome=unknown`、reason `work_step_interrupted` 与 line-end/queue 标识，**没有输出正文或 events 数组**；两份 README 也未声明已捕获输出 |
| 2 | cancel command/模型请求/主体/AU 与 GET 回执一致 | **已满足（当前基线）** | 134 四项断言：本次运行自身 attempt、回执标识同一 command/attempt/step/model request、回执 id == 提交命令 id、同 run 原 GET 身份匹配。`final-interrupt-review.md:38` 的「异构身份也能通过」针对的是**修复前的旧 driver**；134 是修复后真实运行 |
| 3 | 受理 / modeld interrupted / 远端未知 | **已满足** | 受理：`cancel_accepted=true` + 回执；中断：`model_outcome=unknown` + `work_step_interrupted`；远端未知：`cost_status=unknown`、用量未补 0（127 快照 `usage 438/43` 仅为已知子集） |
| 4 | 同一运行前后核对 unknown 预约/已知用量 | **仍缺前侧** | 134 与 127 的 `snapshot-before-restart.json` 都是 117 B 的 `unsupported_capability`；后侧事实完整（`budget{max_calls 3, used 1, reserved 1}`、`cost_status unknown`、原始身份保持），但无前侧即非「同运行前后」 |
| 5 | 重启后原命令查询/重放新增派发 0 | **状态侧成立，行为侧未单独断言** | 134：重启后 settled step 以 unknown 存活、原 step_ref/model_request_id/attempt_id 保持、预约保持，且整轮为**单次真实派发**；但没有一条断言显式核对「以原命令重放查询时新增派发 = 0」 |
| 6 | 源码/服务/运行身份绑定 | **已满足** | `final-interrupt-review.md:3-24`（作者 1e490d0、host d3823e8、driver+4 输入 SHA256）；134/127 快照的 principal/connection/grant/host_instance/mandate/context_scope 一致可核对 |

## 结论（可直接用于关闭判定）

1. **已满足 3 项**：第 2（取消回执与提交命令/身份一致，当前基线 134 的真实运行）、第 3（三分记录）、第 6（身份/源码绑定）。
2. **部分成立 1 项**：第 5——重启后状态与预约保持、整轮单次派发成立，但缺「原命令重放新增派发 0」的显式断言。
3. **仍缺 2 项**：第 1（原请求输出 events 从未捕获）、第 4（同运行前快照不存在且不可重建）。
4. 因此真实出口**仍不成立、#22 不能据此关闭**；剩余缺口要么由用户授权的有界真实运行补齐（捕获输出 events + 同运行前快照 + 重放新增派发计数），要么由作者提供其历史运行中已存在的这些记录。**不得把第 1/4 项用受控结论或推断补成已验。**

## 方法与边界

只读打开上述已入库文件与字段；未运行真实请求、未改动产品/驱动/主机/数据库/他人工作；新真实模型调用 0。
