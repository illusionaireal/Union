# evidence/123 — U-086 重建子步 4：取消命令回执持久性（重启后同 ID 可查）

## 范围（等值守复核 22649f4 期间的准备子步，遵守已冻结合同）

页面协议把 `cancel_step` 并入原请求协议后，丢失响应恢复依赖「重启/刷新后按同一命令 ID 查回执」。工作命令回执经 `store_receipt` 持久化；本子步补一个集成级行为测试：**取消命令（自动在途，cancel intent 路径）在 Console 重启后按原 ID 查询必须返回同一回执**——这是页面「查询原请求」按钮的持久化前提（对应 cancel-page-contract 第 2 条的 Core 侧事实）。

## RED

`tests/test_core_work.py::test_a_cancel_intent_receipt_survives_a_console_restart`
（按 cancel-route 合同构造：自动步进在途 reserved 时于 modeld GET 回调内发真实 HTTP cancel_step 命令，随后断言重启重放同回执）

两段真实失败（red.txt 完整保留）：
1. 首个 RED 形态：unknown 步进上取消被拒（`该步已结算`）——按合同修正测试顺序（取消发生在在途 reserved 窗口，与 cancel-route-probe 一致）；
2. 真实产品 RED：**取消受理送达后回执先落库、送达结果后补**——`cancel_accepted` 在 `store.save` 之后才置 True，内存响应与持久化回执分叉；重启重放返回 `cancel_accepted=False` 旧版本（`回执与原请求不匹配` 的重放断言失败，diff 显示 False vs True）。

## GREEN（最小）

`ai_union/application/work.py`：把取消送达移到 `store.save` **之前**——受理结果（送达成功/失败与 message）先定稿，再持久化；重启重放与内存响应恒等。送达失败仍保持 `cancel_accepted=False` 落库（不伪造受理），步进状态/费用不受影响。

## 回归

- 本测试 OK；core work 39 OK。
- Python 全量 **784 tests OK（11 skipped）**。
- 值守探针：cancel-route PASS、cancel-boundary 4/4、candidate-boundary 3/3。

## 回归

Python 全量 + 值守三套探针 + check:management。
