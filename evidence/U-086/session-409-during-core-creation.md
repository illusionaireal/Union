# U-086：`/api/session` 在 core_v1 AU 创建期间可能 409（前快照缺失的根因假设）

2026-11-10。只读代码核对，不新增模型调用、不改产品代码。执行者 DSH 会话
`dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`。

## 现象（已入库证据）

`evidence/127/128/129/134/136/137/138/139` 的 `snapshot-before-restart.json`
**全部**是 117 B 的：

```json
{"code":"unsupported_capability","error":"此 AU 尚在准备态，自主行动与资源操作尚未启用"}
```

而同一 run 的 `snapshot-after-restart.json` 是 6643–6705 B 的正常 `core.work.v1` 正文。
前侧失败、后侧成功，且失败文案在 `ai_union/errors.py:22` 是**通用缺省消息**（HTTP 409，
`errors.py:15`），不能据文案推断「AU 处于准备态」。

## 代码路径（本轮只读追踪）

1. 驱动前快照：`scripts/exit22b_page.cjs` → `snapshot()` → `scripts/exit22-restart-evidence.cjs` 的
   `readSnapshot`，读取 `/api/session`、`/api/v1/work?organization_id=…`、再次 `/api/session`。
2. 路由：`ai_union/server.py:152-155` —— `/api/session` → `app.session_info(token)`；
   `/api/v1/work` → `app.work.read(...)`。
3. `ai_union/console.py:170` `session_info`：遍历 `_catalog_entries()`；
   对「`creator is None` 且 `item["profile"] == "legacy_v0"`」的条目走
   `self.engine(token, item["id"])` → `_catalog_engine` → `_resolve_entry` →
   `resolve_directory(...)`；一旦**解析出的 profile 不是 `legacy_v0`**，`console.py:119` 直接
   `raise CoreError("unsupported_capability")`。

## 根因假设（**未确认，附反证**）

**catalog 行仍记 `legacy_v0`，而该 AU 的目录/状态已是 `core_v1`（准备态/创建中）** 时，
`session_info` 的 legacy 分支会在 `engine()` 里被 `_catalog_engine` 拒绝，整个
`/api/session` 返回 409 `unsupported_capability`。重启后 Console 重新读取目录与 catalog，
两者一致，同一读取即成功——这正好解释「前侧 117 B、后侧 6643 B」。

**2026-11-10 追加反证（本轮复核，降低确定性）**：

1. `ai_union/adapters/au_catalog.py:114-115` 要求 `profile == entry["profile"]`，否则抛
   `INCOMPATIBLE`（即 `incompatible_state`）。也就是说「catalog=legacy、目录=core_v1」
   的真实不一致会先以 **`incompatible_state`** 结束，而不是 `unsupported_capability`。
2. `session_info` 对 `profile != "legacy_v0"` 的条目直接 `continue`（`console.py:180` 附近），
   因此它根本不会对 core 条目调用 `engine()` → 也就不应产生 `console.py:119` 的
   `unsupported_capability`。
3. 能抛出**默认文案**「此 AU 尚在准备态…」的位置只有三处：`console.py:119`（`_catalog_engine`）、
   `adapters/au_catalog.py:70`（`check_legacy_runtime` 读到 `runtime_profile=core_v1`）、
   `au_catalog.py:135`（`legacy_directory`）；`application/governance.py:23` 用的是另一段自定义文案。

因此**更可能的路径**是：驱动/页面在「准备态 AU」上走了仍按 legacy 打开引擎的某条路径
（`check_legacy_runtime` 或 `legacy_directory`），而不是 `session_info`。要确认究竟是哪条路由，
需要一次带路由级 HTTP 记录的运行；本轮无法只靠静态代码唯一确定。

**结论修订**：本文件原先把该 409 归因于 `session_info` 的说法**不成立或至少未证实**；
它记录的是「一个不一致条目不应拖垮整个 session 读取」这一**稳健性缺口**（该缺口本身真实存在，
且已由 [修复候选 9472a64](session-409-skip-fix.md) 覆盖），但**不能**声称为 117 B 前快照的根因。

这属于**就绪/catalog 一致性问题**，不是权限问题，也不会因为重跑驱动而自动消失。

## 影响

- 任何在「core AU 已建、catalog 未刷新」窗口内读取 `/api/session` 的页面/驱动都会拿到 409；
  U-086 的前快照恰好落在这个窗口（创建 → 派发 → 取消 → 前快照 → 重启）。
- 这不影响 B 口径其它已满足项（回执/身份/unknown 保留），但**第 4 项「同运行前后」因此长期缺失**。

## 建议修法（下一轮或交值守，需产品合同+TDD+复核）

- 方案 A（最小、稳妥）：`session_info` 对单个条目解析失败时按 `unsupported_capability`
  跳过该条目并继续（与现有 `not_authorized` 跳过风格一致），使 `/api/session` 不再因一个
  不一致条目整体 409。
- 方案 B：创建/采用流程在写目录后**同步刷新 catalog profile**，消除不一致窗口（更彻底，
  但涉及写入顺序与并发，需 ADR/合同）。
- 两者都必须先写 RED 测试（构造 catalog=legacy、目录=core_v1 的 fixture，断言
  `/api/session` 仍 200 且列出该 AU 为 `core_v1`），再最小实现，并跑全量 Python+npm。

## 边界

本文件只是**只读归因与建议**，未修改任何产品代码；真实前快照仍不可补造，第 4 项仍未证。
