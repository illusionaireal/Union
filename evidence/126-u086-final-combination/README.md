# evidence/126 — U-086 组合最终自查（合并值守修正后的三路径与双浏览器模式）

## 基线

`dsh/u086-page-cancel` = **f5f6c7d**：合并值守全部复核分支（98dd2e8、e083a24、51b5ca1、5bec20f、915cc15、19afff3）与作者实现链（310c7e1→abfa9ee→22649f4→813b3b5→aa82962→53ed829）。governance.py/governance_store.py 采用值守快照级投影（19afff3），work.py 保留作者修复。

## 最终自查（全部在本机独立复跑）

1. **值守新单测模块** `tests.test_cancel_delivery_observation`：8 tests OK（快照级投影、并发写者读取、观察不可覆盖、损坏不冒充 200、schema 兼容）。
2. **作者持久性测试** `test_a_cancel_intent_receipt_survives_a_console_restart`：OK（取消受理送达后重启，receipts 合并视图与首次 POST 恒等）。
3. **五套值守探针**：delivery **6/6**、observation **2/2**、cancel-route **PASS**、cancel-boundary **4/4**、candidate-boundary **3/3**——全部 PASS。
4. **实际浏览器双模式**（值守驱动 `u086-cancel-recovery-browser.cjs`，每模式 1 次有界回环替身请求）：
   - 正常模式：**15 checks passed**，command POST=2（run+cancel），fake=1，real=0（browser-normal.txt）。
   - 丢取消响应模式（`UNION_U086_LOSE_CANCEL=1`）：**16 checks passed**，POST=2，fake=1，real=0（browser-lose.txt）——丢失响应经原 GET 恢复同一取消命令，无重发。
5. **Python 全量**：792 tests OK（11 skipped）——f5f6c7d 合并后复验。
6. **npm**：check:console（335 前端）+ check:management（37 管理）全绿。

## 结论

服务端（作者）与页面（值守）双方内容齐备且全部合同探针通过；PR43 草稿指向本分支。按 page-combination-contract，页面侧采用仍需另一工程角色独立复核 + head CI 通过——本轮不自行采用、不关闭 #40/父 #22，零真实推理。
