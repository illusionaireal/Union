# evidence/134 — 真实中断出口最终核验（c836a91/d6a9bec 驱动重构后）

## 背景

c836a91 把取消命令的 `page.evaluate` 移出探针抽取块（vm 兼容）后，须复验真实运行语义不变。复验中发现并修复两处驱动完整性问题：

1. **成功路径产物丢失**：130 重构时误删 success 路径的 `checks.json`/`snapshot-after-restart.json` 写入与 `console.log`（127 原版有）——已恢复；
2. **重开断言流程适配**：22b 中断出口不 adopt/deliver（interrupt 出口），`delivered_result_id` 恒为 undefined——从 131 复制的原成果锚定断言改为 flow-aware：仅当 work 带 delivered id 时核对恒等（中断出口如实跳过，偏差已记录）。

## 结果

**20/20 checks，exit 0**（单次真实派发，deepseek-v4.1-flash）：

- 在途预约携带线端 id + 本次运行自身 attempt；
- 取消受理（cancel_accepted=true）+ 回执身份（command/attempt/step/model request）+ 提交命令 id 恒等 + **同 run 原 GET 身份匹配**；
- unknown 保留（cost unknown、budget reserved=1）；
- 重启持久：settled step 以 unknown 存活、原身份（step_ref/model_request_id/attempt_id）保持、理由持久、预约保持。

## 备注

- 本证据取代 130 作为当前驱动的真实核验基线（130 的 checks/snapshot 结构在此修复后才完整）。
- 探针兼容（final-interrupt）的 CANCEL 块已可直接运行；REOPEN 的 2 ERROR 归因探针 fixture 缺 `inflight`（待值守补 fixture 或豁免合同③）。
