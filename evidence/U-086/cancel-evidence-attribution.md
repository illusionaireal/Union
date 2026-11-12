# U-086：原始取消证据读取的归因缺口（严格 TDD，2026-11-10）

针对 B 口径第 2 项「存档可核对层」的第一块离线工作：中断驱动把取消回执写进
`cancel-receipt-before/after-restart.json`，但读取失败时无法归因到具体路由。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 契约（先冻结）

- 读取器 `scripts/exit22-cancel-evidence.cjs` 只读：不发送、不重放任何命令。
- 新增要求 ①：无论成功与否，都要给出四条路由的 HTTP 结果
  （`/api/session`、`/api/v1/work`、`/api/v1/governance/receipts`、再次 `/api/session`）。
- 新增要求 ②：任一路由非 200 时，错误信息必须包含**键名 + 路由 + 状态码 + Core 错误码**。
- 既有要求不变：身份/step/connection/回执逐字段比对与 `canonical(receipt)` 恒等比较。

## RED（先在 commit `96e6b07` 上观察，命令 `node --test tests/exit22-cancel-evidence.test.ts`）

- 用例 1（`cancel evidence records the per-route HTTP outcome for attribution`）失败：
  `actual: undefined` vs 期望的四条 `{route, status}` 映射。
- 用例 2（`a rejected session read names the route, status and Core error code`）失败：

  ```text
  AssertionError: The input did not match the regular expression /\/api\/session/. Input:
  'original cancel evidence HTTP status\n\n409 !== 200\n'
  ```

  即旧实现只抛通用的状态断言，既没有路由也没有 Core 错误码。
- 用例 3（回执事实被改写时仍失败于 `original cancel versions`）为回归保护，RED 阶段即通过。

## GREEN（最小实现）

- 读取后先构造 `http` 映射（键 → `{route, status}`），再逐条检查；失败时抛出
  `original cancel evidence <key> read failed: <route> HTTP <status> <code>`。
- 返回值增加 `http`；其余断言与返回字段不变。

## 验证

- `node --test tests/exit22-cancel-evidence.test.ts` → **3/3 通过**。
- `npm test -- exit22` → **309/309 通过**（原 306 + 新增 3）。
- `npm run check:management` → **37/37**。
- 无真实模型调用、无产品行为改动、无部署或迁移。

## 边界与后续

- 本切片只提升**失败可归因性**与**证据结构**，不产生新的真实运行事实；
  第 2 项要求的「完整回执与配对 POST/GET 正文」仍需一次有界真实运行落盘，
  或由原 owner 交出历史运行里的这些记录。
- 下一步（同清单）：C「重启后按原命令查询并断言新增派发 = 0」；B 前快照端点/时序的代码部分。

## 追加：三项取消事实分列落盘（2026-11-12，head 待定）

卡面要求「分别记录取消受理 / modeld interrupted / 远端事实」。此前这些事实散落在多个断言与检查里，
没有一份**单列三态**的驱动产物。本轮新增只读模块 `scripts/exit22-cancel-facts.cjs`
（`buildCancelFacts({receipt, step, work})`），驱动在结算后写 `cancel-facts.json`：

- `local_acceptance`：`accepted`、`receipt_id`、`status`、`delivery_message`（来自产品受理回执）；
- `modeld_settlement`：`observed`、`step_status`、`interrupted`（仅 `status==='unknown'`）、`reason`、`usage`、`cost_status`；
- `remote_fact`：**恒为 `unknown`**，理由写明「本机取消受理与投递观察不证明远端模型服务已停止」；
- `reservation`：`reserved` / `used` / `max_calls`（未知一律 `null`，不补 0）。

严格 TDD：新测试 `tests/exit22-cancel-facts.test.ts` 先以 `Cannot find module` 失败，实现后 **4/4**；
接线后用 `node --test tests/exit22-observed-settlement.test.ts` 发现切片测试上下文缺少 `cancelReceipt`，
改为守卫写（仅在真实驱动上下文内落盘），随后 `observed-settlement` **8/8**、全量 `exit22` **352/352**、
`check:management` **37/37**。

偏差说明：为保证复审切片测试可运行，落盘语句带 `typeof cancelReceipt !== 'undefined'` 守卫；
真实驱动上下文一定满足，切片上下文跳过（该上下文不需要此产物）。