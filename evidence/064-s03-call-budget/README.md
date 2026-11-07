# 064：S03.2d 工作调用额度预约与结算（U-067 / 在线 #22）

2026-11-07 23:55–00:15。执行所有权（063）之后，接进模型循环前还缺一件事：**每次执行尝试消耗的调用必须有归属、用途与预约**（F12 / D-05、R-07）。本轮把这块做成可验证的 API 行为，**仍未调用模型**，U-067 保持 `doing`。

## 本轮用户可验证结果

`POST /api/v1/work/commands` 新增 `reserve_step` / `settle_step`，`GET /api/v1/work` 投影新增 `steps` 与 `budget`：

- `reserve_step {"work_id"}` → 生成 `work-overview#s1`，`status=reserved`、`purpose=work_step`、`attempt_id` 指向当前执行尝试；**必须已有进行中的 attempt**（否则拒绝并提示先开始执行）。
- `settle_step {"work_id","step_id","status","reason"}` → `used`（真的用掉）、`released`（放弃释放）、`unknown`（结果未知，**保留预约**直至核对）。
- 上限：每一步占 1 次调用，`reserved + used` 不得超过该工作的 `max_calls`（示例 4 次；第 5 次被拒并提示调用上限）。
- 已结算的步进不能改判（「该步已经结算」），历史保留。
- 投影示例：`budget={max_calls:4, reserved:0, used:1}`、`steps=[{step_ref,attempt_id,status,purpose,at,settled_at,reason}]`。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-s03.2d.txt` | 真实 RED：`reserve_step`/`settle_step` 不被支持、投影无 `budget`（2 项失败） |
| `green-s03.2d.txt` | 11 项 `test_core_work` 通过；1 处失败是我的期望值算错（`unknown` 保留预约，故 4 条都在额度内），产品语义正确、改的是测试 |
| `regression-s03.2d.txt` | 相关回归（documents/core_work/core_creation×2/core_models×3/governance×4/isolation/entrypoints/participants/au_contract/console） |
| `management-check.txt` | `npm run check:management` |

被测系统真实模型调用 **0** 次；未部署、未迁移真实 AU。

## 所有权与边界

- `ai_union/domain/work.py`：`STEP_STATUSES`/`SETTLED`；`budget()`（reserved 含 unknown、used 单列）、`reserve_step()`（要求 active attempt、按 work `max_calls` 封顶）、`settle_step()`（只允许从 reserved 结算）；`validate_state` 校验步进结构（`work_id#s{n}`、purpose、attempt 前缀）；投影含 `steps`/`budget`。规则层不触存储/模型。
- `ai_union/application/work.py`：命令在同一 `GovernanceStore` 事务内落步进事实；不发起调用。
- 与 S02 的 `resource_grant`/`occupied_calls` 分开：S02 管“连接验证”的两次调用；S03 管“有责任工作”的每次步进，二者不互相记账。

## 未完成 / 下一步

1. **S03.2e**：`step` 与真实模型请求配对（infer → tool_call → 回执 → 二次推理），失败/超时按 `unknown` 结算并核对，不重放。
2. **S03.3**：成果正文/来源保存与采用，工作页/成果页展示、下载、刷新持久。
3. **S03.4**：按 Work/写目标隔离与恢复；React 总览的目标/资料/限额表单。

因此本卡仍 `doing`。
