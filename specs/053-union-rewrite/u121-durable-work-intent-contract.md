# U-121 / #76 持久工作意图契约与实施计划

2026-11-27，基线 `b0d0043`。#47 完整受控采用，在线 #76 v3 由实际用户认领，所有前置已完成。本契约在行为代码前冻结。依据 Main Chapter V1 D-02/D-03、P-02/P-04、R-01/R-03/R-06/R-08，PRD F06、FRONTEND §4.2、产品 VJ05/工作和成果旅程、ADR-0005/0008/0010，以及 U-112、U-122、U-092、U-093 已交付的作用域。严格 TDD 由用户 AGENTS 指定。

## 单一用户提交

正常 Core Work 页面使用 `/api/v1/work/commands` 五字段 envelope。`start_work_intent.data` 为现有 `start_work` 字段和版本（业务资料须有效 `material_version`），增加 `constraints`（可为空，最多 4,096 字符）和 `delivery_mode`（`automatic_text` 或 `governor_review`）。工作目标和约束只作工作输入；任何文字都不能变更治理、工具、资料、模型或用量授权。`automatic_text` 仅在这项工作批准的同 AU 文本结果范围内采用交付，宪章/组织目标/资源/任职/Mandate/退出等保留事项沿原治理。表单说明批准边界和资料/模型版本；无可用准备应保留目标未采用并提示当前缺口。

成功回执用现有 `succeeded` 仅指意图已持久接受，含 `work_id`, `intent_id`, `attempt_id` 和 `delivery_mode`。不声称模型已调用或成果已交付。原 `id` 是 intent ID，形如 `intent-<AU 摘要>-<随机引用>`，使用 AU UTF-8 SHA-256 的前 24 个小写十六进制字符和 32 个随机十六进制字符。它绑定原组织，原请求核对仅访问该 AU。浏览器在保存引用并提交前核对完整请求不超过 HTTP 的 200,000 UTF-8 字节；工作资料、目标、约束和主体令牌不进入浏览器持久存储。完全相同的原请求返回原持久回执且不再启动；变参、跨账户/组织或旧版本拒绝。未知只查原回执；即使 Core 重启也可查，不发新命令。

可查询 Work 上新增 `intent` 投影，保留 `id`, `status`, `delivery_mode`, `authorized_principal_id`, `attempt_id`, `reason`（当前可行动原因）及存在时的 `decision`。可见状态为 `accepted`, `running`, `waiting_unknown`, `awaiting_decision`, `blocked`, `delivered`, `stopped`，由持久事实驱动。`decision` 仅对应同一候选，至少包含 `result_id`, `result_seq`, `sha256`, `input_cursor` 和合法决定主体 `authorized_principal_id`。工作输入与原执行读取、原回执查询保持各自资格。成果正文和下载仍由原 U-122 分作用域入口提供。

`decide_work_intent` 可对 `governor_review` 的原候选提交一次明确采用交付，data `{work_id,intent_id,result_id,result_seq,sha256,input_cursor,reason}`。须查当前 effective governance、资料/模型/Mandate、原候选及原输入覆盖。成功回执带同一组原引用，省略 `reason`；提交先前有效原命令可查询，不能改写既有决定。`stop_work_intent` data `{work_id,intent_id,reason}` 在当前有效治理授权内停止后续动作，先持久关闭批准，再判断现有执行事实；成功回执带 `work_id,intent_id`，不释放 unknown、重派或宣称远端已取消。旧手工开始/步骤/结果/结算不能改变托管 Work 的已批准流程，仍用于无意图的历史工作。读取、U-093 追加与必要原请求观察保留。

## 原事务、原执行与恢复

