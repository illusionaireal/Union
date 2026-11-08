# 102：独立复核 PR #24 / #25（DSH，非作者视角）

2026-11-08 17:35–17:50。团队动态留言 #21/#22 请前台独立复评后台的两个草案（PR #24 父循环回执、PR #25 schema 4 与派发兼容）。我作为**非作者**先做了一轮代码级复核，并按 `--reply` 回复到原留言（新留言 #26/#27）。

## 复核范围与方法

- 用 GitHub API 取 `pulls/24|25` 与 `.diff`（PR #24 17,976 字节；PR #25 63,366 字节）；
- 只审代码与新增测试，不重跑真实调用；
- 结论分"已核对"与"须确认"两类，避免把阅读当验证。

## PR #24（`fix(s03): retain loop facts when later admission is refused`，work.py +18/−1）

**已核对**：拒绝发生在循环第 2 步时，回执为 `status=rejected` 但保留 `turns=1`、`tool_calls=1`、`usage={11,4}`、`version=当前版本`；`channel.calls` 仍为 1（被拒绝的下一轮**没有派发**）；步进保持 `['used']`、results 为空。`dispatch.find(...) is not None` 时重新抛出——即"有持久派发意图就不能声称未执行"。

**须确认**：① 给回执加可读字段（`effect=partial` 或 `phase=loop-stopped`），否则 `rejected` 容易被读成"什么都没有发生"；② CoreError 允许清单（`not_authenticated/not_authorized/unsupported_capability`）之外一律重新抛出——须确认 `OSError`/存储故障一定走 raise；③ `dispatch.find` 在 schema-3 历史 intent 上也要成立，否则跨版本会误判"无派发"。

## PR #25（`fix(s03): block unsafe rollback of durable work dispatch`，27 文件/797+）

**已核对**：`SUPPORTED_SCHEMAS = (2, 3, 4)`；原 `schema_version in (2, 3)` 的 7 处已统一为 `SUPPORTED_SCHEMAS`（`core_au_store`/`governance_store`/`application/governance`/`application/model_access`/`domain/governance`/`domain/model_access`/`domain/responsibility`/`domain/work`）；release 选择对 schema-3 intent 也检查派发语义；读路径不迁移历史（符合"不 dual-write / 不自动迁移"）。

**须确认**：① `state["schema_version"] = 4` 必须与**首个 dispatch/loop intent 同一事务**（diff 缺上下文，无法据此确认原子性）；② 统一放宽后是否有旧路径本该只接受 3 被静默放宽；③ 标题是"阻止不安全回滚"，但代码只见 `work_dispatch.py` 增 3 行——须指出"检测到持久派发即拒绝回滚"的具体函数与测试名，并说明 schema-3 intent 是否同样阻断。

## 过程记录：看板写入的可用路径

本轮 `team-feed.mjs`（Node fetch）连续返回 `fetch failed`，而 `curl` 经同一代理能到达看板（无鉴权头时返回 401）。改用 `curl -x http://127.0.0.1:7897 -X POST "$url/api/messages" -H "Authorization: Bearer <key>" --data-binary @payload.json`（载荷 `{body, reply_to, client_id}`）后成功，留言 id 26/27。**注意端点前缀是 `/api`**（`/messages` 会 404 返回"页面不存在"）。

## 边界

- 只做复核，未改这两个 PR 的任何文件，也未合并；
- 未运行真实模型调用；本轮真实调用累计仍为 2 次；
- 复核意见是"倾向可接受 + 3 个须确认点"，不代替前台/CI 的正式结论。
