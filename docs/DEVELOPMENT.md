# 从新环境接手开发

> 当前模块成熟度、目标完成情况、路线和统一待办见[项目总览](../PROJECT.md)（2026-10-27）。下文日期条目保留各迭代的历史范围；较早的“当前/未完成”描述须结合后续证据阅读。

2026-10-28 下一开发批次：见 [开发路线](DEVELOPMENT_ROADMAP.md)，先 U-022 同构 AU 最小契约和 U-018 观察/调整接口核查，再定义真实任务及修必要缺口。跨 AU 同时任职暂不做；组织演进和平台工具分轨验收。

2026-10-28 管理入口：先读 [PROJECT](../PROJECT.md) 和 [TASKS](../TASKS.md)，任务状态只改 `management/project.json`，运行 `npm run management:render`。`npm run check` 已包含主账/生成视图和管理规则检查；维护说明见 [管理手册](../management/README.md)。

2026-10-17 / 010：默认 API 执行使用 Deep Agents Harness。`npm start` 自动在项目 `.venv` 安装固定依赖；直接开发先 `python3 -m venv .venv`，再 `.venv/bin/python -m pip install -r requirements-harness.lock -e .`，随后用该解释器运行测试与 CLI。Windows 使用 `.venv\Scripts\python.exe`。下文无 Python 依赖的描述仅对应历史版本。筹建、逐次调用、会话恢复及工具测试见 [组织 Harness](ORGANIZATION_HARNESS.md)。

2026-10-16 工作台更正：前端整体更新范围见 [007](../specs/007-workspace-redesign/spec.md)。八页导航与独立 `/models` 已覆盖通用组织；使用入口见 [FRONTEND](FRONTEND.md)。新增 `npm run test:workspace` 验证普通公司、API 连接管理、密钥处理、组织切换和全页面移动端。不要只启动小说演示来验收整体前端。

2026-10-16 更新：开发主分支 `dev`；小说公司首版已接入网页创建、模型 API 配置并绑定/连接测试、经营周期/章节/账本及缺失用量核对。操作入口按页面职责展示。最新范围和使用步骤见 [NOVEL_COMPANY.md](NOVEL_COMPANY.md)，下文旧迭代记录以此更新为准。

更新：2026-10-18（北京时间）。面向只有 GitHub 仓库、没有上一轮聊天或云环境快照的开发者。验收与复盘以 `evidence/` 和 `docs/reviews/` 为准；旧单 HTML 演示和工具已退役，见 [说明](site.md)。

统一开发入口为 `dev`，整合运行时、真实 API 和 React 前端；当前验证见 [dev 集成](../evidence/dev-integration/README.md)。真实 API 后端见 [005](../specs/005-real-model-api/spec.md)，配置与运行按 [API_MODELS.md](API_MODELS.md)。React 运行表单可选择已绑定的默认 API，连接管理表单已由 007 接入（修正此处旧描述）。下文各日期和数量保留其历史验收含义，不替代当前集成证据。

## 1. 读取顺序与当前任务

先读 [当前状态](ai-union/STATUS.md)、[工程交接](../HANDOFF.md)、[PRD v0.6](PRD.md)和[产品设计](product-design.md)。[004 组织操作工作台](../specs/004-organization-console/tasks.md)的 W2–W8 及 [003 观察模块](../specs/003-runtime-dashboard/spec.md)已完成本地 fixture 验收；[005 工程化前端](../specs/005-frontend-engineering/tasks.md)已迁移至 React + TypeScript + Vite；后续从真实执行器的有限试跑缺口继续，不重做已完成原型与服务。

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
