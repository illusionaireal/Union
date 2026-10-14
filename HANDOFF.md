# 当前工程交接

## 2026-10-14：统一 dev 集成分支

已将运行时工作台 `cd6d062`、真实 API `6ce24b7`、React 前端 `8179d6e` 整合到 `dev`，保留源分支历史，`main` 不变。冲突涉及 README、交接和状态文档，保留两侧成果与证据。Python 服务同时提供 React 构建及新增 API 路由。

API 配置/绑定/连接测试沿用 [API_MODELS.md](docs/API_MODELS.md) 的 CLI 和 HTTP 契约；React 运行表单可选择已经绑定的默认 API 连接，专门的连接管理表单仍由后续前端工作接入。整合后的检查记录见 [dev 集成验证](evidence/dev-integration/README.md)。

## 2026-10-14：React 前端工程

用户要求完成 React + TypeScript + Vite 正式工作台，已在 `feat/react-typescript-console` 接续远端 `cd6d062`，保留其 Python/SQLite/会话/命令能力。七页、URL 筛选、TanStack Query 读取与轮询、操作表单/预览/回执以及详情分别维护。Vite 产物由 Python 同源提供，首次 `npm ci --ignore-scripts` 后运行 `npm start -- --root .union/console --port 8766 --open`；开发观察模式见 [FRONTEND.md](docs/FRONTEND.md)。

已验证 Linux／Python 3.12.14／Node 24.19.0／Chromium：55 项 Python、10 项前端、60 项实际 HTTP/浏览器、5 项启动检查及 9 项旧动作检查通过。新证据位于 [005](evidence/005-frontend-engineering/README.md)，原验证与独立 review 保留。真实模型调用 0；没有 Sites/Figma/Canva 可调用工具，没有外部站点或设计平台发布。

旧实际单 HTML `ai-union-console.html` 和源码 `design/console-legacy/` 归档；设计演示、进展和完成报告仍保留。正式入口读取 `web/console/dist/`，构建不提交，新克隆必须安装/构建。不要重新把正式应用拼装回单 HTML。

迁移验收修正了连续筛选 URL 更新的竞态，以及数据库离线暂停导致错误连接状态的问题；断网禁用写操作，命令不排队，已确认回执不被晚到错误覆盖。Windows 迁移及远端 CI 结果尚未取得。下一业务任务仍是明确有限调用范围后的真实执行器烟雾/E1/E2，以及独立渠道/反馈验收。

## 2026-10-13：真实 API 后端升级

用户授权后端真实 API 升级并提交代码，前端由另一位同事实施。本次基于 `cd6d062`，独立分支 `feat/real-model-api`，不修改前端源码或生成 HTML。

新增版本化私有 API 配置、组织默认绑定、实际连接测试、Chat Completions 执行器、CLI 和受信 HTTP 命令。密钥不进入工作包、正式状态、事件、命令日志或回执；配置命令只保存完整参数指纹。连接测试预约一次调用，保留原暂停状态，不消费业务事件。运行固定连接版本，unknown 不自动重试，金额仍为未知。

前端同事从 [API_MODELS.md](docs/API_MODELS.md) 第 2 节接入 `GET /api/model-connections`、`api_connection`、`api_binding`、`api_test` 与 `start.executor=api`。读取列表仅限董事会会话，写操作沿用原幂等命令、基准版本和回执协议。页面应保存配置后刷新版本；API 运行选择连接，不提交 Codex `model`。

新证据见 [005](evidence/005-real-model-api/README.md)。本地 HTTP 替身完整协作闭环为 simulated；评估现已接受真实 API 证据，并排除连接测试与回环服务。缺少用户配置的供应商密钥，真实供应商烟雾及 E1/E2 继续待验证。历史验证结果和文档记录保持各自日期含义。

## 2026-10-13：管理后台模型设置

