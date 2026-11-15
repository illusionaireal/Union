# U-086：区分「目录解析失败」与「创建审计不一致」（真实 catalog/HTTP 回归）

2026-11-10 三轮。值守要求「真实 catalog/HTTP 回归 + 准确修复 head」，并指出两条真实错配仍 409。
本轮给出**真实 HTTP 回归测试**（不是桩）并完成产品级区分。执行者 DSH 会话
`dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 问题

`session_info` 的 creator 分支调用 `creation.read`，而 `application/creation.py` 把
**目录解析失败**与**创建审计不一致**都包成同一条 `incompatible_state`
（「AU 目录或治理记录不完整或不兼容…」）。因此：想跳过「目录/目录档不一致」的行，
就会连带吞掉「创建审计被篡改」这一必须 409 的不变量
（`tests/test_core_creation_failures.py::test_creation_audit_must_still_match_its_original_request`）。

## 契约（先冻结）

- `creation.read` 区分两类失败：
  - 目录解析失败（`au_catalog` 的 `INCOMPATIBLE`，含 profile 与目录不一致、state 读不出）
    → `CoreError('incompatible_state', RESOLUTION_INCOMPATIBLE)`；
  - 创建审计/存储记录不一致（`core_au_store` 的 `INCOMPATIBLE`）
    → 仍为原审计文案。
- `session_info` 的 creator 分支仅跳过：`not_authorized`、`unsupported_capability`、
  以及 **`RESOLUTION_INCOMPATIBLE`**；审计文案照旧上抛（保持 409 不变量）。
- `_legacy_engines()`（含 `close()` 路径）**不跳过任何行**，保持既有「记录损坏必须在关闭时暴露」不变量。

## RED → GREEN

- RED：真实 HTTP 探针（`evidence/U-086/session-real-catalog-probe.py` 的同一写法）
  在篡改 catalog profile 后 `/api/session` 返回 **409**（`incompatible_state`）。
- GREEN：区分两类失败后，同一真实场景 `/api/session` 返回 **200** 且不列出该行；
  同时 `/api/v1/aus/<id>` 仍返回 409 `incompatible_state`（错误没有被隐藏）。
- 过程中两次踩到既有不变量并回退：①把 `incompatible_state` 一律豁免 →
  创建审计测试由 409 变 200；②让 `_legacy_engines` 跳过 → `test_catalog_integrity`
  9 项失败（关闭时必须暴露损坏记录）。两次都收窄后通过。

## 验证

- 新增真实回归 `tests/test_core_session_real_catalog.py`：**2 例**（会话 200 + AU 端 409），
  通过真实 Console 服务器、真实登录与真实创建命令，测试内 `finally` 复原 catalog 行以便正常关闭。
- 相关模块：`test_core_session_inconsistent_catalog` 9 项、`test_core_creation_failures` 7 项、
  `test_catalog_integrity` 11 项全绿。
- **全量 Python**：`Ran 827 tests / OK (skipped=11) / exit 0`。
- Node：`npm test -- exit22` **320/320**；`check:management` **37/37**。

## 仍待值守复验

值守的 4 探针覆盖「真实临时 catalog/HTTP 错配」两种；本轮以真实回归覆盖其中
「profile 不一致」与「AU 端仍 409」两点。若其探针仍失败，请指出剩余路径
（例如损坏 legacy state 库时的关闭路径），并推送 `evidence/U-086/session-catalog-review-20261110/`。
