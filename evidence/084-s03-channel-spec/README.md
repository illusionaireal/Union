# 084：真实通道接线的接口规格与离线验证（U-067 / 在线 #22）

2026-11-08 06:59–07:35。网络仍不可达（GitHub HTTPS 与看板 API 均已中断约 11 小时），无法做真实模型往返。本轮不再凭猜测实现 modeld 适配器（协议事件格式无法离线验证，硬写等于制造未验证外围），改为**把接线所需的精确条件写成规格**，并对 8 个本地提交做一次完整离线验证。

## 1. 已就绪：V1 侧端口与调用链

| 环节 | 现状 | 位置 |
| --- | --- | --- |
| 端口 | `chat(package, messages, tools) -> (message, usage)`，经 `WorkService.transport` 注入 | `ai_union/application/work.py` |
| 规划 | `step_plan()` 产出 `package`（`work_id`/`attempt_id`/`run_id`）、`messages`（system=Agent 定义指令，user=工作目标）、`tools`（仅 `list_documents`/`read_document` 的 JSON Schema） | `ai_union/domain/work.py` |
| 应用 | 模型返回后：执行授权工具 → 记回执 → 正文登记候选成果 → 步进结算 `used`；通道异常 → 未知步进 + 保留预约 + `reconcile_step` | `ai_union/application/work.py` |
| 循环 | `run_loop` 轮次 = `min(3, 剩余预算)`；未知即停；原请求重放返回原回执 | 同上 |
| 用量 | 步进级 `usage{input_tokens,output_tokens}` + `cost_status=unknown` | 同上 |
| 测试替身 | `FakeTransport` / `Failing` 两类，覆盖 29 项 `test_core_work` | `tests/test_core_work.py` |

## 2. 接线还缺什么（宿主侧）

**A. 模型通道端点**：需要一个实现 `chat(package, messages, tools)` 的对象。两条候选路：

1. **modeld**（S02 路径，`ai_union/model_service.py`）：`ModelServiceClient` 已有
   - `call(method, path, body, *, admin=False, timeout=10)`
   - `request(request_id, au_id)` → `GET /v1/requests/<id>?au_id=…`
   - `events(request_id, au_id, after)` → `GET /v1/requests/<id>/events?au_id=…&after=…`
   - 请求体字段（照 `ModelServiceTransport.chat`）：`id/run_id/au_id/connection_id/connection_revision/grant_ref/grant_revision/model_id/messages/tools/generation.maxOutputTokens/deadlines`
   - **待确认**：`events()` 返回的事件类型与字段（成功结果、用量、失败/取消的确切形状），以及创建请求用 `POST /v1/requests` 还是既有 outbox 路径。`model_service.py` 里 SSE 解析在旧 transport 内，未导出可复用的解码器。
2. **直接供应商 API**（`model_api`/`model_protocols`）：四协议已实现，但需要真实网络与密钥。

**B. 连接配置来源**：V1 AU 的 `model_access.connections[<id>]` 需含 `model`、`max_output_tokens`、`grant_ref`/`grant_revision`（modeld 路径）或 API 端点/密钥（直连路径），且已被采用为默认连接。

**C. 授权与额度**：用户已授权 OpenCode Go 订阅做**首次有界验收**：≤2 次调用、每次 ≤1024 输出 tokens、仅合成公开测试资料。`run_loop` 的 `turn_cap` 会自然收敛到 2；每次调用的 usage 会记在步进上，费用保持 unknown。

**D. 触发方式**：`POST /api/v1/work/commands`，`kind: run_loop`，`data: {work_id}`；需要先有已采用的默认连接与一次进行中的 attempt。

## 3. 本轮离线验证（覆盖全部 8 个本地提交）

| 检查 | 结果 |
| --- | --- |
| `npm run check` | 退出 0（前端 206 项 + 管理/计划/动作安全） |
| `npm run check:management` | 退出 0 |
| Python 全量 `-m unittest discover` | 见 `python-full.txt` |
| 相关回归（work/governance/models/console/workspace/documents/creation/isolation） | 126–130 项通过（随轮次累计） |
| 真实模型调用 | **0** |

## 4. 本地提交清单（待推）

`d5e779f`（U-078 junction 修复）→ `29f2d5a`（执行绑定宿主实例）→ `6bfb910`（执行摘要）→ `c4dd401`（run_step）→ `fa4e184`（run_loop）→ `b16b1f3`（用量披露）→ `0b32f26`（未知保留预约 + reconcile_step）→ `3d08270`（未知即停 + 预算内轮次）。

任务分支：`dsh/s03-work-runtime`（未切换工作区，避免影响共享 checkout 中他人未提交文件）。

## 5. 下一步（按优先级）

1. **网络恢复**：推 `dsh/s03-work-runtime` → 开 PR（按 AGENTS 规则 8 由协调者审阅合入）。
2. **确认 modeld 事件协议**（上文 2.A 待确认项）：拿到后即可写 `ModeldWorkTransport` 并用现有 `FakeTransport` 测试补齐事件解析分支。
3. **一次有界真实验收**：≤2 次调用、≤1024 tokens、仅合成资料；记录真实 usage、费用未知项、候选成果与工作流转结果，作为 #22「自动循环 + 真实有界验收」证据。