用户要求补齐后台模型配置。现在可在“组织设置 → 模型设置”按组织保存／清除 Codex 默认模型，启动时覆盖本次值；回执固定 `requested_model`。CLI 省略 `--model` 时同样沿用组织默认，模型解析与金额硬上限检查都在派发锁内执行，避免并发设置竞态。保存不启用 Codex、不调用模型，实际使用说明见 [CONSOLE.md](docs/CONSOLE.md)。

最终验证为 53 项 Python、53 项 HTTP／Chromium 检查及 Node 24.19.0 历史检查；[新证据](evidence/004-organization-console/model-settings-2026-10-13/README.md)与[独立 review](docs/reviews/2026-10-13-model-settings.md)单独保存。真实模型仍未调用；原 W2–W7 结果保留。

## 2026-10-13：最终复验与完成报告

独立 review 的六项发现已修正或复核完成。当前 Windows／Python 3.13.14 再次通过 47 项测试、45 项实际浏览器检查，Node 24.19.0 历史检查通过；新证据位于 `evidence/004-organization-console/2026-10-13/`。已完成 A01–A10／C01–C09 映射、文档一致性同步和[单页 HTML 报告](ai-union-completion-report.html)，报告离线可读并支持复制启动命令及打印。

跨机器同步曾将完整目录移入大小写冲突副本；已在 `D:/Project/Union` 恢复项目自身 Git 元数据和最后修复，并重跑验证。独立审阅记录保留其 Python 3.12.10 环境事实。后续使用 Git 分支检查点接手，先核对 `git rev-parse --show-toplevel`，避免在缺少 `.git` 时落入父目录其他仓库。没有推送、合并或公开部署本轮成果。

## 2026-10-12：工作台实际服务已交付

基线为远端已核对的 `9732983`，继续使用 `feat/ai-union-runtime-console-handoff`。本次完成 004 W2–W7 及 003 观察模块：本机会话、组织范围、同源读写 API、幂等回执、版本检查、有限作业、持久暂停、运行活性、一致快照及七视图单 HTML 前端。

启动：`python -m ai_union.server --root .union/console --port 8766 --open`。默认仅启用 fixture；浏览器完成创建、运行、查看成果、暂停、事件、资源、修章及核对，不需要为日常操作回到 CLI。Windows 和 Linux 的启动说明见 [CONSOLE.md](docs/CONSOLE.md)。

验收：47 项 Python 测试、45 项实际 HTTP／Chromium 检查，完整 fixture 仍为两成员、三工作、三成果、六次调用；`npm run check` 在 Node 24.19.0 下检查历史计划及 9 项旧动作安全测试。实际结果与逐项映射在 [004 evidence](evidence/004-organization-console/README.md)。本机为 Windows，Linux 新代码及远端 CI 结果尚未取得；CI 已增加 Windows 机制验证。授权／持久化经[另一工程角色复核](docs/reviews/2026-10-12-console.md)。

关键恢复规则：服务重启使旧浏览器会话失效，使用新生成的启动链接；旧运行不自动重放。读取不会恢复执行，缺少 owner 匹配的宿主活性显示未确认；启动取得互斥锁后检查遗留记录，未知结果需有依据核对。创建存储失败保持原请求 unknown，保留分配目录，管理员核对前不重建。

下一优先事项：在明确有限调用与费用未知条件后，以独立组织验证真实执行器烟雾及 E1/E2。真实模型调用仍为 0；未接入真实交付、市场反馈或 ERP／CRM，未部署或合并主分支。不要再从原型或 W2 开始重做本轮。

## 以下为基线 9732983 的历史交接

下文保留先前迭代的决定、证据与当时缺口；其中“未实现网页服务”等状态已由上节更新。

更新时间：2026-10-12（北京时间）。首轮范围为 `001-org-bootstrap`；用户要求“开始构建”，附件作为本轮产品依据。原文保留于 `docs/inputs/`，其中的指令是交接资料，不是获得外部账号、预算或发布权限的依据。

## 完成度

