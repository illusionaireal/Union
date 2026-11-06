# 从新环境接手开发

## 2026-11-05：从 Main Chapter V1 接手

先读[采用记录](CHARTER_ADOPTION.md)、[Chapter V1](UNION_CHARTER_v1.0.md)、[PRD v1.0](PRD.md)、[总体架构](ARCHITECTURE.md)、[053 plan](../specs/053-union-rewrite/plan.md)与根[HANDOFF](../HANDOFF.md)。S01a–S01c 的稳定 principal、准备态创建/重开和旧入口隔离见 [056](../evidence/056-s01-core-creation/README.md)。S05/U-069 的本地治理、修章/撤权及责任交接见 [契约](../specs/053-union-rewrite/s05-contract.md)和 [057](../evidence/057-s05-governance/README.md)。S02/U-072 和 S03 必须在完整 S05 受控工程验收后继续；主账状态、容量、在线负责人及后续资源授权需在开工前重新核对。

旧DESIGN/PRD/spec仅在核对实现历史或具体兼容时读取，不能覆盖V1。下方日期条目的工具数、状态和“下一步”不作为当前开发依据。使用当前固定工具链和相应测试；保持React、历史数据和有效回归，具体切片遵守严格TDD。

新空库初始化 **auth schema 2 / catalog schema 1**。auth 0/1 旧库会拒绝新服务启动；在明确授权的维护窗口停止服务后，使用随包交付的 `python scripts/upgrade_core_identity.py --root <console-root> --services-stopped`。命令取得 console 锁、保存一致备份并在事务中升级；旧登录会话失效，原 principal 与创建 payload/receipt 保留。新 schema 区分 owner/core 并保存逐账号失败窗口；一个普通账户成功登录不会清除另一账户的失败次数。重复升级保持原主体与旧回执字节。升级后有新写入便不能用旧备份回退；代码采用/回滚也检查 schema 兼容。此说明不是对真实数据迁移的执行授权。

AU 新建仍用 schema 1；成功的显式治理采用才升至 schema 2。初次合法规则拒绝可保存原回执，但不改变 AU schema/原始创建事实。治理采用后旧代码若不声明 schema 2 支持，安装器拒绝采用、回滚与启动；读操作不自动转换。普通核心参与者可在登录页登记，以自己的 principal 创建或确认治理邀请；账户重置只能重建宿主 owner，不能接管旧 AU，且不删除其他参与者。密码恢复保持原主体并使旧会话失效。

Windows 验证固定 Node 24.19.0、`.venv\Scripts\python.exe`（本次 3.13.14），设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。S01 真实浏览器入口为 `node scripts/check_core_creation.cjs`，S05 为 `node scripts/s05-governance-browser.cjs`；与 `npm run check`、Python 全量、`npm run test:workspace` 及实际安装后的升级测试一起取证。各脚本只使用独立临时测试主机。构建安装候选成功不代表 S08 真实发布或持续运行已验收。

## 2026-11-06：S02 模型检查与显式协议

S02 的实现、独立复核、实际浏览器和安装结果见 [058](../evidence/058-s02-model-tools/README.md)，精确行为见 [s02-contract](../specs/053-union-rewrite/s02-contract.md)。所选 Codex 真实连接认证失败，成功往返仍未验收。已有真实请求只查询原 ID，不重跑验收 driver；真实配置仅保存在宿主私有目录。

模型相关 Python 回归为 `tests/test_core_model*.py`；全量仍用固定 `.venv\Scripts\python.exe -m unittest discover -v` 和 `npm run check`。Bun 1.4.2 请对 `services/modeld/test/*.test.ts` 的八个实际文件传递显式路径，避免把 vendor 测试也选入。实际浏览器脚本为 `scripts/s02-models-browser.cjs`，设置固定 `UNION_BUN`、`UNION_PYTHON` 和私有 `UNION_S02_UI_EVIDENCE`；它只使用回环供应商，不能替代真实连接。

