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
