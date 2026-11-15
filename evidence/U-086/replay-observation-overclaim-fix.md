# U-086：修正重放观测的两处过度声称（回应值守 #141）

2026-11-10 二轮。值守对 `93dd46b`（重放观测接线）不采用，指出两条：
①`compareSnapshots` 拒绝时不会落盘失败观测；②持久快照无变化却被写成
`new_dispatches: 0`，而并未提供原命令重放/实际派发计数。本轮按此修正。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 契约定稿（修正后）

- `observeNoNewDispatch(before, after, workId)`：
  - 两侧可用且持久事实**未变** → `status:'unchanged'`、`persistent_differences:0`、
    `dispatch_count:null`、附注「仅为持久状态未变，未观察重放或派发计数」；
    **不再出现 `new_dispatches` 字段**。
  - attempts / model_request 去重数 / `budget.used` 任一增长 → 仍抛具名错误（真实的差异）。
  - 任一侧不是 `core.work.v1` 正文 → `status:'unavailable'` + 原因。
- `recordReplayObservation(...)`：
  - 任何情况下都写 `replay-observation.json`；
  - **仅当**存在显式派发计数且为 0 时才追加通过 check（当前观测器不产出计数，故通常不加）；
  - 观测抛错（检测到新派发）→ 记 `status:'failed'` + 原因并追加失败 check；
  - 前侧不可用 → 记 `unavailable`，不加 check。
- 驱动顺序：**先**调用记录器、**再**调用 `compareSnapshots`，因此比较被拒绝时观测文件已落盘。

## RED → GREEN

- RED：改语义后先跑，`exit22-replay-no-dispatch` 的「unchanged」用例与
  `exit22-replay-observation` 的「unchanged 写通过 check」用例共 **2 项失败**
  （旧断言期待 `observed`/`new_dispatches: 0`/1 条通过 check）。
- GREEN：更新两处断言语义后 **8/8 通过**；`npm test -- exit22` → **320/320**。

## 验证与边界

- 全量 Node（exit22）320/320；Python 未受影响（本轮不含 Python 代码改动）。
- 仍未提供「原命令重放的实际派发计数」：该计数需要产品侧派发计数源，当前证据链没有；
  本轮的做法是**如实标记 unknown**，而不是把「状态未变」当作 0。
- 第 5 项因此仍不成立；要成立需要一次有界真实运行并提供派发计数（或在产品侧提供计数源）。

## 第二轮（回应值守留言 #142/#143 的新反例）

值守新发现：请求 ID / 成果内容变化但**数量不变**时，strict 比较正确拒绝，但落盘仍是
`unchanged`／差异 0。本轮修正：

- 新增 `recordReplayComparisonFailure({fs,path,output,workId,error})`：写入
  `status:'failed'`、`persistent_differences:null`、`dispatch_count:null` 与比较错误原因。
- 驱动在 strict 比较**之前**先用纯函数探针比较一次（不重复副作用）：失败则落盘失败记录并
  继续抛出；成功则照常执行原有 `const restartComparison = ...`（保留既有切片标记）。
- 新测试 1 项；`exit22` **321/321**。