1. 在原 `GovernanceStore` AU 事务中验证当前提交身份、版本、有效治理、Work 责任、同 AU 资料/模型版本及有限预算；Work/Member/Binding/Mandate/Definition、原 attempt、批准与接受回执同一次保存。保存失败不启动工作，接受后关闭页面无影响。后台读取原批准及已收存身份，确认对应 Core 账户继续有效、治理和当前结果资格仍存在。受信运行凭据是原批准记录和同 AU/Work 的窄内部引用，不能由公开 JSON、provider、浏览器服务令牌、展示名或主机构造。已有手工调用继续采用当前 Core session。原请求元数据审计可查。
2. 复用原 Work `run_loop`/`run_step`、`work_dispatch` 预留/已派发、`work_recovery` 当前 epoch 和原请求 GET/正式采用。内部版本重验行为沿 U-093，只允许已验证兼容的低影响输入，保留发布版本校验。驱动受本 Work 累计实际占用的调用预算限制，人工 `run_loop` 的 3 轮选择不限制已批准持久工作，但不得扩额。追加输入后仍在批准预算内时，通过原步进机制纳入；后到未采用输入、unknown、失权和未解决副作用阻断正式交付，保留明确原因、继续条件和同一负责人。
3. 运行中候选按原结果记录正规保存。自动文本提交需校验现行批准、治理和资源版本以及同一个原候选、尝试、输入游标和依赖来源；验证后沿现有采用/结束 attempt/交付规则同事务保存，或通过明确的同 Work 持久后继意图可靠接续。批准审查时形成具体待决定对象；模型不能批准自己的交付。撤销、关闭进程或掉线都不能擦除原请求、真实用量、原责任、私有观察或预约。
4. 合法接受后唤醒 WorkService 的受控后台推动。宿主启动扫描已有已采纳且未终结的 V1 intent，绝不自动启动一般手工 Work、旧 AU 或无批准准备态。进程内工作集合只防止同 Work 并发，是提示，不是持久队列。宿主退出让出原 epoch 能力，重开按 U-092 接同一个 attempt。拿不到原结果保留待核对，原 dispatching/unknown 永不重放；只有封存且未越过原 POST 边界时可首次发送。原结果明确且持续有权时，同一采用路径可以推进。
5. 首次成功采纳显式升级 schema 7，已有 1–6 历史继续可读，新 read 不写或迁移。发行预检拒绝未理解持久意图约束的旧安装候选，有意图特征时即使 marker 误写低也拒绝。保持原处于各 schema 的模型、恢复与管理入口，不在更新时降级。

## 验收与并行文件责任

- 当前基线 `b0d0043`，任务分支 `codex/u121-intent-20261127` 复用独立集成 checkout。模式默认 `automatic_text`，可显式选择 `governor_review`。两名实施者按以下不重叠路径严格 TDD，协调者归集 RED/GREEN、核对接口，并在合成前安排规格与权限/身份/计量复审。预计 6–8 小时有效工程，一个可独立验收结果；出现超估或新的独立出口时复评。
- 实际普通 Core 浏览器，从无 Work、无正文、已合法资源准备出发，只提交一次工作意图。真实 HTTP/SQLite/固定 SDK 和受控模型，两轮工具和答复后原 Work 已交付，打开和下载实际原结果。同样的路径覆盖 `governor_review` 之时的具体决定、一次合法决定与不会提前交付，终止/授权变化诚实反馈。
- 严格 API RED 先观察新意图不能接纳，UI RED 先观察正常页只能登记且不推进。失败矩阵含接受事务回滚、重复命令与丢响应、退出/过期仍推进、重启和旧 owner、真权限失效保留使用事实、跨作用域、未知 GET 404 零重 POST、手工命令不能绕过、追加输入不被成果吞掉、保留决定失败和旧安装边界。复用既有测试夹具，真实模型零，部署、迁移另行授权。
- 后端负责 `ai_union` 相应现有模块和窄 Work intent 应用规则、Python 测试与受影响 release 预检。前端负责 `web/console/src` 正常 Work 表单、状态、原回执和用例，可复用 U-122，受控整合浏览器脚本再由协调者接 CI。协调者冻结接口、计划、证据和 Git/看板。规格、权限/身份/费用独立复核，再组合 npm、完整 Python、实际浏览器/API和准确候选七项 CI，读回采用及在线完成。
