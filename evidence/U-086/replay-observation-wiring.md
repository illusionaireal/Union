# U-086：把「重启后无新增派发」接进中断驱动（严格 TDD，2026-11-10）

上一刀只做了可测的观测函数（`evidence/U-086/replay-no-dispatch-observation.md`）。
本刀把它接进中断驱动，使每次真实运行都会落盘 `replay-observation.json`，
并只在两侧可用时才断言「零新增派发」。执行者 DSH 会话
`dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 契约（先冻结）

- 新增 `scripts/exit22-replay-observation.cjs` 的 `recordReplayObservation({fs, path, output, before, after, workId, check})`：
  - 始终写 `replay-observation.json`；
  - `observed` 且 `new_dispatches === 0` → 追加一条**通过**的 check；
  - 前侧不可用 → 记录 `status:'unavailable'` 与其原因，**不追加 check、不宣称 0**；
  - 检测到新派发（观测函数抛错）→ 记录 `status:'failed'` 与原因，并追加一条**失败**的 check。
- 依赖以参数注入（`fs`/`path`/`output`），便于在既有 vm 切片测试中运行。
- 接线位置：`exit22b_page.cjs` 中 `restartComparison` 之后、取消证据之后之前。

## RED（在 commit `7680721` 上观察，命令 `node --test tests/exit22-replay-observation.test.ts`）

```text
Error: Cannot find module '../scripts/exit22-replay-observation.cjs'
✖ tests/exit22-replay-observation.test.ts
ℹ tests 1 / pass 0 / fail 1
```

## GREEN（最小实现）

- 实现上述记录器（三态：observed / unavailable / failed），写文件与 check 语义分开。
- 驱动加三行调用，传入既有 `fs`/`path`/`output`/`before`/`after`/`workId`/`check`。

## 验证

- `node --test tests/exit22-replay-observation.test.ts` → **3/3 通过**。
- `npm test -- exit22` → **320/320 通过**（317 + 新增 3）；既有以源码切片为上下文的用例
  （`exit22-cancel-receipt` / `exit22-final-read` 等）未受影响，说明接线位置安全。
- 无真实模型调用、无产品行为改动、无部署或迁移。

## 边界与后续

- 现状下 `before` 侧多为 117 B 的 `unsupported_capability`，因此真实运行会写出
  `status:'unavailable'` 且**不加 check**——这是刻意的「不声称零派发」。
- 要得到 `observed` 记录，仍需一次有界真实运行（且前快照可用），或原 owner 交出历史记录；
  本刀不替代真实验收。
