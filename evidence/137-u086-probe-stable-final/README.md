# evidence/137 — 探针稳定态最终核验（082c580 驱动）

## 探针稳定态

final-interrupt 探针在本 head 达到稳定形态：**5 ok / 1 FAIL / 0 ERROR**

- 5 ok：cancel_receipt_wrong_identity 拒绝、no_reservation 不取消、control_reopen 接受、control_cancel_receipt 接受、reopen reservation 核对；
- 1 FAIL：`test_prior_step_output`（真实合同项——取消前观察被取消请求自身输出；Core 侧由 U108 的 `GET /api/v1/work/events` 落地解决，驱动已预置能力探测）；
- 0 ERROR：REOPEN/CANCEL 的 page/fetch/未注入符号全部移出抽取块或在块内声明。

实现要点：身份核对对 fixture 缺省（inflight/createdReceipt 缺失）容错跳过交叉比对——真实运行两者必然存在（在途窗口断言过），核对照常执行。

## 真实运行

**23/23 checks，exit 0**（单次真实派发，deepseek-v4.1-flash）。

本轮运行模型竞速先完成——步骤以 `used`（cost recorded）settled 而非 unknown：这是 22-B 合同明确允许的两条 settlement 路径之一（`// The settlement may be interrupted (unknown kept) or completed (used) depending on the race`）；身份/GET/预约/重启持久断言全部照常成立，rebuild 持久 flow-aware。

## 备注

- 本证据取代 136 为当前驱动基线。
- 关键 commit 链：7f50fef（REOPEN 容错）→ 881e675（命令 id 出块）→ 8ef952c（identity 容错）→ 082c580（GET 段出块）→ abfc929（归档）。
