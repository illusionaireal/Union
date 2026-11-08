# evidence/120 — U-086 重建子步 1：cancel_step 命令面（实时集成合同之上）

## 契约冻结（遵守 reviewer 接续范围，evidence/119）

- 新 work 命令 `cancel_step`：`{"work_id", "step_id", "reason"}`。
- **只结算 `reserved` 步进**（本命令面不触碰 `unknown`——unknown 只能经 `reconcile_automatic` 按线端原请求核对，或确认无法证明执行后由值守按现有合同处理；这是 #81/#83 复核的硬边界）。
- 语义：本地取消 = 释放预约（released），`cost_status` 保持 `unknown`，理由必须记录「本地取消；远端结果未知，不证明远端取消」。
- 复用现有合同：`dispatch.find` 定位步进（校验 `command_id`/`command_sha256`/`principal_id` 归属）、`dispatch.settle` 结算、`dispatch.event` 记事件、`GovernanceStore` 单一写入者不变；不把预约移到派发之后；不改 `reconcile_automatic`/`record_channel_outcome`/`work_model_turns`。

## RED

`tests/test_core_work.py::test_cancel_step_releases_a_reserved_step_before_dispatch`

观察失败：400 `不支持的核心工作命令`（`cancel_step` 不在集成版 FIELDS）。
`evidence/120-u086-cancel-step/red.txt`

## GREEN（最小）

- `ai_union/domain/work.py`：FIELDS + `cancel_step`；`validate_input` 分支（bounded 引用 + reason）；`cancel_step()` 规则（status 必须 reserved；settle 为 released；`cost_status=unknown`）。
- `ai_union/application/work.py`：通用命令分支接 `cancel_step`（与 settle_step 同路径，走 SAVEPOINT work_command 事务）。

## 回归

- `tests.test_core_work` 39 OK（含新测试）。
- Python 全量 660 tests OK（10 skipped）。
- reviewer 探针 `candidate-boundary-probes.py` 3/3 PASS（本分支不受影响）。
- `check:management` PASS。
