# 070–071：S03.4 隔离与"完成有依据"（U-067 / 在线 #22）

2026-11-08 05:49–06:20，两个子步骤各自独立提交。补上两个治理要求：同一授权目录不能被两个工作同时占用执行（R-07），工作完成必须有已采用的成果（D-03）。**仍未调用模型**，U-067 保持 `doing`。

## 070 / S03.4a：共享资料目录的执行隔离（`524b2e8`）

- `start_attempt` 现在检查：**同一 AU 内另一个工作若使用同一 `materials_root` 且存在 running / unknown 的执行**，则拒绝并提示"另一个工作正在使用同一资料目录；请等它结束或为该工作指定其他目录"。
- 不同资料目录的工作互不影响；未知执行只阻塞同目录工作，不阻塞其他工作（R-04）。
- TDD：`red-isolation.txt`——真实 RED（第二个工作在同目录下照样开始了执行）→ `green-isolation.txt`（15 项 `test_core_work` 通过）→ `regression-isolation.txt`（83 项通过）。

## 071 / S03.4b：工作完成必须有已采用成果（D-03）（提交见下）

- 新命令 `deliver_work {work_id, result_id}`：只有**该成果已采用**、且**没有进行中的执行**时，才把工作置为 `delivered`，记录 `delivered_at`、`delivered_by_principal_id`、`delivered_result_id`。
- 顺序故意先校验"已采用"（D-03 的核心）再校验"执行已结束"，两条拒绝信息可区分；已完成的工作不能被再次完成（"该工作已经完成或已结束"），之后 `invoke_tool` 等动作一律拒绝。
- 投影新增 `delivered_at`、`delivered_result_id`；`validate_state` 校验"完成状态 ↔ 完成时间 ↔ 成果引用"三者一致。
- TDD：`red-deliver.txt`——真实 RED（`KeyError: 'receipt'`，命令不存在）→ `green-deliver.txt`（16 项通过）→ `regression-deliver.txt`（**127 项通过**）、`management-check.txt` 退出 0。

过程中发现并修掉两个自身缺陷：① 最初把 `status` 塞进 receipt，覆盖了回执状态导致审计一致性校验失败——改为独立字段 `receipt["work"]`；② 我在 `validate_state` 里写了一行 `or True` 的伪校验，已改为真正的成果引用检查。

## 验证

- Python：`tests.test_core_work` 16 项、相关回归 127 项通过（含 documents / creation / models / governance×4 / console / isolation / entrypoints / au_contract）。
- `npm run check:management` 退出 0。
- 真实模型调用 **0** 次；未部署、未迁移真实 AU。

## 未完成 / 下一步

1. **S03.2e（关键阻塞）**：真实模型循环 infer → tool_call → 回执 → 二次推理 → `submit_result`；需要可用模型连接与有限额度。
2. **S03.1 UI 补全**：总览的目标/资料/限额表单（目前创建 V1 工作仍走 API）。
3. **S03.4c**：中断恢复（服务重启后 running attempt 的处理与核对路径）与更细的写目标互斥。

因此本卡仍 `doing`。
