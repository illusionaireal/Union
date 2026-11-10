# U-086 / #40：按 B 口径对原 ID 记录的逐项补证映射（2026-11-10，经值守记录审计后更正）

本文件把协调者 2026-11-10 在 #22 评论336 / 留言#138 的 B 口径，逐条对照**已入库的原 ID 记录**。
约束：不新增模型请求、不把缺失用量补 0、不发明历史；未记录的一律保留未证。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

**本版已采纳值守 `supplement-record-audit`（609a337）对上一版的五项更正**，见文末「复核后更正」。
凡「驱动报告通过」与「存档可独立重算」两层必须分开陈述。

## 记录来源（本轮实际打开）

- **门控版真实运行**：`evidence/139-u086-original-output-gate-exit/`
  - `checks.json`：**118 项通过、exit 0**、nonce `UNION-EXIT22B-63e8bcc6`
  - 关键 checks：`original request text observed before cancel`、
    `original output events are ordered public text or tool observations`（cursor 分页多次）、
    `in-flight automatic reservation carries the line-end id: work-dfac8f2a…`、
    `cancel receipt identifies the same command/attempt/step/model request`、
    `original GET returns the delivered cancel receipt (identity match)`、
    `step settled as unknown (cost unknown)`、`an unknown settlement keeps the budget reserved`、
    `the settled step survives the rebuild as unknown`、`the settled step keeps its original identity across the rebuild`
  - `snapshot-after-restart.json`：`budget{max_calls 3, used 1, reserved 1}`、`usage{438,46}`、`cost_status unknown`、
    `steps 2`（`work-exit#s1` used / `work-exit#s2` **unknown**，`cancel_requested_at 2026-11-09T06:40:11Z`）、
    **两条不同 model request**（`work-b6dc2493…`、`work-dfac8f2a…`）、`attempts 1`、`tool_calls 1`
  - `snapshot-before-restart.json`：117 B 的 `unsupported_capability`
- 其它真实运行：`evidence/138`（24/24）、`evidence/134`（20/20）、`evidence/127`（13 项）；**三个运行的
  AU/principal/请求 ID/快照 hash 各不相同**，绑定必须逐 run 分开
- 复核侧：`final-interrupt-review.md`、`strict-download-review.md`、`evidence/U-085/2026-11-09-source-review.md`

## 逐项判定（重述为两层：驱动报告 / 存档可核对）

| # | B 口径要求 | 驱动报告层 | 存档可核对层 | 依据与缺口 |
| --- | --- | --- | --- | --- |
| 1 | 被取消原请求**确有输出 events** | 139 的 check 明确写 `original request text observed before cancel` 与有序公开文本/工具观察（cursor 分页） | 事件正文未入库（只留哈希与 UTF-8 字节数），cursor 分页不落盘 | 139 README 与 final-read combination 已登记其评审局限；不得把 check 标签升级为完整页面验收 |
| 2 | cancel command/模型请求/主体/AU 与 GET 回执一致 | 139/134 均有 `cancel receipt identifies the same command/attempt/step/model request`、`cancel receipt id matches the submitted cancel command`、同 run 原 GET 身份匹配 | **不可独立重算**：两份 checks 内嵌的取消回执 JSON 均在 **192 字符处被截断**（`…"grant-45d` / `…"grant-790`），提交命令与配对 POST/GET 正文未入库 | 需原 owner 提供完整回执与配对正文；本文件只能陈述「驱动报告通过」 |
| 3 | 受理 / modeld interrupted / 远端未知 | Core 侧受理与 unknown 事实齐备 | `model_outcome=unknown` + reason 含 `work_step_interrupted`；**无 modeld 实际返回的完整中断回执** | 保留 Core 取消/未知事实；modeld 真实状态仍需其原始回执；远端未知按 unknown 保留、cost 不补 0 |
| 4 | 同一运行前后核对 unknown 预约/已知用量 | 重启后单侧事实完整 | **前侧不存在**：127/128/129/134/136/137/138/139 八个 before 快照全部缺成功的 `core.work.v1` 观察（117 B `unsupported_capability`） | 无前侧即非「同运行前后」，不可事后重建 |
| 5 | 重启后原命令查询/重放新增派发 0 | 重启后 unknown 以原 `step_ref/model_request_id/attempt_id` 存活、`reserved=1` 保持 | 该 run 内可见**两条模型请求记录**（1 used + 1 unknown），**远端调用数未知**；无「以原命令重放新增派发=0」断言 | 不得把「单次真实派发」写成「一次模型调用」，也不得据此推断远端调用 1 次 |
| 6 | 源码/服务/运行身份绑定 | 各 run 的身份字段可读 | 已有 127 复核的驱动/输入 SHA256 与 139/134 的 principal/connection/grant/host_instance/mandate/context_scope | **须逐 run 绑定**：127 的 hash 不认证 134/139 的执行源码（三者 AU/请求 ID 不同） |

## 结论（经更正）

