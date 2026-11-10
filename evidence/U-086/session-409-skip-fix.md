# U-086：一个不一致的 catalog 行不再让整个 `/api/session` 失败（严格 TDD）

2026-11-10。修的是**产品代码**（`ai_union/console.py`），因此附完整 RED/GREEN 与全量回归；
本分支仅供协调者评审后采用，不自批。执行者 DSH 会话
`dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 缺陷（先有可执行反例，见 [只读探针](session-409-probe.py) 与 [归因](session-409-during-core-creation.md)）

core_v1 AU 创建/刷新的窗口里，catalog 行可能仍标 `legacy_v0`，而该 AU 的目录已解析为
`core_v1`；此时 `Console._catalog_engine` 抛 `unsupported_capability`，`session_info`
未捕获该错误码，导致**整个** `GET /api/session` 返回 409（文案是 `errors.py:22` 的通用缺省
「此 AU 尚在准备态…」）。8 个入库 `snapshot-before-restart.json` 全是这同一个 117 B 错误体，
正是该窗口所致。

## 契约（先冻结）

- 只跳过**目录/目录档不一致**这一类：`unsupported_capability` 与 `incompatible_state`。
- 其余 `CoreError`（如 `storage_unavailable`、`not_authorized`）**照旧上抛**，不扩大吞错面。
- 可读条目照常列出；`core.au.v1` 协议、`principal_id`、`service_instance` 等字段不变。

## RED（在 commit `e5f1402` 上观察）

```
$ python -m unittest tests.test_core_session_inconsistent_catalog
ERROR ... ai_union.errors.CoreError: 此 AU 尚在准备态，自主行动与资源操作尚未启用
Ran 4 tests ... FAILED (errors=3)
```

（另用 `evidence/U-086/session-409-probe.py` 复现同一缺陷：单行不一致即让整次 session 读取失败。）

## GREEN（最小实现）

`console.py` 的 legacy 分支把 `self.engine(...)` 包在 `try/except CoreError` 中：
仅当 `error.code in ("unsupported_capability", "incompatible_state")` 时 `continue`，
否则重新抛出。

## 验证

- `python -m unittest tests.test_core_session_inconsistent_catalog -v` → **5/5 通过**。
- 全量 Python：`python -m unittest discover` → **Ran 822 / OK (skipped=11) / exit 0**（817 + 5）。
- Node：`npm test -- exit22` → **320/320**；`npm run check:management` → **37/37**。
- 无真实模型调用、无部署、无迁移、未改他人文件。

## 评审要点（请协调者关注）

- 语义变化仅在「单个不一致/不可解析条目」不再中断整次 session 读取；其余错误码不变。
- 该修复只解除**读取期**的 409 窗口；真正的根治（创建流程同步刷新 catalog profile）
  仍未做，建议单独 ADR/合同评估并发与写入顺序。
- 即使修复被采用，U-086 第 4 项仍需**一次有界真实运行**产出同一次运行的前后双侧快照；
  历史的 117 B 前快照不可补造。
