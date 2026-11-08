# evidence/122 — U-086 重建子步 3：自动调用取消意图（cancel_intent）RED→GREEN

## 合同（遵守 reviewer cancel-boundary-contract + cancel-route-probe）

值守功能探针 `cancel-route-probe.py` 给出确切 RED：自动步进已派发（POST 已发生、原自动预约 reserved）时，有权主体的 `cancel_step` 必须：
1. 把取消意图送到**原线端请求**：向 modeld `POST /v1/requests/<model_request_id>/cancel?au_id=<au_id>`（与 model_checks 面既有协议一致）；
2. **不释放预约**：步进保持 reserved/unknown，`budget.reserved` 不变（cancel_requested/interrupted 不证明未执行）；
3. 回执分开「取消受理」与「执行事实」：受理 recorded（status=succeeded），步进结算仍走原请求核对（`reconcile_automatic`）；
4. 授权：与 work 命令同主体校验（`rules.authorize` + principal 一致）。

现有 `cancel_step`（310c7e1）保留：只处理无 `command_id` 的手工预约（reserved→released）。自动调用（有 `command_id`）改走新分支：记录取消意图 → transport 端 POST cancel → 步进不动。

## RED

`evidence/U-086/cancel-route-probe.py` 在本分支复跑：`FAIL — the actual automatic request never received the requested cancellation`（modeld cancel POST = 0）。`evidence/122-u086-cancel-intent/red.txt`

## GREEN（最小）

- `ai_union/application/work.py`：`cancel_step` 分支前先 `dispatch.find` 定位原步进；若 `command_id` 存在（自动调用）→ 校验 in-flight（`active_steps`）→ 通过 `transport`（`self.transport` 或 factory 构建的同连接通道）向原线端发 `cancel`（复用 `ModelServiceClient` 协议：`POST /v1/requests/<id>/cancel?au_id=`）；受理失败不改变步进（保持 unknown/reserved）；步进**不结算**。回执 message 记录「取消受理已送达原请求；执行事实仍按原请求核对」。
- domain：`validate_input` 不变（同字段）；`cancel_step` 规则拆成两个入口：手工预约释放（原样）+ 自动调用取消意图（新 `cancel_intent()`，只更新 `step["cancel_requested_at"]` 审计字段，不改 status/cost）。

## 回归

- `cancel-route-probe.py` PASS（本分支）。
- `cancel-boundary-probes.py` 4/4 PASS（安全对照不回退）。
- Python 全量 784 tests OK（11 skipped）。
- core work 39 OK。
