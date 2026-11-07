# 079：S03.2e 自动执行基元 `run_step`（U-067 / 在线 #22）

2026-11-08 06:34–07:20。按 2026-11-08 审查处置（P0-1：**S03 下一出口是自动执行循环，冻结新增纯手工 UI**）实现第一个自动执行基元：由模型决定调用哪个只读工具，宿主执行并落回执，模型的最终回答直接成为**候选成果**。

## 本轮用户可验证结果

`POST /api/v1/work/commands` 新增 `kind: run_step`（`data: {work_id}`）：

1. 读阶段（无锁）：校验工作/执行所有权/预算/工具，生成消息与工具 schema（`list_documents`、`read_document`）。
2. **模型调用在事务之外**（与 S02 相同的两阶段纪律），宿主只在拿到结果后开事务。
3. 写阶段（单事务）：预约本次步进 → 按模型请求执行**授权目录内的只读工具**并记录回执（`sha256`/`bytes`/`count`）→ 若模型给出正文则登记**候选成果**（来源=本次工具回执）→ 结算步进为 `used`。
4. 回执含 `step`（如 `work-overview#s1`）、`tool_calls`（次数）、`result`（是否产出候选成果）；重放返回原回执。

失败与边界：

- 宿主未配置模型通道 → `rejected`「宿主尚未配置模型执行通道」（**不产生任何步进事实**，可用于后续重试）。
- 模型通道抛错 → `rejected`「模型通道调用失败，未产生步进事实」。
- 模型请求不支持的工具、或工具参数不是合法 JSON → 整轮回滚（不执行任何工具），不静默降级。
- 模型要读工具但该工作未绑定资料目录 → 拒绝。
- 工具只能读授权目录（沿用 061/062 的 `documents` 适配器），**正文不写入 AU 状态**，只在响应中返回。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-run-step.txt` | 真实 RED：`run_step` 不被支持（3 项：工具回合、纯文本回合、无通道拒绝） |
| `green-run-step.txt` | 21 项 `test_core_work` 通过，含 3 项新用例（伪造 transport 断言：模型请求 `read_document` → 回执含 `sha256`、步进 `used`；纯文本 → 候选成果摘要匹配；无通道 → `rejected` 且含"通道"） |
| `regression-step.txt` | 相关回归 **125 项通过**（3 个 Linux-only 跳过） |
| `management-check.txt` | `npm run check:management` 退出 0 |

过程中修复的三处自身问题（如实记录）：

1. 测试文件插入位置错误，把 `FakeTransport` 插进 `CoreWorkTests` 内部，导致该文件只跑 5 项；已回滚该文件并按模块级重做。
2. `reject_step` 初版写了 `or True` 的伪校验与 `_token` 假字段；已改为正常参数（`directory, intent, request, principal, message`）。
3. 测试替身 `chat` 返回单个 dict，而端口约定是 `(message, usage)`，导致 `AttributeError: 'str' object has no attribute 'get'`（服务线程崩、测试端 `RemoteDisconnected`）；已按端口约定修正替身。

## 所有权与边界

- `ai_union/domain/work.py`：新增 `run_step` 输入形状、`TOOL_SPECS`、`step_plan()`（纯规则：所有权/预算/工具范围/消息与 schema）与 `apply_step()`（预约步进 → 记录工具回执 → 视情登记候选成果 → 结算 `used`）；复用既有 `reserve_step/settle_step/record_tool_call/submit_result`，规则层仍不访问存储、网络与文件。
- `ai_union/application/work.py`：`run_step` 两阶段流程；工具实际读写由 `adapters/documents.py` 在事务内完成；**端口是 `transport.chat(package, messages, tools) -> (message, usage)`**，宿主可通过 `WorkService.transport` 注入（当前未接线真实通道）。

## 未完成 / 下一步（自动循环剩余）

1. **真实通道接线**：把宿主已授权的模型通道（OpenCode Go 订阅，**上限 2 次调用、每次 1024 输出 tokens、仅合成公开资料**）接到 `transport`，做一次**有界真实验收**并记录用量/费用未知项。
2. **循环与终止**：连续多回合（工具→再推理→成果）由谁驱动（宿主循环命令 vs 单步），以及预算用尽/超时的收敛语义。
3. **中断 unknown**：模型通道超时后的核对路径（当前超时=拒绝、不落下步进，符合"未产生事实不重放"）。
4. 冻结新增手工 UI（审查 P0-1）；工作页不再扩功能。

因此本卡仍 `doing`，未做真实模型调用（本轮 transport 为测试替身）。