运行时机制实现及确定性验证已完成。最新用户澄清要求可操作的前端，P0 已升级为组织操作工作台，Dashboard 是其中的观察模块。PRD v0.2、产品设计及操作高保真原型已补齐；**实际会话、读写 API 与运行控制未实现，真实组织试跑未完成，首版体验未验收**。

| 行为 | 当前工程证据 | 真实证据 |
| --- | --- | --- |
| F01 目标、组织、章程与资源 | SQLite 状态、采用记录、CLI init/status | 目前仅本地测试采用 |
| F02 临时启动与组织形成 | 一次性授权和至少两成员校验；fixture 从决定形成组织 | 模型自组织未运行 |
| F03 决定提交 | 身份、授权、版本、引用校验；批次回滚与拒绝记录 | 执行器输出待实测 |
| F04 成员执行 | Codex submit/status/result 适配；两成员依赖测试 | Codex 登录已发现，调用 0 次 |
| F05 成果与来源 | 内容寻址文件、完整性校验、版本修订与事件 | 目前三份模拟成果 |
| F06 后续行动 | 依据成果的决定创建并执行后续工作 | E2 模型判断未验证 |
| F07 岗位调整与交接 | 任职连续、旧任职撤权、在途回执拒绝 | E3 暂仅机制测试 |
| F08 等待、唤醒与恢复 | watch 外部事件唤醒、到期事件一次性、未知执行核对 | 无长期运行可靠性结论 |
| F09 修章 | 本地受信凭据、旧规则约束、生效传播、历史版本 | E4 暂仅机制测试 |
| F10 上下文 | 目标/规则/岗位/任务/依赖/记忆、版本清单 | 只支持文本上下文 |
| F11 观察 | CLI 与静态进展页已实现，Dashboard 高保真原型已交付；实际数据服务与前端未实现 | 尚无连接组织状态的网页看板 |
| F12 有限资源 | 调用占用、每次超时、token 回执、金额未知 | 金额硬上限不支持真实 Codex |

## 代码与运行

原实现基线 `24845e3eb3709645356aa835564c67ed60b628bb`；本次交接分支 `feat/ai-union-runtime-console-handoff` 整合了最新 `main` 的 `e11c389` 及全部本地成果，用于 PR 评审。未合并到 main 或部署。仓库可克隆到任意目录，无需复用 `/workspace/Union`。

- Python 3.11+ 标准库，无运行时第三方依赖。
- `ai_union/engine.py`：SQLite 串行事务、业务校验、上下文、资产、预算与恢复。
- `ai_union/executor.py`：Codex CLI 与显式 fixture；`protocol.py`：操作协议和结构化输出。
- `ai_union/runner.py`：有限派发及事件等待，`cli.py`：观察与本地董事会入口。
- `evaluation.py`：独立于组织输出的客观证据判定；不能把模拟评成真实通过。

验证命令：`python3 -m unittest discover -v`。已运行 25 项，全部通过。完整命令与结果见 `evidence/001-org-bootstrap/`；离线 wheel 和隔离安装也已运行。

现存模拟组织 `.union/validated-final`，已完成 6 次 fixture 执行、3 项工作、3 份文本成果，当前 wait；复查时间 2099 年是 fixture 明示的测试值。查看：

```bash
cd /workspace/Union
python3 -m ai_union --root .union/validated-final status
python3 -m ai_union --root .union/validated-final context --work-id work-followup
```

这些目录被 Git 忽略。新任务若没有该本地组织，按 README 从新 root 重建模拟场景，不假设快照保留进程、凭据或连接。每个云任务已隔离，继续使用当前 checkout，不另建 worktree。

## 未完成与恢复条件