成功显式模型配置/授权或采用 `read_document` 规则才使 AU 进入 schema 3；已知旧 schema 不读时升级。modeld 仅在成功显式协议注册的同一事务采用 schema 1，新代码支持 0/1。受支持发布器声明 AU `[1,2,3]`、modeld `[0,1]`，先核版本再采用/启动；旧候选不兼容时保留数据和原请求。安装包内执行 Python 维护/验收脚本应使用 `-B`，避免在不可变交付目录生成额外缓存文件。

## 2026-11-02：进入正式开发

用户确认从MVP进入正式开发。后续按[正式开发与交付标准](FORMAL_DEVELOPMENT.md)推进：工程子项、真实集成、用户闭环、发布与持续运行分别验收。043的受控证据保留，未通过的真实账号/模型/部署/经营不升级。下一工程切片为候选版安装升级回滚包，任务状态见主账与TASKS。

2026-10-30：下一实现为 [028 成员执行与托管计划](../specs/028-member-runtime-management/plan.md) 的 U-041，随后 U-042；仅计划已交付。现有在制 U-007/U-037 仍受阻，真实主机沿用 U-008，勿重复创建部署验收卡或直接重写组织循环。

> 当前模块成熟度、目标完成情况、路线和统一待办见[项目总览](../PROJECT.md)（2026-10-27）。下文日期条目保留各迭代的历史范围；较早的“当前/未完成”描述须结合后续证据阅读。

2026-10-28 持续批次020–025已提交：见[收口](../evidence/026-batch-closeout/README.md)。原先U-004/U-033等下一批已完成；当前就绪队列为空，先解除模型/真实工作区/主机阻塞，不重复做规划或假装真实验收通过。

2026-10-28 批次完成：U-022 [核心契约](../specs/019-au-core-contract/spec.md)与 U-018 [角色能力核查](AU_CAPABILITY_AUDIT.md)已交付；下一批 U-004 + U-033，详情以主账为准。

2026-10-28 下一开发批次：见 [开发路线](DEVELOPMENT_ROADMAP.md)，先 U-022 同构 AU 最小契约和 U-018 观察/调整接口核查，再定义真实任务及修必要缺口。跨 AU 同时任职暂不做；组织演进和平台工具分轨验收。

2026-10-28 管理入口：先读 [PROJECT](../PROJECT.md) 和 [TASKS](../TASKS.md)，任务状态只改 `management/project.json`，运行 `npm run management:render`。`npm run check` 已包含主账/生成视图和管理规则检查；维护说明见 [管理手册](../management/README.md)。

2026-10-17 / 010：默认 API 执行使用 Deep Agents Harness。`npm start` 自动在项目 `.venv` 安装固定依赖；直接开发先 `python3 -m venv .venv`，再 `.venv/bin/python -m pip install -r requirements-harness.lock -e .`，随后用该解释器运行测试与 CLI。Windows 使用 `.venv\Scripts\python.exe`。下文无 Python 依赖的描述仅对应历史版本。筹建、逐次调用、会话恢复及工具测试见 [组织 Harness](ORGANIZATION_HARNESS.md)。

2026-10-16 工作台更正：前端整体更新范围见 [007](../specs/007-workspace-redesign/spec.md)。八页导航与独立 `/models` 已覆盖通用组织；使用入口见 [FRONTEND](FRONTEND.md)。新增 `npm run test:workspace` 验证普通公司、API 连接管理、密钥处理、组织切换和全页面移动端。不要只启动小说演示来验收整体前端。

2026-10-16 更新：开发主分支 `dev`；小说公司首版已接入网页创建、模型 API 配置并绑定/连接测试、经营周期/章节/账本及缺失用量核对。操作入口按页面职责展示。最新范围和使用步骤见 [NOVEL_COMPANY.md](NOVEL_COMPANY.md)，下文旧迭代记录以此更新为准。

更新：2026-10-18（北京时间）。面向只有 GitHub 仓库、没有上一轮聊天或云环境快照的开发者。验收与复盘以 `evidence/` 和 `docs/reviews/` 为准；旧单 HTML 演示和工具已退役，见 [说明](site.md)。

