# 从新环境接手开发

## 2026-11-13：按当前分支和完整产品契约接手

从最新 `origin/rewrite/charter-v1` 建个人任务分支，PR目标是 `rewrite/charter-v1`；dev仅供历史核查及未来单独集成，不从它继续V1卡。先读实时Kanban原卡/评论、[完整体验](product-design.md)、[前端合同](FRONTEND.md)，再读该卡实际消费的053/领域合同；本地没有新U卡章节不构成回到旧任务的理由。

U-110冻结全局旅程，U-111–115及既有反馈/持续性卡按同一结果验收。U-118封闭旧 `ops/dev-orchestrator` 的新派发/本地任务写权；新开发复用 `ops/automation` 与统一在线adapter。宿主注册会复制配方，修改仓库不会自动升级副本；本轮仓库修正不声称已部署或已核验宿主采用。

下文日期化记录中的旧分支、下一任务、工时、检查数和状态都是当时证据，不覆盖本节及实时卡。

## 2026-11-11：先定义完整旅程，再拆实现

用户已授权执行[产品审计修正](reviews/2026-11-11-kanban-charter-product-audit.md)。旧 AU 适配和旧 UX 保留退出重构目标；U-110 先冻结整套 V1 体验，后续 UI 执行卡必须注明其所属旅程、消费契约、文件责任及整体验收。2–8 小时粒度不应把用户目标拆成相互缺入口的按钮，也不能以单次任务 MVP 替代完整组织产品。

本次 U-109 只交付任务重排与约束纠正；U-111–U-115 是后续实现，现有 #41–#50 等反馈/持续性卡仍保留。按实际公开创建、成果、执行、恢复合同确定前置；工程验证不无依据地等待整张真实验收父卡。新增未开工卡不自动占 WIP，原 owner/progress/blocked 责任不得隐藏。工程支持、限定真实验证和完整用户/持续验收分别记录。

源码保留现有正确行为，UI 可按新契约替换，必要回归保障随功能迁移；旧测试冻结了错误交互时更新其契约和断言，不能通过削弱身份/权限/unknown 语义让测试通过。实时布置与依赖只从在线 Kanban 查询，[U-109 证据](../evidence/U-109/README.md)只是本次交付记录。

## 2026-11-08：每次执行先评估粒度，运行态只读 Kanban

本节是当前开发协作规则。下方历史条目中的主账状态、开始时间、容量和“下一步”不参与在线任务准入；涉及产品定义和验收仍遵守 Chapter V1 与对应契约。

### 一张执行卡的规定粒度

- **一个可独立验收的结果，通常 2–8 小时有效工程工作量**，包括核对实现、修改、验证和交接。估算用于计划，不是工期承诺，也不是模型调用或长作业的超时限制。
- 预计超过 8 小时，或包含两个及以上可分别交付的结果，必须先尝试拆分，再实施。优先按用户结果、功能模块的完整行为或独立缺陷拆；一个必要的前端/API/存储闭环可以跨模块，不按技术层机械割裂。
- 小于 2 小时的独立修复可以保留一张卡；函数修改、断言和顺序步骤放 checklist。若拆开会破坏同一事务或不可分割的兼容切换，在卡上记录原因、工作量和检查点，保留最小完整变更。
- 一张执行卡须写明：问题和结果、具体文件/模块范围、非目标、工作量、验收操作与证据、真实前置依赖，以及拆分或不拆分的理由。工程验证、真实接入、用户验收分别列明；需要资源的验收写清资源、限额、责任人和解除条件。

### 每次开始、恢复和交付

1. 读取实时 board 和相关评论，核对依赖、优先级、负责人、版本与现有拆分，避免重复建卡。先按卡片范围做粒度预评估；已有负责人且仍在开发的卡不能抢占。
2. 对可认领任务用当前 `version` 与实际 `user.id` 认领，收到成功回执后才核对关联仓库实现、验收和未提交修改。编码前复评粒度；需要拆分时先将子卡、估算、范围、依赖和验收写入 Kanban，再推进合格的执行卡。
3. 父卡保留完整目标、已有证据和未完成验收；子卡写“上级卡 #ID”，父卡用 checklist/描述列出子卡 #ID。当前 API 没有专门父子字段，不把归属关系伪装成前置依赖。子卡继承真正未完成的前置；父卡等待子卡、子卡又依赖父卡的环不允许出现。
4. 分拆不自动改变他人负责人、原认领、原依赖或 WIP 算法，也不把 blocked 移到 backlog 隐藏占用。已有负责人从下一次推进开始应用本规则。需要调整依赖时说明消费的接口/成果和依据，保存在线更新回执后才能按新依赖执行。
5. 每次恢复先检查上次估算与范围；已合格且没有变化时复用原评估，不反复拆分或刷评论。发现新增独立结果、范围扩张或估算超限时重新拆分。每小时运行可以只完成一个检查点，不要求一小时关闭整卡。
6. 严格 TDD 与风险相称的验证照常执行。把实际进展、提交、验证和剩余项写回执行卡；父卡只有在全部约定出口通过后完成。遇到阻塞，在原卡记录原因、证据、责任人和解除条件，并在 Kanban 团队交流区发起求助，写清原卡编号及需要谁提供什么；不发布凭据，不在每轮检查重复同一求助。无可认领卡时等待后续检查。

