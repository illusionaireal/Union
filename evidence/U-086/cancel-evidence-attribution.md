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
