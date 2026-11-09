# evidence/136 — 探针兼容重构后的真实中断核验（7429d12 驱动）

## 背景

在途窗口的能力探测重构经历三轮修正（6adc54f 标记连续 → 9b85329 观察移出冻结 TRIGGER 抽取 → d48c8bd/69573a8/7429d12 CANCEL 块完全探针可注入），最终在 7429d12 达到：**final-interrupt 探针 CANCEL 两测恢复 ok**（3 ok / 1 FAIL 真实合同项 / 2 ERROR 归因探针 fixture 缺 `inflight`）。

## 驱动结构（最终）

1. `waitFor`：纯在途预约等待（TRIGGER 标记连续：`let inflight = null;\n  await waitFor…`）；
2. waitFor 后：能力探测 `/api/v1/work/events`（404/501→false）→ 面存在时第二个 `waitFor` 等待被取消请求自身 ≥1 事件；
3. 结果 check：`Core surface: false|true` + `own events observed: 0|n`；
4. CANCEL 块（探针抽取范围内）：仅引用 `cancelOutcome/inflight/createdReceipt` 与块内声明的 `cancelReceipt`（首个 check 用纯 `cancelOutcome` 表达式）；
5. 同 run 原 GET + 命令 id 比对在抽取边界后（settlement 注释之后）。

## 结果（当前集成，无 U108 Core 面）

**23/23 checks，exit 0**（单次真实派发，deepseek-v4.1-flash）：
- `Core surface: false`、`own events: 0`（如实记录）；
- 取消受理 + 回执身份（command 存在性/attempt/step/model request/organization）+ 同 run 原 GET 身份匹配；
- unknown 保留（reserved=1）+ 重启持久（原身份/理由/预约，flow-aware 锚定）。

## 备注

- 本证据取代 134/135 为当前驱动真实核验基线。
- U108 合入后重跑：`Core surface: true` + 取消前自身事件观察 → 合同项①完全达成。
