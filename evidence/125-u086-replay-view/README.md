# evidence/125 — U-086 重建子步 6：重放送达视图与观察完整性（值守增量合同 2 项）

## 值守增量合同（915cc15）两处边界

1. **重放同视图**：`WorkService.command` 的 `existing` 提前返回必须返回与首次 POST 相同的持久送达视图（重放=GET 恒等），且不重发取消。
2. **观察完整性**：读取 `delivery_observations` 时必须验证已存 hash（覆盖 id/principal/observed），被篡改的观察不得作为可信事实返回。

## RED（值守探针本机复跑）

`delivery-observation-probes.py` 2 FAIL：重放返回 `cancel_accepted=null` 且缺 delivery；篡改观察 GET 仍 200 接纳。`evidence/125-u086-replay-view/red.txt`

## GREEN

- **重放视图**：`WorkService.command`/`run_step`/`run_loop`/reconcile/`reserve`/`store_receipt` 等全部 9 处 `store.existing` 提前返回，经 `_existing_view(cx, …)` 在**调用方同一连接**上读观察（避免二次写锁死锁——首次实现曾因独立事务 `database is locked` 退化），合并出与首次 POST/GET 恒等的 `cancel_accepted/message/delivery`；existing 命中即返回，不重发取消。
- **观察完整性**：`GovernanceStore.delivery_observation` 重算 `hash({id, principal_id, observed})` 与存储 hash 比对，篡改 → None；receipts GET 对 `cancel_step`（受理为待送达）在观察不可信时 **fail-closed 503**（不把篡改事实当可信返回）。
- 测试断言三路径一致：POST = 重放（existing 视图）= 重启后 GET（合并视图）。

## 回归

值守四套探针 + 新 2 探针、Python 全量、check:console、check:management。
