# evidence/130 — 真实中断出口（按最终中断复核三项断言修正）

## 背景

值守复核（e91ae4e，`final-interrupt-review-probes.py` 3 FAIL/3 对照）指出 evidence/127 驱动的三项断言缺口。本证据为按该三项修正后的真实中断重跑（真实 modeld，deepseek-v4.1-flash，单次派发）。

## 三项修正对应

1. **被取消请求自身的身份**：断言在途预约携带线端 id（`work-6ae1408d…`）且属于本次运行自己的 attempt（`work-exit#a1`）——`distinct id, own attempt`；取消 POST 送达该 id 即证明其在途（与值守 cancel-route 探针同构）。注：`/api/v1/models/events` 端点为 model_checks 专用（check_id 绑定），work 自动步进无事件端点，故被取消请求的"自身活动"以线端身份+在途事实断言。
2. **取消受理身份全比对**：取消命令 ID 提交前固定（`cancelCommandId`），回执比对 `id/step.step_ref/model_request_id/organization_id`；**同 run 原 GET**（`/api/v1/governance/receipts`）返回同一持久送达事实（`cancel_accepted` 与 `model_request_id` 恒等）。
3. **重开核对预约+身份**：重启后步进保持 `step_ref/model_request_id/attempt_id` 原身份、理由持久、**unresolved 步进 reserved=1**。

## 结果

**18/18 checks，exit 0**（较 127 的 13 项增加 5 项身份/预约断言）。

## 偏差

无页面截图（同 127）；页面渲染事实以 checks 与重启后快照为准。
