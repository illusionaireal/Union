# 091：适配器假设与 modeld 真实源码交叉核对（U-067 / 在线 #22）

2026-11-08 08:29–09:00。真实模型往返仍缺宿主凭据（无 modeld 进程与 `UNION_MODELD_CONFIG`，本机只有 Bun）。但仓库里**有 modeld 的源码**，因此把 `ModeldWorkTransport` 的每项协议假设逐条对照真实实现，替代"只对照旧 transport 用法"的弱证据。

## 逐项核对结果（全部一致）

| 我的适配器假设 | modeld 真实实现 | 位置 |
| --- | --- | --- |
| `POST /v1/requests`，202 返回请求对象 | `if (method === 'POST' && path === '/v1/requests') … journal.submit(...); return json(publicRequest(...), 202)` | `services/modeld/src/server.ts` |
| 请求对象含 `id`/`au_id`/`state`/`action_authorized`/`result` | `publicRequest` 返回 `{id, au_id, request_digest, action_authorized, state, created_at, cancel_requested, result, error}` | 同上 |
| `GET /v1/requests/<id>` 与 `/v1/requests/<id>/events?after=` | `path.match(/^\/v1\/requests\/([^/]+)(\/(events\|cancel))?$/)`，events 校验 `after >= 0` | 同上 |
| 事件 JSON 形如 `{events: [...], state}` | `json({ events: journal.events(row.id, au, after), state: row.state })` | 同上 |
| 事件带 `seq` 且需递增游标 | `journal.events(row.id, au, cursor)` 以 `cursor = item.seq` 推进 | 同上 |
| 终止状态 `completed` / `failed` / `interrupted` | `journal.finish(row.id, authorized ? 'completed' : 'interrupted', …)`；`['completed','failed','interrupted'].includes(state)` | `server.ts`、`journal.ts` |
| 结果含 `message` 与 `usage` | `result = await kernel.infer(…)` 后 `journal.finish(..., result, …)`；`publicRequest` 返回 `result`；`usageResult` 产出 `input_tokens`/`output_tokens` 等字段 | `server.ts`、`kernel.ts`、`usage.ts` |
| `usage` 键名为 `input_tokens`/`output_tokens` | `usageResult` 明确返回 `input_tokens`、`output_tokens`、`cached_input_tokens`、`reasoning_tokens` 等 | `services/modeld/src/usage.ts` |
| 授权失效时拒绝采用结果 | `actionAuthorized = !row.cancel_requested && !['failed','interrupted'].includes(row.state)` | `server.ts` |

## 额外一致性发现（对 unknown 语义是有力支持）

modeld 启动时会把上次遗留的在途请求直接终结为 **interrupted**：

```ts
for (const row of this.db.query("SELECT id FROM requests WHERE state IN ('connecting','streaming')").all()) {
  this.finish(row.id, 'interrupted', null, 'service_restarted_result_unknown');
}
```

这与本卡 082/083 的设计完全对齐：**服务重启后的在途执行 = 结果未知，必须核对、不得重放**；我的 `run_loop` 遇到 `model_outcome: unknown` 即停、并用 `reconcile_step` 核对。

## 尚未验证（保持不变）

- 没有真实 modeld 进程与宿主凭据，**仍未做真实推理往返**；本轮是源码级一致性核对，不等于真实运行证据。
- 真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）仍需 `UNION_MODELD_CONFIG` + 运行中的 modeld + 已采用的 AU 连接。

## 下一步

宿主具备凭据后：启动 modeld → 设置 `UNION_MODELD_CONFIG` → 用 `max_calls=2` 的工作跑一次 `run_loop`，记录真实 usage / 费用未知项 / 候选成果，并把 #22 的"真实有界验收"段落补齐。
