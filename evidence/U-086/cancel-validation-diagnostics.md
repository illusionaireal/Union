# U-086：取消证据读取的后续校验失败诊断（复审包）

日期 2026-11-12。回应值守评论 **433** / 留言 **#146** 对 `0729da8` 的 P2 裁定。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 合同（冻结）

`readCancelEvidence(page, reference, expectedReceipt)` 在任何失败下都必须留下**已完成安全观测**：

| 阶段 | 已观测内容 | 失败时 error 携带 |
| --- | --- | --- |
| 四路 GET（session/work/receipt/current） | 各路由 status | `http`（键→`{route,status}`）、`route`、`status`、`code` |
| GET 后严格校验（principal、Work/step 身份、receipt 事实、投递一致性） | 四路均 200 | `http`（同四路）、`route:null`、`status:null`、原错误 `code` 保留 |

约束：不吞断言、不序列化响应正文或凭据、不补造 receipt/历史快照、unknown 派发计数保持 `null`。

## 反例与合法控制（严格 TDD）

已在 `tests/exit22-cancel-evidence.test.ts` 固化 12 项，其中本轮新增 6 项：

四反例（修复前全部失败于 `error.http === undefined`，修复后均保留四路 map 并严格拒绝）：

1. `session.body.principal_id` 被改 → `original cancel principal` 断言拒绝；
2. `current.body.principal_id` 被改 → 同上；
3. `receipt.body.receipt.id` 被改 → `original cancel receipt id` 断言拒绝；
4. `receipt.body.receipt.message` 被改 → `original cancel receipt facts changed` 拒绝。

两个合法控制（修复前后都必须通过）：

5. 干净读取 → 返回 `{protocol, reference, service_instance, http, receipt}`，`http` 为四路 200；
6. 干净读取且 `work.version` 更新（12→99）→ 仍通过（版本号不是身份）。

## 复现命令

```text
node --test tests/exit22-cancel-evidence.test.ts        # 12/12
npm test -- exit22                                      # 348/348
npm run check                                           # Node 348 + 管理 37 + 前端 29 文件/363
```

值守探针自检（作者侧，机械重签 21 文件 manifest，非复核签名）：

```text
node --test replay-probes.cjs          # 5/5
node --test cancel-driver-probes.cjs   # 6/6（含此前失败的 4 条完整失败归档断言）
```

## 交付

- 修复：`c4b95b7`（`scripts/exit22-cancel-evidence.cjs` + 6 项测试）
- 自检记录：`c5bdc3b`；完整 check 记录：`a858999`
- 分支：`dsh/u086-page-cancel`（已推送 `gh`，head `a858999`）

## 边界

- 仍属作者自检，**不等于**独立复核；请值守按 `a858999` 复验。
- #40 原 owner/WIP 与 #22 真实出口保留；第 4/5 项（117 B 前快照根因、真实派发计数）**仍不成立**。
