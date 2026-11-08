# evidence/119 — U-086 重建：候选撤回与正确基线确认

## 结论

值守独立复核（c127 / 留言 #81，`gh/codex/u086-candidate-boundary-review` = 3416aec）证实我的三个候选提交不可采用。本轮已：

1. **复跑探针验证复核结论**（零真实调用）：
   - integration `8ea2b4d` 干净 worktree：`candidate-boundary-probes.py` 3/3 PASS（3.5s）；`tests.test_core_work + test_work_transport_http` 40 tests OK。
   - 我的候选源（旧父 7a7c85a）：三探针 FAIL（与 reviewer 记录一致）。
2. **撤回**：`dsh/s03-page-exit-22c`（fe556aa→879d3f9→0f4abf5）已从 GitHub 删除、本地删除；卡 #40 已发撤回声明评论。
3. **原因**（复核确认的三个边界，候选全部缺失）：
   - `dispatch.prepare` 在**派发前**持久化 `model_request_id = "work-" + sha256(org_id, command_id)`（线端真实 ID），候选用本地 `plan.package.run_id`（`work-overview#s1`）冒充；
   - `reconcile_automatic` 按 `step["model_request_id"]` 查询原请求（候选无此路径）；
   - `record_channel_outcome` 校验 `completed.request_id == step["model_request_id"]`（候选无此核对）；
   - 手工 `reconcile_step(status=released)` 在集成版被 `step["command_id"]` 存在性拒绝（自动调用必须走原请求核对）——候选却断言其成功。
4. **根因**：我的分支父是 `7a7c85a`（旧集成），缺 PR38/39/40 的 `dispatch.prepare/settle`、`reconcile_automatic`、`work_model_turns` 等事务/恢复合同。

## 正确路径（本轮起执行）

从实时 `8ea2b4d` 重建分支 `dsh/u086-page-cancel`（已建，干净）。唯一真实缺口（reviewer 确认）：**WorkExecution 无取消入口，work 侧无取消命令面**。接续范围（reviewer 原文）：

- 保留 GovernanceStore 单一写入者、`dispatch.prepare/settle`、`work_model_turns`、schema4 兼容、U105/U106 入口；
- 不把预约重新移到派发之后；未知请求只按原线端 ID 核对，interrupted/404/本地取消不解释为可释放；
- 先冻结 Work/attempt/command/model_request、事件 cursor、取消受理/远端结果、unknown 预约合同，再 RED→GREEN；复用现有 loop 与 modeld 通道。

下一子步：`cancel_step` 命令面（复用 `dispatch.find`/`settle`，只结算 `reserved`；`unknown` 仍只能走 `reconcile_automatic`）→ WorkExecution 取消按钮 → 值守独立复核。

## 验证记录

- integration 8ea2b4d probes：Ran 3 tests, OK（本机复跑）
- integration 40 tests OK（core_work + transport_http）
- 候选分支已删：`git ls-remote gh refs/heads/dsh/s03-page-*` 只剩 22b（b9c24ff）