1. **驱动报告层**：第 1、2、3 项在 139/134 的驱动报告里均有对应通过标签；第 6 项的身份字段可读。
2. **存档可核对层**：仅第 6 项部分成立（逐 run 分开）；第 2 项因回执截断无法独立重算；第 1 项事件正文未入库；
   第 3 项缺 modeld 原始中断回执；第 5 项缺重放计数断言；第 4 项前侧缺失。
3. 因此**真实出口仍未完整**、#22 不能据此关闭；已更正上一版「4 项已满足」的表述为「驱动报告通过、存档待补」。
4. 补齐路径：由原 owner 提供（a）完整取消回执与配对 POST/GET 正文、（b）modeld 真实中断回执、
   （c）任一 run 的成功前快照、（d）原命令重放的新增派发计数；或由用户授权的有界真实运行重新捕获。
   以上均不得以 check 标签或推断替代。

## 待诊线索：为什么「前快照」永远只有 117 B（供 owner/值守离线排查）

本轮读驱动与工装时发现一条可离线查的线索，不涉及新调用：

1. 集成里的前快照写法是 `scripts/exit22b_page.cjs:405`（`exit22c_download.cjs:379` 同形）：
   `const before = await snapshot(); fs.writeFileSync('snapshot-before-restart.json', …)`。
2. `snapshot()`（`exit22b_page.cjs:26`）调用 `scripts/exit22-restart-evidence.cjs:4` 的 `readSnapshot`，
   后者读 `/api/session` + `/api/v1/work?organization_id=…`，并返回**复合对象** `{session, work, current}`；
   其中对 `session`/`current` 断言 `core_protocol`、`principal_id`、`service_instance`，
   对 `work` 断言 `core.work.v1`/`organization_id`/`access.principal_id`。
3. 但入库的 8 个 `snapshot-before-restart.json` 都是**单个错误对象**
   `{"code":"unsupported_capability","error":"此 AU 尚在准备态，自主行动与资源操作尚未启用"}`（117 B），
   **不是** `{session, work, current}` 复合结构，也不是断言失败应有的抛错形态。

由此可查的两个方向（都不需新真实调用）：
- (a) 这些 run 用的驱动版本可能与集成内的 `readSnapshot` 不同（或该错误由外层 catch 直接落盘），
  需比对 run 对应的驱动 commit 与集成的差异；
- (b) 若确实是 `/api/session` 或 `/api/v1/work` 返回该错误，则与「同一 AU 已能派发并取消真实请求」
  的事实矛盾（除非快照发生在 AU 启用生效之前），属**就绪门/时序**问题，应离线定位后再谈第 4 项。

### 已定位到代码级归因（本轮继续追查，仍为只读）

- `unsupported_capability` 的默认文案「此 AU 尚在准备态…」在 `ai_union/errors.py:22` 是**通用缺省消息**，
  HTTP 状态 409（`errors.py:15`）；因此**不能**从该文案推断「AU 处于准备态」。
- 该错误在代码里由「**用 legacy 引擎路径访问 core_v1 AU**」触发：
  `ai_union/console.py:119`（`_catalog_engine`：`profile != "legacy_v0"` 即抛）、
  `ai_union/adapters/au_catalog.py:135`（`legacy_directory` 同判）、`au_catalog.py:70`（core_v1 状态读到即抛）；
  另一处是 `application/governance.py:23`（自定义文案「此接口仅支持核心 V1 AU」）。
- 结论方向：前快照的 117 B 409 更可能是**驱动在切换到 Core 会话之前读了 legacy 路由**
  （如 `/api/session` 走 legacy console 引擎），而非 AU 真处于准备态；重启后 Console 以 Core 模式启动，
  同一读取才成功。若成立，第 4 项的「前侧缺失」属**驱动时序/路由选择**问题，
  可由 owner 在不新增真实调用的前提下改驱动（先确认 Core 会话后再拍前快照），
  但**仍需一次有界真实运行**才能产出前后两侧的同一 run 记录。

这两点只影响「前快照为何缺失」的归因，不改变第 4 项仍未证的结论。

## 复核后更正（回应值守 `supplement-record-audit` 609a337）

1. 「134 为单次真实派发」→ 改为：该 run 内有**两条**模型请求记录（1 used、1 unknown），已知用量子集
   438/40（139 为 438/46），**远端调用数未知**，不推断。
2. 「受理/interrupted/远端未知三项均已记录」→ 改为：Core 侧齐备，**modeld 完整中断回执缺失**。
3. 「取消命令/POST/GET 身份完全建立」→ 改为：**驱动报告通过**，存档回执在 192 字符处截断，无法逐字段重算。
4. 「127 的复核绑定 134 的源码/服务」→ 改为：**逐 run 分开**，127 的 hash 不认证 134/139。
5. 「原输出从未捕获」→ 已在上一版（f87ab46）改为「139 有捕获标签」，本版继续保留并注明其评审局限。

## 方法与边界

只读打开上述已入库文件与字段；未运行真实请求、未改动产品/驱动/主机/数据库/他人工作；新真实模型调用 0。
