# evidence/135 — 被取消请求自身事件观察的预置准备（U108 能力探测）

## 背景

work-events 合同二选一的选项①由 U108（#62/PR50，`GET /api/v1/work/events`）实现。为使 #40 驱动在 PR50 合入后**无需再改**即可获得完整合同语义，在 22b 中断驱动的在途窗口加入能力探测。

## 机制

在途窗口 `waitFor` 内探测 `GET /api/v1/work/events?...&step_ref=…&after=0`：

- **404/501** → Core 面不存在（`workEventsCapable=false`）→ 维持现行在途事实证据（取消 POST 送达在途请求），立即继续；
- **非 ok**（暂时失败）→ 本轮不计，下轮重试；
- **200** → 面存在（`true`）→ 等待**被取消请求自身**至少一个事件（`request_id === inflight.model_request_id`）后才取消——完整合同语义；
- 结果以 check 记录：`cancelled-request own events observed before cancel (Core surface: false|true)`。

## 结果（当前集成，无 U108）

**21/21 checks，exit 0**（单次真实派发，deepseek-v4.1-flash）——`Core surface: false`，走现行在途证据路径；全部既有断言不变。

## 备注

- PR50 合入后重跑本驱动：check 将记录 `Core surface: true` 且取消前已观察自身事件——合同项①完全达成，无需选项②折衷。
- 本证据为预置准备记录；产品字节未动（驱动/证据工具层）。