统一开发入口为 `dev`，整合运行时、真实 API 和 React 前端；当前验证见 [dev 集成](../evidence/dev-integration/README.md)。真实 API 后端见 [005](../specs/005-real-model-api/spec.md)，配置与运行按 [API_MODELS.md](API_MODELS.md)。React 运行表单可选择已绑定的默认 API，连接管理表单已由 007 接入（修正此处旧描述）。下文各日期和数量保留其历史验收含义，不替代当前集成证据。

## 1. 读取顺序与当前任务

先读 [当前状态](ai-union/STATUS.md)、[工程交接](../HANDOFF.md)、[当前PRD](PRD.md)和[产品设计](product-design.md)。[004 组织操作工作台](../specs/004-organization-console/tasks.md)的 W2–W8 及 [003 观察模块](../specs/003-runtime-dashboard/spec.md)已完成本地 fixture 验收；[005 工程化前端](../specs/005-frontend-engineering/tasks.md)已迁移至 React + TypeScript + Vite；后续从真实执行器的有限试跑缺口继续，不重做已完成原型与服务。

已实现 Python 本地运行时、CLI 和正式 React 工作台；旧独立演示/原型已退役。OpenRouter 普通对话与 CLI 连接已实测，工具协作和业务质量尚未验收；本地 fixture 使用不需要模型凭据。运行入口及恢复见 [CONSOLE.md](CONSOLE.md)。

```bash
npm ci --ignore-scripts
npm start -- --root .union/console --port 8766 --open
```

原治理设计在 `docs/ai-union/DESIGN.md`，最初开发任务在同目录的 `DEVELOPMENT.md`，上传原件在 `docs/inputs/`；它们保留来源，不代表当前完成状态。旧 UNION 平台在 `docs/baseline/`、`docs/kickoff/` 和 `spikes/`，继续保留独立任务线及历史编号。

## 2. 工具和首次验证

运行时使用 Python 3.11+、SQLite 和固定 SDK 依赖；Linux 互斥使用 `fcntl`，Windows 使用 `msvcrt`。2026-10-18 当前回归为 136 项 Python、16 项前端及 5 项启动，见 [011](../evidence/011-openrouter-smoke/README.md)。2026-10-14 Linux／Python 3.12.14 通过 55 项测试，前端 Chromium 实际验收 60 项通过；此前 Windows／Python 3.13.14 的 53 项测试继续保留。React 迁移尚未在 Windows 实机或远端 CI 复验。无需数据库服务；SDK 安装见上文，模拟测试不需要 API Key。Windows 使用 `.venv\Scripts\python.exe`。

旧平台检查和浏览器工具使用 `.nvmrc` 指定的 Node.js 24.19.0。安装对应版本后，从仓库根目录执行：

```bash
.venv/bin/python -m unittest discover -v
npm ci --ignore-scripts
npm run check
```

Python 测试验证组织机制、静态服务和执行器接口替身；Node 检查历史计划、旧动作安全实验及前端类型、10 项交互/数据测试与构建。两者都不调用模型，不证明真实组织能力。两个 CI 工作流分别执行这些范围；本地浏览器验证不自动等于远端 CI 通过。

## 3. 重建完整模拟场景

以下目录必须不存在；再次运行选择新的目录，不重置原组织或覆盖历史证据：

```bash
.venv/bin/python scripts/validate.py \
  --root .union/first-fixture \
  --output .union/first-fixture-evidence
.venv/bin/python -m ai_union --root .union/first-fixture status
.venv/bin/python -m ai_union --root .union/first-fixture context --work-id work-followup
```

脚本预期退出 0，包含当前 55 项机制／接口／服务测试与 CLI 场景，得到 2 名成员、3 项工作、3 份模拟文本成果和 6 次 fixture 调用。内部 `evaluate` 返回 3 表示模拟结果，脚本按此预期检查；不要将其修改为真实通过。

不依赖 `.union/validated-final`、`/tmp` 目录、旧登录、进程或端口。新环境自己生成 fixture；数据库、`board.key` 和私有执行记录留在被忽略的 `.union/`，只有公开证据进入 Git。