开工记录模板（写入卡片描述或一条评论；后续仅记录变化）：

```text
粒度评估：结果=…；范围/非目标=…；预计=…小时；拆分/不拆分理由=…
关系：上级卡=…；子卡=…；真实前置=…；当前负责人/版本=…
验收：操作与预期=…；验证命令/证据=…；真实资源条件=…
本轮：检查点=…；剩余范围=…；阻塞责任与解除条件=…
```

### 本次补充的独立工程卡

任务认领、状态和进度只在 [UNION Kanban](https://union-kanban.361102304.workers.dev/) 查询；以下仅记录稳定范围与验收，不镜像运行态。

| 任务 | 范围与粒度预评估 | 验收重点 |
| --- | --- | --- |
| #31 / U-077：Kanban 运行态统一 | CLI/MCP/kanban-client 的在线读写与 WIP 来源；一个统一协作结果，预计 4–8 小时；超限由执行者再拆 | 本地历史 started_at/WIP 不挡在线认领；依赖/已有负责人保护；版本冲突与超时核对；访问失败不退回本地；运行态不自动写入 project.json |
| #32 / U-078：跨平台测试修复 | tests/test_documents.py 的目录链接越界测试及必要测试准备；一个跨平台安全行为，预计 2–4 小时 | Linux symlink 与 Windows junction 都验证越界读取/枚举拒绝、根内正常读取和安全清理；仅对明确宿主能力缺失跳过；两平台证据分别记录 |

两项修复已有实现中的问题，没有未完成业务前置，彼此独立；不等待 U-067/U-075 的剩余业务交付。上述是开发范围，不代表代码修复已完成。U-077 的执行者还须核对 CLI/MCP 及其余说明中残留的旧规则。

### 在线来源与交付边界

Kanban API 是认领、负责人、状态、依赖、评论及 WIP 的唯一运行态来源；`management/project.json` 仅在交付提交同步长期路线与证据，不反向覆盖 Kanban。在线 API 未提供容量上限时如实记为未提供，不从本地历史推断。在线访问失败必须报告真实原因，不能用仓库镜像代替。

凭据优先使用 `UNION_KANBAN_KEY`；执行上下文已获用户明确授权的既有凭据可临时使用，不把值写入代码、任务提示词、提交、评论或日志。认领必须使用最新版本并核对成功回执；409 或不确定写入先读回核对。用户已于 2026-11-08 明确允许当前开发阶段直接上传 GitHub 仓库：上传前 fetch，合并实际并发变更并验证上传后的分支/提交；不覆盖他人未提交内容。生产部署、新增或轮换密钥、付费及不可逆外部操作保留单独的决定边界。完整接口约定见 [Kanban 开发说明](../management/KANBAN.md)。

## 2026-11-05：从 Main Chapter V1 接手

先读[采用记录](CHARTER_ADOPTION.md)、[Chapter V1](UNION_CHARTER_v1.0.md)、[PRD v1.0](PRD.md)、[总体架构](ARCHITECTURE.md)、[053 plan](../specs/053-union-rewrite/plan.md)与根[HANDOFF](../HANDOFF.md)。S01a–S01c 的稳定 principal、准备态创建/重开和旧入口隔离见 [056](../evidence/056-s01-core-creation/README.md)。S05/U-069 的本地治理、修章/撤权及责任交接见 [契约](../specs/053-union-rewrite/s05-contract.md)和 [057](../evidence/057-s05-governance/README.md)。S02/U-072 和 S03 的实际任务依赖、负责人及 WIP 以开工时 Kanban API 为准，后续资源授权分别核对。

旧DESIGN/PRD/spec仅在核对实现历史或具体兼容时读取，不能覆盖V1。下方日期条目的工具数、状态和“下一步”不作为当前开发依据。使用当前固定工具链和相应测试；保持React、历史数据和有效回归，具体切片遵守严格TDD。

新空库初始化 **auth schema 2 / catalog schema 1**。auth 0/1 旧库会拒绝新服务启动；在明确授权的维护窗口停止服务后，使用随包交付的 `python scripts/upgrade_core_identity.py --root <console-root> --services-stopped`。命令取得 console 锁、保存一致备份并在事务中升级；旧登录会话失效，原 principal 与创建 payload/receipt 保留。新 schema 区分 owner/core 并保存逐账号失败窗口；一个普通账户成功登录不会清除另一账户的失败次数。重复升级保持原主体与旧回执字节。升级后有新写入便不能用旧备份回退；代码采用/回滚也检查 schema 兼容。此说明不是对真实数据迁移的执行授权。

AU 新建仍用 schema 1；成功的显式治理采用才升至 schema 2。初次合法规则拒绝可保存原回执，但不改变 AU schema/原始创建事实。治理采用后旧代码若不声明 schema 2 支持，安装器拒绝采用、回滚与启动；读操作不自动转换。普通核心参与者可在登录页登记，以自己的 principal 创建或确认治理邀请；账户重置只能重建宿主 owner，不能接管旧 AU，且不删除其他参与者。密码恢复保持原主体并使旧会话失效。

Windows 验证固定 Node 24.19.0、`.venv\Scripts\python.exe`（本次 3.13.14），设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。S01 真实浏览器入口为 `node scripts/check_core_creation.cjs`，S05 为 `node scripts/s05-governance-browser.cjs`；与 `npm run check`、Python 全量、`npm run test:workspace` 及实际安装后的升级测试一起取证。各脚本只使用独立临时测试主机。构建安装候选成功不代表 S08 真实发布或持续运行已验收。

## 2026-11-06：S02 模型检查与显式协议

S02 的实现、独立复核、实际浏览器和安装结果见 [058](../evidence/058-s02-model-tools/README.md)，精确行为见 [s02-contract](../specs/053-union-rewrite/s02-contract.md)。原 Codex 真实连接认证失败保留；用户后来新指定的兼容 API 已完成两次推理、一次资料读取及安装包重启，真实结果页面另有 14 项 Chromium 检查。已有真实请求只查询原 ID，不重跑验收 driver；真实配置、登录恢复信息及派发标记仅保存在宿主私有目录。

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

## 2026-11-08：S03 自动执行的宿主模型通道（`UNION_MODELD_CONFIG`）

V1 的自动执行（`POST /api/v1/work/commands` 的 `kind: run_step` / `kind: run_loop`）**默认没有模型通道**，调用会返回"宿主尚未配置模型执行通道"的拒绝。宿主需要显式接线：

1. 准备宿主私有的 modeld 配置（回环 `origin` + `admin_token_file` / `worker_token_file`，令牌文件 32–256 字符、二者不同；非 Windows 需 0600 权限）；
2. 启动工作台前设置环境变量 `UNION_MODELD_CONFIG=<该配置文件路径>`；
3. 工作台启动时会把 `Console.work.transport_factory` 接成 `modeld_factory(该路径)`，`run_step` 才会真正发起模型请求。

失败语义（与证据 085/082 对应）：

- 配置缺失/格式非法 → 建立通道时抛 `Rejected` → 回执 **rejected**，**不留下步进、不占调用预算**；
- 通道超时、5xx、`interrupted` → 回执 `succeeded` + **`model_outcome: unknown`**，并留下一条 `status: unknown` 的步进，**预算保持占用**；必须用 `kind: reconcile_step` 核对（`used`/`released`/`failed` + 依据）后才释放；
- 4xx/422 明确拒绝、`action_authorized=false` → **rejected**，可重新发起。

用量与费用：每次步进记录 `usage{input_tokens,output_tokens}` 与 `cost_status: unknown`；核心不估算金额、未知不写 0。真实有界验收仍在等待网络与宿主通道（≤2 次调用、每次 ≤1024 输出 tokens、仅合成公开测试资料）。

离线验证：`tests.test_core_work`、`tests.test_work_transport`、`tests.test_work_transport_http`（真实回环 HTTP 替身）、`tests.test_core_work_http`（API→步进→通道→工具→候选成果端到端）。
