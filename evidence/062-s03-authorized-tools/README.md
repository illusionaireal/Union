# 062：S03.2b 授权工具调用与持久回执（U-067 / 在线 #22）

2026-11-07。S03 的第三个可验证子步骤：让“Runtime 调用只读资料工具”成为一个有授权、有回执、可重放、可审计的动作——按责任成员的 Mandate 授权、只读宿主登记的目录、把回执写进 AU 事务。本轮**仍未调用模型**，U-067 保持 `doing`。

前置：U-067 由 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7` 在制（在线 #22 `progress` v6）；S03.2a 已交付 [061](../061-s03-authorised-documents/README.md)。

## 本轮用户可验证结果

`POST /api/v1/work/commands`（`kind: invoke_tool`）+ `GET /api/v1/work`：

- `{"tool": "list_documents", "arguments": {}}` → 返回授权目录内可读文件清单（`["nested/a.md","overview.md"]`），AU 版本 +1。
- `{"tool": "read_document", "arguments": {"path": "nested/a.md"}}` → 返回正文、`sha256`、`bytes`；正文只在响应里，AU state 只留摘要。
- 每次调用在 work 上留下持久回执：`{seq, step_ref: "work-overview#1", tool, arguments, sha256|count, bytes, at}`，工作投影可见 `tool_calls`。
- 拒绝（HTTP 200 + `status=rejected`，不改 AU 状态）：工具不在该工作 Mandate 的 `actions` 内、目录未登记、路径越界（`../outside/secret.txt`、`C:\Windows\win.ini`）、路径是目录、文件不存在。
- 请求形状错误（例如 `path` 为空串）按既有约定返回 **400 invalid_request**，不算产品规则拒绝。
- 同一请求体重放返回**原回执**，不新增 tool_call、不增加版本。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-s03.2b.txt` | 真实 RED：章程直接拒绝 `list_documents`（`章程含不支持的 allowed_tools`）——暴露“AI 根本没有列目录工具”的缺口，2 项失败 |
| `green-s03.2b.txt` | 两轮修正后 7 项通过。修正的 2 处都是我的测试假设：① 重放必须原样重发同一请求体（重算 base_version 会变成另一个请求）；② 空 `path` 属于请求形状错误（400），与规则拒绝（200+rejected）是不同语义——按既有约定分开断言，产品未为测试让路 |
| `regression-s03.2b.txt` | 相关回归 **150 项通过**（1 平台跳过）：documents、core_work、core_creation(+failures)、core_models(+checks/boundaries)、governance×4、core_isolation、core_entrypoints、core_participants、au_contract、console |
| `management-check.txt` | `npm run check:management` 退出 0 |

被测系统真实模型调用 **0** 次；未部署、未迁移真实 AU。

## 所有权与边界

- `ai_union/domain/creation.py`：V1 章程工具词汇加入 `list_documents`（legacy 校验不变，仍只有 `produce_artifact`/`workspace_execute`）。
- `ai_union/domain/work.py`：`TOOLS` 增加 `list_documents`；新增 `invoke_tool` 输入形状与参数精确校验；新增 `tool_target`（按 Mandate `actions` 授权、工作未结束、必须有已登记资料目录、回执上限 50）与 `record_tool_call`（只存摘要与 `step_ref`，不存正文）；`validate_state` 校验回执结构；投影含 `tool_calls`。
- `ai_union/application/work.py`：`invoke` 在同一 `GovernanceStore` 事务内调用 `adapters/documents.py` 完成读写，回执随命令一起提交；重放走原回执；不调用模型、不起 Harness。
- 调用主体仍是**当前治理者**（宿主侧执行者），授权来自成员 Mandate 而非调用者等级——这是本步的临时边界，S03.2c 引入真实执行所有权（attempt/owner）后应由执行所有权决定谁能推进。

## 未完成 / 下一步

1. **S03.2c**：把这些工具接入真实模型循环（infer → tool_call → 回执 → 二次推理），并绑定 attempt 所有权与恢复语义；需要可用模型连接与调用额度（S02 受控替身可先用）。
2. **S03.3**：Harness 候选 → Runtime 复核 → 成果正文/来源保存与采用，工作页/成果页展示、下载与刷新持久。
3. **S03.4**：按 Work/写目标隔离与恢复；React 总览的目标/资料/限额表单。

因此本卡仍 `doing`，不能记为完成。
