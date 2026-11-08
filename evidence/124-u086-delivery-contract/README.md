# evidence/124 — U-086 重建子步 5：取消送达的事务边界与持久观察（按 cancel-delivery-contract）

## 值守合同（51b5ca1）六项故障 + 两项页面，根因

`store.save()` 只写 SQL，事务在 `store.transaction` context 退出时才提交；我的送达在事务/全局锁内、且发送后只改内存回执不回写 → POST 与持久 GET 不一致（False vs True）；错误 id/au 的回包也被记为送达；事务提交失败会先产生取消副作用再丢意图；页面侧 run_loop 未决引用阻塞了取消入口、成功取消的查询入口消失。

## GREEN 设计（按合同 1–4）

1. **意图先提交、锁外送达**：`cancel_step`（自动路径）事务内只写 `cancel_intent`（step 审计字段 + `delivery_observed=None`）并持久化回执（status=succeeded, `cancel_accepted=None`「待送达」）；**离开事务与全局 mutex 后**再向线端发 cancel；送达结果以**持久送达观察**（`store_receipt` 无 AU 状态变更、changed=False）写回同一命令回执——重放可见 `cancel_accepted` 终值。送达失败落 `cancel_accepted=False`（不伪造受理）。
2. **受理/送达分开可查**：同一命令回执演进两次（待送达→已送达/失败），重放总是最新持久事实；原 step 状态/费用不动。
3. **线端响应校验**：cancel POST 的返回体必须 `id == model_request_id` 且 `au_id == organization_id`；不匹配 → `cancel_accepted=False`（错误身份不是受理）。
4. **占用不变**：unknown/reserved 预约不释放、不重派；事务提交失败时（save 抛异常）**取消尚未发生**（送达在 save 成功后）——副作用不先于意图。

页面（两项）：`cancelLocal` 的 `reference` 早退改为「只屏蔽同 kind 重复」——run_loop 未决不阻塞 cancel_step；成功取消（resolved）后仍显示该引用的「查询原请求」入口。

## RED（值守探针本机复跑）

`cancel-delivery-probes.py` 六项在本分支（813b3b5+merge）复跑：5 FAIL（red.txt）：意图不可见/持锁/GET=False/错误id与au仍True/提交失败丢意图；页面扩展 2 FAIL（run_loop 阻塞取消、成功取消无查询入口）。

## GREEN 实现（对应合同 1–4）

- **意图先提交、锁外送达**：事务内只写 `cancel_intent`（审计字段）+ 受理回执（`cancel_accepted=None`「待送达」）并 `store.save`；离开事务与全局 mutex 后才构建通道发 cancel；送达观察经 `GovernanceStore.record_delivery` 写独立 `delivery_observations` 表（带自身 hash，不动被审计的 command/receipt 行）。
- **受理/送达分开且可查**：`GET /api/v1/governance/receipts` 合并视图——受理回执 + `delivery` 观察字段；`cancel_step` 的展示 `cancel_accepted`/`message` 取最新观察；POST 响应带同一 `delivery` 视图（POST 与 GET 恒等）。
- **线端响应校验**：返回体必须 `id == model_request_id` 且 `au_id == organization_id`，否则 `cancel_accepted=False`（错误身份不是受理）。
- **提交失败无副作用**：save 抛异常（探针注入）→ 事务回滚，送达从未发生（`cancel_posts=0`）。
- **页面两项**：`cancelLocal` 不再被 run_loop 未决引用早退阻塞（run 与 cancel 各持原 ID）；成功取消（resolved）后引用仍显示「查询原请求」入口（reference 选择不再按 kind 过滤掉 cancel_step）。

## 回归

- 值守探针：delivery 6/6 PASS（green.txt）、cancel-route PASS、cancel-boundary 4/4、candidate-boundary 3/3、DOM（值守原 5 项 + 本分支 page-execution 20）。
- Python 全量 **784 tests OK（11 skipped）**。
