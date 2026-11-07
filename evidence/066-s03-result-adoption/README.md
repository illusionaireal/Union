# 066：S03.3b 成果提交与采用（U-067 / 在线 #22）

2026-11-08 03:55–04:20。本轮交付"成果"这一环的**责任与可信性**：候选成果必须绑定执行尝试与已有来源回执，正文摘要可校验，只有治理者能采用，采用后不能覆盖。**仍未调用模型**（AI 产出留下一步），U-067 保持 `doing`。

## 本轮用户可验证结果

`POST /api/v1/work/commands` 新增 `submit_result` / `adopt_result`；`GET /api/v1/work` 投影新增 `results`（不含正文）：

- `submit_result {"work_id","result_id","title","content","sources"}` → 生成候选成果，回执含 `sha256`、`bytes`、`sources`、`attempt_id`；**必须持有进行中的 attempt**；正文 ≤32KB，每工作 ≤20 份。
- `sources` 必须是**本工作已存在的执行步进或工具回执**引用（`work-overview#s1` / `work-overview#1`），未知来源、跨工作引用、重复引用一律拒绝——成果因此可追溯到"读了哪些资料、花了哪些调用"。
- `adopt_result {"work_id","result_id"}` → 只有治理者可采用；采用前**重算摘要**，正文与登记摘要不一致则拒绝（防篡改）；已采用的不能再次采用或覆盖（「已经采用」），保留 `adopted_at`/`adopted_by_principal_id`。
- 投影只给 `{id,title,sha256,bytes,sources,status,created_at,adopted_at}`，**正文不进入读投影**（工作页只显示标题+摘要+状态）。
- 工作页「AI 工作（V1）」面板新增"成果"一行：`项目概览（第一版）（已采用 · abcdef012345…）`；无成果时显示「尚无候选成果」。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-s03.3b.txt` | 真实 RED：两个命令不存在、投影无 `results`（2 项失败） |
| `green-s03.3b.txt` | 13 项 `test_core_work` 通过；1 处失败是我测试里"没产生来源就引用"（产品规则正确，改测试） |
| `regression-s03.3b.txt` | 相关回归 **156 项通过**（1 平台跳过） |
| `frontend-check.txt` | `npm run check:console` 退出 0：**20 文件 / 198 项前端测试** + `tsc` + `build`（首轮 1 处失败是 Tasks 夹具缺 `results` 字段，已补） |
| `management-check.txt` | `npm run check:management` 退出 0 |

## 所有权与边界

- `ai_union/domain/work.py`：`submit_result` / `adopt_result` 纯规则（来源可追溯、摘要、采用前置校验、上限、状态机）；`validate_state` 校验成果结构（摘要长度、candidate/adopted 与 `adopted_at` 一致）；投影去正文。
- `ai_union/application/work.py`：命令在同一 `GovernanceStore` 事务内落成果与采用事实；不调用模型、不写文件。
- 前端：`CoreWorkResult` 类型 + 面板"成果"行 + 两项测试；只读展示，无新增写操作按钮。

## 未完成 / 下一步

1. **S03.2e（关键）**：真实模型循环 infer → tool_call → 回执 → 二次推理，产出候选成果并 `submit_result`；失败/超时按 `unknown` 结算、核对、不重放。需要**可用模型连接与有限调用额度**。
2. **S03.3c**：成果正文读取/下载端点（当前正文只在 AU 事务内保存，尚无 HTTP 读取）与成果页。
3. **S03.4**：按 Work/写目标隔离与恢复；总览的目标/资料/限额表单。

因此本卡仍 `doing`。
