# 085：modeld 工作通道适配器 + "明确拒绝 / 结果未知"分离（U-067 / 在线 #22）

2026-11-08 06:59–07:40。网络仍不可达，真实模型往返无法进行。本轮把**真实通道的代码侧**补上，并修掉一个语义缺口：此前**任何**通道异常都被当成"结果未知"（保留预约），但"服务明确拒绝（4xx/422）"意味着请求**确实没执行**，应当直接拒绝、不留预约。

## 1. 新增 `ai_union/work_transport.py`

`ModeldWorkTransport(client, au_id, connection, timeout_seconds=…)` 实现 V1 端口 `chat(package, messages, tools) -> (message, usage)`，协议**逐项对照**既有 `ModelServiceTransport.chat`（`ai_union/model_service.py`，非猜测）：

- `POST /v1/requests`，body 字段：`id/run_id/au_id/connection_id/connection_revision/grant_ref/grant_revision/model_id/messages/tools/generation.maxOutputTokens/deadlines`；
- 轮询 `GET /v1/requests/<id>?au_id` 与 `/events?after=`，终止状态 `completed|failed|interrupted`；
- 成功读 `result.message` 与 `result.usage`；`action_authorized=false` → 拒绝采用；
- 步进引用 `work-overview#s1` 会转成请求安全标识 `work-overview-s1`（`#` 不合法）。

**失败契约（关键）**：

| 情形 | 抛出 | 运行时含义 |
| --- | --- | --- |
| 4xx / 422 等明确拒绝 | `Rejected` | **确实未执行**：不留步进、不占预算 |
| 其他（503、超时、中断） | 其他异常 | **结果未知**：保留预约，等 `reconcile_step` |

## 2. 应用层配合

`run_step` 现在分别处理：`Rejected` → `reject_step`（无步进事实）；其他异常 → `unknown_step`（保留预约 + `model_outcome=unknown`）。

## 3. 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-adapter.txt` | 真实 RED：模块不存在（`ModuleNotFoundError: ai_union.work_transport`） |
| `test-adapter.txt` | 适配器 5 项：成功返回 message+usage 且请求体字段正确（含 `#`→`-` 转换）、422→`Rejected`、503→仍是未知类、`interrupted` 不当作结果、`action_authorized=false` 拒绝 |
| `red-definite.txt` | 应用层真实 RED：明确拒绝时此前被当成"未知"并留下步进（`'succeeded' != 'rejected'`） |
| `green.txt` | `test_core_work` 30 项 + `test_work_transport` 5 项全部通过 |
| `regression.txt` | 相关回归（work/adapter/governance×2/models/console/workspace/documents/creation/isolation） |
| `management-check.txt` | `npm run check:management` |

过程中修掉自己一处错误：新测试用例忘了导入 `Rejected`，导致 `NameError` 被当成"未知"路径（反而证明了两条路径的区别生效）；补导入后通过。

## 4. 边界与未验证项（必须如实说明）

- 适配器**只按既有 modeld 协议实现**，**尚未对真实 modeld 运行过**（网络/服务不可用）。事件形状、`result` 字段、`action_authorized` 均照 `ModelServiceTransport` 的既有用法，未经真实进程复验。
- 宿主接线仍需：`ModelServiceClient` 的宿主私有配置（回环地址 + 双令牌）、AU 连接配置（`grant_ref/grant_revision/model/max_output_tokens`）、以及一次进行中的 attempt。
- 真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）仍待网络恢复。

## 5. 下一步

1. 网络恢复：推任务分支 → PR；启动 modeld，用授权额度跑一次 `run_loop`，核对真实 usage 与费用未知项。
2. 若 modeld 不可用：改用直连供应商路径（`model_api`/`model_protocols`）实现同一端口，同样先受控再真实。
