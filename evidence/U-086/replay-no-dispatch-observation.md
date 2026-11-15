# U-086：重启后「无新增派发」观测（严格 TDD，2026-11-10）

对应协调者 B 口径第 5 项的行为侧缺口：驱动一直没有显式的
「以原命令重开/重放后新增派发 = 0」断言。本切片先离线补上可测的观测函数，接线另轮。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 契约（先冻结）

`scripts/exit22-restart-evidence.cjs` 新增只读函数 `observeNoNewDispatch(before, after, workId)`：

- 输入是**已读到的 Core work 正文**（`protocol === 'core.work.v1'`），不发起任何请求。
- 任一侧不是 core.work.v1 正文（例如历史 117 B 的 `unsupported_capability`）时，
  返回 `{status:'unavailable', reason}` 并包含该侧的键名与错误码，**不猜测、不报 0**。
- 两侧可用时比较：attempts 数、`model_request_id` 去重数、`budget.used`；
  任一增加即抛 `new dispatch after restart: <指标> <before> -> <after>`。
- 全部不变时返回 `{protocol:'acceptance.replay-observation.v1', status:'observed',
  attempts{...}, model_requests{...}, budget{...}, new_dispatches:0}`。

## RED（先在 commit `26cb0b6` 上观察，命令 `node --test tests/exit22-replay-no-dispatch.test.ts`）

```text
✖ an unchanged restart observes zero new dispatches
✖ a new attempt after restart is rejected as a new dispatch
✖ a new model request after restart is rejected as a new dispatch
✖ an increased used counter is rejected as a new dispatch
✖ a missing before side is reported unavailable instead of guessed
ℹ tests 5 / pass 0 / fail 5
```

根因：`observeNoNewDispatch` 尚不存在（`TypeError: ... is not a function`）。

## GREEN（最小实现）

- 增加 `side()`：校验 `core.work.v1`、取该 work 的 attempts/model_request/预算；
  非正文时返回 `unavailable` 原因串。
- 依序比较 attempts → model requests → budget.used，任一增长即抛具名错误；否则返回观测对象。
- 导出 `observeNoNewDispatch`（不改动既有 `readSnapshot`/`compareSnapshots`）。

## 验证

- `node --test tests/exit22-replay-no-dispatch.test.ts` → **5/5 通过**。
- `npm test -- exit22` → **314/314 通过**（原 309 + 新增 5）。
- `npm run check:management` → **37/37**。
- 无真实模型调用、无产品行为改动、无部署或迁移。

## 边界与后续

- 本函数尚未接入驱动主流程；接线时要避免破坏现有以源码切片为上下文的测试，
  计划在 `restartComparison` 之后单独落盘 `replay-observation.json` 并只在
  `status === 'observed'` 时增加一条 check。
- 即便接线完成，真正的「真实运行证据」仍需一次有界真实运行（含可用的前快照），
  或原 owner 交出历史记录；不得用本函数的存在替代真实验收。

## 追加：比较摘要显式标注「派发计数未知」（2026-11-11 07:4x）

重启比较此前只给 `transport_dispatch_count: null` 与 `no_new_request_identity: true`，
读者容易把「身份集合相同」误读成「没有派发」。本轮在同一摘要里显式加两个字段：

- `dispatch_count_unknown: true` —— 计数来源不可用；
- `identity_equality_only: true` —— 本次比较只证明请求身份相同，不证明传输层派发次数。

RED→GREEN：新增测试 `the comparison summary states that dispatch counting is unknown`
先失败（两字段缺失），实现后 `exit22-restart-snapshot` **106/106**；
全量 `npm test -- exit22` **341/341**；`check:management` 37/37。无 Python 改动。
## 追加：`replay-observation.json` 每条记录显式标注计数未知（2026-11-11 07:5x）

与比较摘要一致，记录器统一在写入前计算 `dispatch_count_unknown`：

- `dispatch_count` 是数值（仅 `observed` 且显式计数）→ `false`；
- `dispatch_count` 为 `null`（unchanged / unavailable / failed / 比较失败）→ `true`。

RED→GREEN：新测试先以「字段缺失」失败；实现后该套件 **5/5**、全量 `npm test -- exit22` **343/343**。
写入器仍不发明计数：`observed` 之外一律 `null` + `unknown:true`。
更正：上面写的「343/343」为笔误，实测 `npm test -- exit22` 为 **342/342**（新增 1 条测试：341→342）。