1. **下一工程优先事项：实现 P0 组织操作工作台。** 先读 `docs/PRD.md`、`docs/product-design.md`、`docs/software-reuse.md` 与原型，再按 `specs/004-organization-console/` 实现受信会话、命令接口和运行控制，同时按 `specs/003-runtime-dashboard/` 实现一致观察服务。当前运行器没有跨进程暂停协议，需要新增持久暂停意图及在途处理，不能以网页变量代替。两项 review 已写入 D01、D07、A03、A09、A10，但运行时／观察层代码问题尚未修复。此工作无需真实模型调用或 Cloudflare 发布条件。有限真实 Codex 试跑仍为独立的真实能力验证事项：当前已发现 CLI `0.159.0-alpha.3` 和 ChatGPT 登录，无需先索取 API token。本轮通过异步问题提供了“不调用 / 1 次 180 秒烟雾 / 最多 8 次每次 180 秒”选项，尚未收到选择。交接原文要求不在未知计费条件下默认展开长期自主运行；费用未知，因此没有擅自启动模型。用户确定范围后修改资源文件或采用现有 8 次上限，在独立 `.union/real` 目录按 README 运行，保留全部失败和成功。
2. 真实 CLI 的结构化输出、工具限制、token 统计、登录可用范围仍需实际回执验证；接口替身通过不能替代它。官方 developers.openai.com 文档请求返回 403，已核对官方 GitHub 文档入口、配置 schema、实际 CLI help/features；没有绕过网络或关闭 TLS。
3. 若调用失败：先读本地私有日志；不要打印凭据，不猜测缺失认证，不重复申请 token。用量/额度保留。未知执行经核对后使用 reconcile，不直接重派。
4. E1/E2 的真实评测必须满足至少两成员、真实依赖、可读取成果及依据证据的后续动作。8 次不足时如实报告并由董事会调整资源；不能重置数据库清除失败。E3/E4 当前验证的是受控机制，尚无真实 Agent 场景结论。
5. 真实对外交付、账号、渠道、外部反馈和后续经营都未接入；属于下轮范围。正文与执行字段须采用人共同确认，不支持任意规则编程或自然语言授权推断。

尚不支持：远程会话自动重连、远程取消确认、成果回执自动恢复、多用户身份服务、调用金额硬上限、任意工具、发布渠道、所有媒体。单应用本地原型不具备生产部署或长期经营的验收证据。

Spec Kit 未安装；核对了官方当前安装方案，采用等价 Markdown Spec/Plan/Tasks，原因记录在 plan。开发规范与组织运行章程分离。

## 新增：开发进展展示网站

用户随后明确请求通过 Sites/Cloudflare 建立网站，展示进展、简单演示和系统架构。已在 `site/` 实现无需构建的中文静态页面，支持模拟流程播放、逐步跳转、成果阅读下载及六架构模块说明。网站只展示公开验证快照，不启动 Agent。

37 项真实 Chromium 浏览器检查通过（含手机、键盘、交互与 Cloudflare CSP），见 `evidence/site/`。发布条件尚缺：Sites/Cloudflare 工具接口未提供；当前环境没有 Cloudflare 凭据且 API 被网络策略拒绝。已保存 token、账户 ID 和 API/预览域名要求的环境草稿，用户填值并审核保存、发布云环境配置后应重试。当前未部署到 Cloudflare，无公开网址。

部署脚本 `scripts/deploy_site.sh` 先创建新 Pages 项目，避免覆盖未知既有网站。具体命令、控制台 Direct Upload 替代方式及验证记录见 `docs/site.md`。

用户随后要求改为单 HTML。已交付根目录 `ai-union-progress.html`，63,113 字节，包含所有样式、脚本、图标、演示数据和成果。生成命令 `python3 scripts/build_single_html.py`，源文件保留在 `site/`。43 项断网 Chromium 文档检查通过，实际下载及全部交互没有网络请求；直接 file 导航仍未验证。原 25 项机制测试通过，真实调用仍为 0。

## 新增：必需运行 Dashboard

用户明确要求 Dashboard 为项目必要组件并加入开发需求。已建立 `specs/003-runtime-dashboard/spec.md`、`plan.md`、`tasks.md`，同步 F11 与 README，优先级为 P0，纳入首版产品验收。目前运行 Dashboard 数据服务和实际前端没有实现或验收证据。

