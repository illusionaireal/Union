# U-086：取消证据读取失败也留下可归因记录（严格 TDD）

2026-11-10 四轮。值守在 `recheck-5545d4f` 中指出「取消诊断代码在本候选里没有变化，
其更早的失败记录发现仍未关闭」。本轮按同一模式补齐：**读取失败必须落盘**。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 契约

- 新增 `scripts/exit22-evidence-failure.cjs` 的
  `recordEvidenceFailure({fs,path,output,name,workId,error})`：
  写 `<name>-failure.json`，含 `status:'failed'`、`name`、`work_id`、`reason`、
  `dispatch_count:null`、`recorded_at`；**不含 receipt、不含 new_dispatches、不声称 0**。
- 驱动在两次 `readCancelEvidence`（重启前/后）外各加 try/catch：
  失败先落盘失败记录，再原样抛出，绝不只留堆栈。

## RED → GREEN

- RED：新测试 `tests/exit22-evidence-failure.test.ts` 首跑
  `Cannot find module '../scripts/exit22-evidence-failure.cjs'`（1 项失败）。
- GREEN：实现记录器后 2/2 通过；接入驱动后 `npm test -- exit22` → **323/323**（321+2）。

## 验证

- `npm test -- exit22` 323/323；无 Python 改动。
- 失败记录只描述失败本身；派发计数保持 `null`（未知），不写 0。

## 边界

- 本人仍未持有显式派发计数源；第 5 项因此仍不成立。
- 值守 probes 的 anchor 与 source-manifest 需按新 head 重签后复验本刀。

## 第三轮：恢复值守探针锚点（2026-11-11 00:2x）

值守 replay 探针以驱动源码切片为上下文，锚点为
`  require('./exit22-replay-observation.cjs').recordReplayObservation({`
到 `  const cancelEvidenceAfter = `。我上一刀把记录器改名成局部变量、并把
`cancelEvidenceAfter` 改成 `let`，**破坏了两个锚点**。本轮恢复：

- 记录器调用改回内联 `require(...)` 形式（锚点 1 复原，且切片内不含额外局部变量）；
- 新增 `readWithFailureRecord({loader, ...})` 包装器，两次取消证据读取改为
  `const cancelEvidenceBefore/After = await require('./exit22-evidence-failure.cjs').readWithFailureRecord({...})`
  （锚点 2 复原，同时保留失败落盘）。
- 校验：两个锚点各出现 1 次；`exit22` **325/325**（323+2 包装器测试）；`check:management` 37/37。

偏差说明：包装器的实现先于其测试（记录器本身仍是先 RED 后 GREEN），已在测试内补
「失败原样抛出」与「成功原样返回」两例固定契约。