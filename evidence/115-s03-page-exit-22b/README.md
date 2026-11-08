# evidence/115 — 页面级 S03 出口 22-B（真实 Console + 真实 modeld 通道）

## 结论

页面级 22-B 通过：AU 从 `#/tasks` 页面路径完成「登记 → 真实模型执行 → 摘要核对 → 采用 → 交付 → 控制台重建后持久化」全链路，退出码 0，10 项检查全过。

## 环境

- 集成基线：`integration-live` = bb5795b5（PR34 已合入，WorkExecution 在 core tasks 页 readOnly 面板挂载）。
- 通道：`scripts/exit22b_host.py` 以产品 `UNION_MODELD_CONFIG` 构造真实 `ModeldWorkTransport`；连接行通过产品命令面 `save_connection`/`set_connection` 落库（`profile=modeld_grant`，grant 由宿主准备并回传 `grant_ref`）。
- 模型：OpenCode Go `deepseek-v4.1-flash`（宿主 modeld，用户已无限次授权）。
- 工作流：页面经 `/api/v1/governance/commands`（amend_charter → appoint）与 `/api/v1/work/commands`（start_work → start_attempt）登记，随后用页面 readOnly 面板 `WorkExecution` 的「运行 AI 工作」按钮真实执行；采用/交付经 `/api/v1/work/commands`（adopt_result → finish_attempt(delivered) → deliver_work）。

## 检查清单（checks.json）

1. private ticket page loads — 单次票据会话换 cookie，之后只用 origin，不再触碰已消费的 `#launch=`。
2. can_start probe — `core.models.v1` 连接 `connection-a` 已保存且默认启用，`can_start=true`。
3. tasks page reachable — 治理 adopt+activate 后核心 tasks 页出现（governed UI）。
4. work registered and attempt started through the product API — `work-exit` 登记，`work-exit#a1` 尝试开始。
5. candidate result produced by the real model — 页面按钮触发的 run_loop 产出候选，真实调用 modeld（无 fixture/double 介入执行）。
6. result content digest matches recorded sha256 — 结果内容字节 sha256 与产品记录一致。
7. result cites the synthetic nonce — 内容引用本次运行专用 nonce（防重放/串档）。
8. result adopted and delivered — 采用 + delivered 完成项成立。
9. work still delivered after a console rebuild — kill 宿主、同 root 重启后 delivered 保持。
10. adopted result survives the rebuild — adopted 结果在重建后可读。

（errors 中的 `nav ok, models ok: …` 为过程诊断，不构成失败。）

## 沿途修正（对照 #99 指出的缺口）

- 票据单次消费：任何后续导航都改用 origin，禁止 `#launch=` 二次进入。
- core_v1 创建期 `allowed_tools` 只接受 `produce_artifact`/`workspace_execute`；`read_document`/`list_documents` 由 adopt 后 `amend_charter` 授予。
- `can_start` 需要已采用的默认连接；连接行经 `save_connection`（操作异步，轮询 operations 至 succeeded）+ `set_connection(make_default)`。
- `model_accounts.adopt` 对 core_v1 AU 抛 `unsupported_capability`（引擎面仅 legacy）——改走 `models/commands` 产品路径，未绕过任何边界。
- 结果 sha256 语义 = **结果内容字节**，不是源资料；22-B 不变式按结果内容核对并要求引用 nonce。

## 遗留

- 22-C 页面级（流中取消）可复用本宿主/流程骨架，待下一轮。
- 本证据不关闭 #39/#40 以外的任何卡；仅作为 #39 页面级补充证据。
