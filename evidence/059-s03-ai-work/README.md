# 059：S03.1 提交目标并承担工作（U-067 / 在线 #22）

2026-11-07。用户已授权自动推进 V1 卡；本轮在 `rewrite/charter-v1` 上只完成 S03 的**第一个可验证垂直子步骤**：一名责任主体（当前治理者）为一个目标登记 AI 成员、Agent Definition、责任绑定、Work 与根授权，并读回“负责成员 / 有效授权 / 所用模型 / 待执行”。

前置核对：主账依赖 U-066、U-069、U-072 均为 `done`；在线 #22 无人认领、version 3、依赖卡 #20/#24/#21 已 done，因此把卡置为就绪后认领（在线 PATCH 到 progress，HTTP 200，version 4），本地主账同步 `doing`。

## 本轮用户可验证结果

`POST /api/v1/work/commands`（`kind: start_work`）+ `GET /api/v1/work?organization_id=…`：

- 只有**当前治理者**可发起；普通参与者在同 AU 内为 403 `not_authorized`。
- 必须已有**有效激活**的本地治理（准备态、到期或退出都被拒），且当前治理账号仍存在。
- 必须已配置并**采用为默认**的启用模型连接；请求里的连接必须匹配当前 revision。
- 工具必须在当前**有效章程** `allowed_tools` 内（默认章程只有 `produce_artifact`，请求 `read_document` 先被拒，修章后才通过）。
- 调用上限必须不超过 AU 计划**剩余**次数（12 次计划下请求 13 被拒）。
- 资料目录只接受宿主已登记的**引用标识**，`/etc/passwd`、`C:\docs`、`..\secrets`、`a/b` 一律拒绝；API 从不接收宿主机路径。
- 标识重复被拒；同一请求 ID 重放返回**原回执**，AU 版本不增加、不产生第二份 Work。
- 成功时 AU 版本 +1，并同一命令内登记 AI Member、Definition v1、binding、Work(pending)、根 Mandate；读取投影显示 `capabilities.execution = "not_started"`，不冒称已执行。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-s03.1-initial-fixture.txt` | 首次运行暴露的是测试夹具问题（参与者取版本前先读了被拒的 AU），保留原样 |
| `red-s03.1.txt` | 修正夹具后的真实 RED：`/api/v1/work/commands` 404“接口不存在”、无 WorkService（3 项失败） |
| `green-s03.1-first.txt` | 首轮 GREEN 尝试暴露两处测试期望错误（mandate 投影漏 `active`、元组解包错误），产品未为此改动 |
| `green-s03.1.txt` | 3 项行为测试通过 |
| `regression-s03.1.txt` | 相关回归 85 项通过（core_work、core_creation、governance、governance_persistence、core_models、core_model_boundaries、au_contract、console） |
| `python-full.txt` | Python 全量 582 项：9 项平台跳过，1 项错误 |
| `workspace-symlink-env.txt` | 唯一错误为宿主无权创建符号链接（WinError 1314）的既有环境限制，单独复现，与本次改动无关 |
| `verification.json` | 汇总（含 `npm run check:management` 结果） |

`npm run check:management` 通过（15 模块 / 8 里程碑 / 76 任务，管理测试 8 项）。

## 所有权与边界

- `ai_union/domain/work.py`：纯规则（授权、有效治理、章程工具、默认连接、调用上限、引用与路径拒绝、状态校验、读取投影），无存储/模型/主机调用。
- `ai_union/application/work.py`：在唯一 `GovernanceStore` 事务内启动工作；重放返回原回执；不调用模型、不启动 Harness、不读文件。
- `adapters/governance_store.py`：`read_in`/`save` 增加 `work.validate_state`，仍是 AU 事实的唯一写入者；未升级 `schema_version`（新增段落惰性创建、可选的向后兼容读取，不迁移旧数据）。
- `console.py`/`server.py` 只装配与路由；新增 AGENTS 说明已随模块更新。

## 未完成 / 下一步

本步**没有**执行模型、没有读取真实目录、没有成果页与下载、没有前端工作台表单，因此 U-067 仍为 `doing`，不能记为完成：

1. S03.2：宿主只读 root 登记 + AU 范围授权 + `list_documents/read_document`，step_ref/attempt/工具回执持久配对（含 junction/范围外拒绝）。
2. S03.3：Harness 候选 → Runtime 复核 → 成果正文/来源保存与采用，工作页/成果页展示与刷新持久。
3. S03.4：按 Work/写目标隔离与恢复；React 总览的目标/资料/限额表单。

测试系统真实模型调用 0 次；使用临时目录与显式 modeld 替身；未部署、未迁移真实 AU。