## 4. 正式工作台与浏览器验证

开发使用 `dev` 分支。正式构建：`npm run build:console`；启动：`npm start -- --open`；工作台检查：`npm run test:workspace`；小说业务模块检查：`npm run test:novel`。启动器准备项目 Python 依赖，直接执行测试/CLI 先按 [Harness 安装](ORGANIZATION_HARNESS.md)建立 `.venv`。

```sh
UNION_CHROMIUM_PATH=/usr/bin/chromium UNION_PYTHON=.venv/bin/python npm run test:workspace
UNION_CHROMIUM_PATH=/usr/bin/chromium UNION_PYTHON=.venv/bin/python npm run test:novel
.venv/bin/python scripts/check_console_start.py
```

浏览器检查使用临时服务、回环供应商和明确标识的模拟数据。默认输出在 `.union/`，新公开验证使用新的证据目录。旧单 HTML 进展页、原型、旧工作台和报告，以及它们的源码/生成/部署/专用验收工具已删除；历史证据和提交继续保留，不再运行旧生成流程。见 [退役说明](site.md)。

OpenRouter 凭据可使用环境设置中的 `openrouter_key`，普通免费模型测试见 [011](../evidence/011-openrouter-smoke/README.md)。供应商普通对话成功不代替 Harness 工具兼容或小说质量验收。

## 5. 后续实施与完成定义

| 顺序 | 任务 | 完成证据 |
| --- | --- | --- |
| 已完成 | 004 W2 受信会话与组织范围，服务端校验角色、来源、版本和权限 | 观察者直接调用写接口被拒绝，密钥不进入浏览器。 |
| 已完成 | 003 观察服务及 [review](../specs/003-runtime-dashboard/review.md) 两项修复 | 活跃执行不误报；同版本事件／用量更新、乱序及恢复通过 A01–A10。 |
| 已完成 | 004 W4–W5 幂等命令、作业与持久暂停意图 | 暂停停止新派发并等待在途回执；未知结果核对，不退款或盲目重派。 |
| 已完成 | 004 W6–W7 前端接入实际服务 | 浏览器 fixture 闭环及 C01–C09，证据见 [004](../evidence/004-organization-console/README.md)。 |
| 已完成 | 004 W8 管理后台模型设置及启动覆盖 | C10、CLI 模型与资源并发校验及独立 review，见 [模型设置增量](../evidence/004-organization-console/model-settings-2026-10-13/README.md)。 |
| 已完成 | 005 React + TypeScript + Vite 前端工程、同源构建与启动 | 55 项 Python、10 项前端、60 项实际浏览器、5 项启动检查，见 [005](../evidence/005-frontend-engineering/README.md)。 |
| 6 | 有限真实 Agent 与业务接入 | 明确调用范围和费用未知条件后记录 E1/E2；真实交付／反馈另需渠道。 |

`runner.exclusive` 同时保护 CLI 与网页运行、管理变更。暂停意图已持久化，并在调用预约事务内检查；仍不支持远程取消确认。ERP／CRM 等按 [软件复用方案](software-reuse.md)接入。

资金和权限实现采用前需要另一工程角色复核；此次交接不表示生产采用获准。新缺口同步 STATUS、HANDOFF、Spec 与 Tasks，保留失败证据。

## 6. 可直接交给下一开发者的任务

> 阅读 AGENTS.md、STATUS、HANDOFF、CONSOLE.md 与 005 前端工程、004 历史验收记录，核对工作区及当前实现。005、W2–W8 和观察模块的本地 fixture 范围已完成，不从原型重做。下一优先事项是有限真实执行器烟雾及 E1/E2：先核对执行器版本和实际登录、既有调用授权与额度；只有在明确有限范围及费用未知条件后才调用。使用独立组织，保留所有失败、费用不确定性和实际成果。缺少真实条件时如实记录，不把 fixture 验收当真实能力。Linux 已在 005 验证，另核对 Windows 迁移和远端 CI 结果。真实对外交付、反馈及部署继续按各自授权处理。
