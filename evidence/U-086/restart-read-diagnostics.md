# U-086：重启前后读取的归因缺口（严格 TDD，2026-11-10）

对应协调者 B 口径第 4 项的**离线部分**：`readSnapshot` 是驱动写
`snapshot-before-restart.json` / `snapshot-after-restart.json` 的唯一入口，
但它原先在读失败时只抛通用状态断言，无法归因到路由，导致 117 B 的错误体被误读为
「AU 尚在准备态」。执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；
真实推理 0、无部署/迁移。

## 契约（先冻结）

- `readSnapshot(page, auId, workId)` 仍为只读，仍返回 core.work.v1 正文，形状不变。
- 新增要求：任一路由非 200 时，错误须包含**键名 + 路由 + 状态码 + Core 错误码**。
- 保留要求：`core.au.v1`/`core.work.v1` 协议、`principal_id`、`service_instance`、
  `organization_id`、版本与既有 `requests()`/`results()` 校验不变。
- 错误类型仍须是 **AssertionError**（既有下载/最终读取用例依赖该类型区分
  「授权变化」与「工装失败」）。

## RED（在 commit `a7df99c` 上观察，命令 `node --test tests/exit22-restart-read-diagnostics.test.ts`）

- 用例 2（拒绝的 session 读取）失败：实际消息 `Core session HTTP status\n\n409 !== 200\n`
  ——不含路由、不含错误码。
- 用例 3（拒绝的 work 读取）失败：实际消息 `Core Work snapshot HTTP status\n\n503 !== 200\n`。
- 用例 1（成功读取返回原 Work 正文）为回归保护，RED 阶段即通过。

## GREEN（最小实现）

- 先按 `{session:'/api/session', work:'/api/v1/work', current:'/api/session'}` 逐条检查；
  非 200 时 `assert.fail('restart snapshot <key> read failed: <route> HTTP <status> <code>')`
  ——**用 assert.fail 而非 throw Error**，保持 AssertionError 类型。
- 随后照旧断言协议与身份。

## 验证

- `node --test tests/exit22-restart-read-diagnostics.test.ts` → **3/3 通过**。
- `npm test -- exit22` → **317/317 通过**（原 314 + 新增 3）。
- 过程中发现并修正一处真实回归：初版用 `throw new Error` 导致既有
  `final download GET rejects in-flight expired before saving success` 失败
  （该用例要求 AssertionError 类型），改为 `assert.fail` 后 317/317 全绿。

## 边界与后续

- 本切片只提升**失败可归因性**，不改变任何请求顺序或重试行为，也不产生新的真实运行事实。
- 第 4 项要求的「同一次运行的前后两侧快照」仍需一次有界真实运行；此外仍待
  `replay-observation.json` 接线（上一轮的 `observeNoNewDispatch` 尚未接入驱动主流程）。
