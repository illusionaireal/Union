# U-086 / #40：一次有界真实运行的计划（供协调者决定是否授权）

状态：**待授权**，未执行。执行者应为 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；
需要协调者/值守明确「有界真实运行」授权后才会进行**任何**真实模型调用。

## 目的（只解决两件事）

1. **第 4 项「同一次运行的前后快照」**：在同一次驱动运行内取得 before/after 两侧可核对快照，
   替换历史上只有 117 B `unsupported_capability` 前侧的情形。
2. **第 5 项「重放时真实派发计数」**：在真实中断后按原命令重放，取得**显式**派发计数
   （若端点不提供计数，则如实记录 `dispatch_count_unknown`，不得写 0）。

## 前置条件（缺一即中止，不做降级替代）

- 原 AU、原 Work、原 cancel 命令、原 step/attempt/model_request 身份均可从既有证据取得：
  `evidence/U-086/original-id-supplement-2026-11-10.md` 与存档的
  `cancel-receipt-before-restart.json` / `restart-request-comparison.json`。
- 本机 modeld 与 console host 可正常启动；`/api/session` 对原 AU 返回 200（当前会话修复已合入分支后）。
- 协调者给出明确授权：**允许最多 3 次真实模型调用、总时长 ≤10 分钟**、不新建 AU、不迁移数据、不部署。

## 步骤（一次运行内完成，全部留证）

1. 启动 console host 与页面，读取**前快照**（`/api/snapshot` 与 `/api/v1/work`），落盘 `snapshot-before.json`。
2. 打开原 Work；按原 `step_ref/attempt_id/command_id/model_request_id/connection` **重放原命令**。
3. 记录派发：请求前记录 attempts/model_request 计数与预算 `used/reserved`；请求后再读一次，
   落盘 `replay-dispatch.json`（含 `dispatch_count`，不可得则 `null` + `dispatch_count_unknown:true`）。
4. 取消并读取原请求回执（沿用 `readCancelEvidence`：四路 GET + 严格校验，失败也会落
   `cancel-receipt-*-failure.json` 并保留四路 route/status）。
5. 重启 console（同 root），读取**后快照**，落盘 `snapshot-after.json`。
6. 运行 `compareSnapshots`，落盘 `restart-request-comparison.json`（含
   `identity_equality_only` / `dispatch_count_unknown`）。
7. 生成 `cancel-facts.json`（`local_acceptance` / `modeld_settlement` / `remote_fact: unknown` /
   `reservation`）。

## 边界与禁止

- 不新建 AU、不改治理、不迁移数据、不部署、不动 main/dev。
- 不补造任何缺失快照或回执；缺什么就记 `unknown` 与原因。
- `remote_fact` **恒为 unknown**：本机取消受理与投递观察不证明远端模型服务已停止。
- 超出 3 次模型调用或 10 分钟即停止，保留已有证据并报告中止原因。

## 交付物（本次运行应产出）

`snapshot-before.json`、`replay-dispatch.json`、`cancel-receipt-before-restart.json`（或失败记录）、
`snapshot-after.json`、`restart-request-comparison.json`、`cancel-facts.json`、`checks.json`，
以及一份把上述文件逐项对账的 `evidence/U-086/bounded-real-run-<日期>.md`。

## 成功后仍未闭合

即使本次运行成功，也只能把第 4/5 项从「未取证」推进到「一次有界取证」；#40/#22 的关闭仍需
协调者按验收原文判定，且 CI 需按准确 head 确认。
