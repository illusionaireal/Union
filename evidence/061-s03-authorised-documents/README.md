# 061：S03.2 授权只读资料目录（U-067 / 在线 #22）

2026-11-07。S03 的第二个可验证子步骤：把"AI 只读宿主机授权目录"从口号变成可执行的安全边界——宿主登记资料 root、AU 只以引用标识指定、解析时拒绝越界与目录链接逃逸，并在工作投影中如实报告资料是否真的可用。本轮**没有**调用模型、没有执行 Harness、没有成果产出，U-067 仍为 `doing`。

前置：主账 U-066/U-069/U-072 均 `done`；在线 #22 ready、无人认领 → 本地主账认领为 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`（租约 180 分钟）。

## 本轮用户可验证结果

`GET /api/v1/work?organization_id=…` 的工作条目新增 `materials` 投影：

- 未登记或引用无效：`{"reference": "project-docs", "available": false, "documents": 0}` —— 如实报告不可用，不假装可读。
- 宿主在 `<console-root>/document-roots.json` 登记并放好文件后：`{"reference": "project-docs", "available": true, "documents": 1}`。

配套规则收紧（`POST /api/v1/work/commands` `kind: start_work`）：声明 `read_document` 工具却把 `materials_root` 留空，现被拒绝并说明原因；只用 `produce_artifact` 的工作仍可不指定资料目录（同一请求内验证的正例）。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-s03.2.txt` | 真实 RED：`tests.test_documents` 因适配器不存在而 ERROR；`read_document` 无资料目录仍被接受（FAIL） |
| `red-s03.2b-projection.txt` | 投影 RED：`KeyError: 'materials'`（工作投影尚无资料可用性） |
| `green-s03.2.txt` | 两轮 GREEN 后 14 项通过（含 junction 逃逸拒绝；首轮 2 处失败均为测试夹具假设：`write_text` 在 Windows 写 CRLF、以及列目录是否含二进制文件——保留"列出范围内普通文件、读取时才明确拒绝二进制"的产品行为，改的是测试期望，产品未为测试让路） |
| `regression-s03.2.txt` | 相关回归 **130 项通过**（1 平台跳过）：core_work、core_creation、core_creation_failures、core_models、governance×4、core_isolation、core_entrypoints、core_participants、au_contract、console |
| `management-check.txt` | `npm run check:management` 退出 0 |

被测系统真实模型调用 **0** 次；未部署、未迁移真实 AU、未登记真实宿主目录。

## 所有权与边界

- `ai_union/adapters/documents.py`（新）：宿主登记表 `<console-root>/document-roots.json`（仅宿主写）；引用标识校验；绝对/盘符/UNC/NUL/`..`/空段全部拒绝；用 `resolve(strict=True)` 后与 `realpath(root)` 做包含性判定，因此符号链接与**目录 junction** 逃逸都会被拒；`list_documents` 只报范围内普通文件（上限 200），`read_text` 拒绝二进制与超过 256 KiB 的文件，返回正文、SHA-256 与字节数。该适配器不写、不建、不迁移。
- `ai_union/domain/work.py`：`apply` 增加"声明 read_document 必须指定已登记资料引用"，`validate_state` 增加对应的历史一致性校验。
- `ai_union/application/work.py`：读取投影补 `materials`（只统计可读文档数，不读正文），失败即 `available:false`。
- 局部 AGENTS 已同步（adapters/domain/application），说明新所有者边界。

## 未完成 / 下一步

1. **S03.2b**：把 `read_document`/`list_documents` 注入 Harness（Runtime 选择工作 → infer/invoke_tool），工具回执与 `step_ref`/attempt 持久配对。
2. **S03.3**：Harness 候选 → Runtime 复核 → 成果正文/来源保存与采用，工作页/成果页展示与刷新持久。
3. **S03.4**：按 Work/写目标隔离与恢复；React 总览的目标/资料/限额表单。

尚未有前端资料目录选择、未接真实模型、无成果下载，因此本卡不能记为完成。