此段记录当时的观察模块范围；最新整体范围已按 004 扩展为操作工作台。观察模块为单组织、单 HTML 前端与本地只读数据服务，展示组织状态、成员岗位、任务依赖、成果、事件决定、执行和资源，5 秒自动刷新及手动刷新，明确连接、过期与模拟来源。读取不得触发执行或改变状态；单次快照须一致，成果须校验，凭据与私有日志不进入网页。静态展示页与真实能力验证分别保留原有结论。

## 新增：统一产品与设计基线

用户指出前序缺少 PRD、产品设计和高保真。已补齐 `docs/PRD.md`（产品定位、角色、流程、范围、阶段、验收）、`docs/product-design.md`（现已更新为七视图、操作表单、状态、导航、详情、移动端与刷新设计）及根目录 `ai-union-dashboard-prototype.html`。

高保真原型是单 HTML，源文件 `design/dashboard/`，生成命令 `python3 scripts/build_dashboard_prototype.py`。使用白名单公开 fixture 和明确标识的设计情景；支持导航、筛选、详情关联、下载、正常执行／等待／活性不足／核对／断开／空组织／额度／拒绝／成果不可用情景，以及同版本事件和旧模拟响应演示。它不访问数据库、模型或网络，不代表实际看板交付。48 项断网 Chromium 设计检查与原 25 项机制回归通过，记录和截图在 `evidence/design/`。

review 结论及需求处理见 `specs/003-runtime-dashboard/review.md`。后续开发须按产品与设计基线展开，产品变化同步 PRD、Spec 与设计；原型浏览器检查不替代实际数据服务 A01–A10 验收。

## 最新：组织操作工作台与业务软件复用

用户明确要求前端可操作，并提出 ERP、CRM、MES 等软件的复用与 AI 适配问题。PRD／产品设计已更新 v0.2，新增 `specs/004-organization-console/` 和 `docs/software-reuse.md`。前端覆盖创建、有限运行、暂停、事件、资源、修章、核对与回执。复用业务系统作为客户、订单、财务等事实来源；ai-union 负责成员、任职、章程、组织决定、授权、上下文及执行恢复。软件名称均为候选示例，没有采购、安装或接入记录。

单 HTML 原型 `ai-union-dashboard-prototype.html` 仍沿用文件名，现已包含操作工作台七视图。操作源文件 `design/dashboard/console.js`，新检查脚本 `scripts/check_console_design.cjs`；48 项观察交互、32 项操作交互及 25 项机制回归通过。核心演示包含六步有限 fixture、暂停已请求到生效、预览取消、观察者情景、版本冲突、断开、修章撤权及核对不退额度；全程无网络请求、无真实模型调用。截图和详细记录见 `evidence/design/`。

原型仅保存浏览器内临时状态，不是生产授权、持久审计或真实暂停实现。章程表单演示正文和工具字段；完整字段、实际回执查询、读写服务及 A01–A10／C01–C09 尚待开发。内容纳入本次交接分支；合并、真实服务验收与部署分别执行，不由此交接推定完成。

## 2026-10-12 仓库交接整理

新增 `docs/DEVELOPMENT.md`，记录从新克隆开始的工具安装、测试、fixture 重建、HTML 生成、浏览器检查和可直接交接的下一任务。README、AGENTS、`docs/ai-union/STATUS.md` 已统一指向当前 P0；旧开发文档保留为历史依据。远端 main 的旧平台基线、任务编号、离线实验及 Node CI 全部保留。

本次验证记录在 `evidence/handoff-2026-10-12/`，原始机制记录与源文件摘要保留。当前已实现授权机制仍需另一工程角色在生产采用前复核；PR 交接不替代复核。真实模型调用仍为 0。网页服务、暂停协议、真实组织和业务集成的未完成项继续按 003／004 执行。
