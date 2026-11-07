# 063：S03.2c 执行所有权与未知结果（U-067 / 在线 #22）

2026-11-07 22:45–23:20。用户要求「由 DSH 接手看板里 goose 名下的任务」。本轮做两件事：把交接写成事实，并交付 S03 的执行所有权边界（把工具接进模型循环前必须先有的 R-03 前提）。**仍未调用模型**，U-067 保持 `doing`。

## 交接（goose → DSH）

- 事实：本机已无 goose 进程，`union-autodev`（`0 */2 * * *`）不再触发；最后提交停在 18:05。看板账号本身即 `HOME-GOOSE`（`cafeef64-…`），U-067 与 U-075 挂在它名下。
- 处理：本地主账把 **U-067、U-075 的 owner 改为 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`**（租约 240 分钟）；在线 #22/#28 先读回 version，再 PATCH 到 `progress` 并评论交接说明（#22 v6→comments 4、#28 v5→v6/comments 3，均读回确认）。
- 防重复：`ops/automation/README.md` 增加「DSH 接手」一节，写明同一时刻只保留一条驱动线；本轮每轮仍先看 `git log -1`，50 分钟内已有提交则只核对。

## 本轮用户可验证结果

`POST /api/v1/work/commands` 新增两个命令，并与工具调用绑定：

- `start_attempt {"work_id"}` → 生成 `work-overview#a1`，状态 `running`，记录 `owner_principal_id`、`started_at`；同一工作已有进行中或未知执行时拒绝。
- `invoke_tool` 现在**必须**有一次进行中的 attempt：没有则拒绝（「该工作没有进行中的执行尝试」），回执里写入 `attempt_id`。
- `finish_attempt {"work_id","attempt_id","outcome","reason"}` → `delivered|failed|stopped` 关闭该 attempt；`unknown` 将其置为 `unknown` 并**阻塞**后续 `start_attempt` 与 `invoke_tool`，直到用显式 outcome + 理由改判（改判留 `reason` 与 `ended_at`）。
- 工作投影 `GET /api/v1/work` 增加 `attempts`，历史 attempt 全部保留，已结束的不能再次改判。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-s03.2c.txt` | 真实 RED：4 项失败——`start_attempt`/`finish_attempt` 不被支持，且工具调用在没有执行所有权时也能跑（正是 D-01/R-03 缺口） |
| `green-s03.2c.txt` | 实现后 9 项 `test_core_work` 通过（含两条既有工具测试改为先持有 attempt，属规则收紧而非迁就测试） |
| `regression-s03.2c.txt` | 相关回归 **152 项通过**（1 平台跳过） |
| `management-check.txt` | `npm run check:management` 退出 0 |

被测系统真实模型调用 **0** 次；未部署、未迁移真实 AU。

## 所有权与边界

- `ai_union/domain/work.py`：`MAX_ATTEMPTS=20`、`OUTCOMES`；`start_attempt`/`finish_attempt`/`active_attempt` 纯规则；`tool_target` 返回当前 attempt；`record_tool_call` 增加 `attempt_id`；`validate_state` 校验 attempt 结构与状态；投影新增 `attempts`。规则层仍不访问存储/模型/文件。
- `ai_union/application/work.py`：命令分支把 attempt 事实写在同一 `GovernanceStore` 事务；不启动执行、不调用模型。
- 局部 AGENTS（domain/application）与 `ops/automation/README.md` 同步更新。

## 未完成 / 下一步

1. **S03.2d**：把 infer → tool_call → 回执 → 二次推理接进真实模型循环，attempt 作为唯一执行所有权；未知结果走现有 `finish_attempt(unknown)` + 核对，不重放。
2. **S03.3**：成果正文/来源保存与采用，工作页/成果页展示、下载、刷新持久。
3. **S03.4**：按 Work/写目标隔离与恢复；React 总览的目标/资料/限额表单。

因此本卡仍 `doing`。
