# ai-union 当前状态

## 2026-10-17：组织筹建与成员 Harness

010 已实现 Deep Agents / LangGraph API 执行、分批筹建草案、事务成立、虚拟文件工具循环和任务检查点恢复。模型请求逐次预约和结算，输入和交付仍用普通语言。网页显示筹建进度，连接测试实际验证工具往返的两次调用；`npm start` 自动准备固定依赖。选型、边界及恢复见 [组织 Harness](../ORGANIZATION_HARNESS.md)。

最终本地验证：131 项 Python（其中 21 项 Harness 行为）、16 项前端、71 项工作台浏览器、16 项小说浏览器及 5 项启动检查通过，`npm run check` 与依赖校验通过。独立复核发现的历史 Key 过滤、已取得 token 保留及修正结算出口问题已关闭。证据见 [010](../../evidence/010-organization-harness/README.md)。真实供应商调用仍为 0，模型业务能力、正文质量与真实经营尚未验收。

## 2026-10-17：API 普通对话与组织工具

用户指出逐步强制 Schema 导致调用和组织初始化不可用。009 改为普通探测、正文交付及按需组织工具：宿主生成初始化标识和任职，绑定原始工作包的版本依据；不再发送 `response_format`。完整组织提议在本次剩余额度内可获一次带原因的修正，每次独立记录调用和用量。HTTP 故障、拒绝、截断和 unknown 不自动重发。实现、测试和独立复核以 [009](../../specs/009-agent-conversation/spec.md) 及其新证据为准。真实模型调用仍为 0，不能宣称现场 API 或模型协作已验收。

本地最终验证：110 项 Python、16 项前端、60 项工作台浏览器、16 项小说浏览器及 5 项启动检查通过，`npm run check` 通过；独立复核发现的凭据解码检查和参数语法错误恢复均已修正并复验。见 [009 验证记录](../../evidence/009-agent-conversation/README.md)。

## 2026-10-16：运行故障反馈

用户反馈首版无法正常运行。最新 `dev` / `54e35b5` 的本机干净启动可通过；用户具体故障尚无现场记录，运行可用性不能据自动化通过认定。已复现“错误原因被页面隐藏”的缺陷并补充公开诊断和恢复提示，见 [008](../../specs/008-runtime-failures/spec.md)。真实供应商试跑及用户现场验收仍待完成。

## 2026-10-16 当前增量：整体工作台与独立 API 入口

根据用户对“仅做小说特化项、API 入口不清楚”的纠正，已按 [007](../../specs/007-workspace-redesign/spec.md) 更新整个 React 工作台。通用组织和已有数据均使用新首页、启动准备、八页导航与移动端；左侧“模型与 API”直接新增、编辑、切换/取消默认、测试连接与查看回执。无组织时也可发现入口和创建流程。

验证见 [007 evidence](../../evidence/007-workspace-redesign/README.md)：91 项 Python、16 项前端、50 项新工作台浏览器、61 项原工作台和 16 项小说流程通过；`npm run check` 通过。真实模型调用 0。权限和账本机制保持已有实现，新连接管理使用原受信命令。用户已授权将本轮验证完成的更新提交并推送到远端 `dev`；远端提交以 Git 记录为准。

## 2026-10-16 当前增量：小说公司首版

产品定位确认“UNION——一家开箱即用的 AI 公司”，持续开发主分支为 `dev`。已实现网页创建小说公司、API 配置/绑定/测试、三周期 mock 投稿与结算、负面反馈后任务与成果溯源、估算预算控制及缺失用量核对。见 [体验指南](../NOVEL_COMPANY.md)、[006 规格](../../specs/006-novel-company/spec.md)和[新验收证据](../../evidence/006-novel-company/README.md)。

当前工程测试通过；真实供应商调用仍为 0，不能宣称真实公司自治或小说质量已验收。脚本演示与本地 HTTP 替身均明确标识模拟。真实发布、实际市场验证和盈利后置。

以下保留此前迭代的历史记录；“连接管理表单待接入/尚无经营平台”等旧缺口由本节更新。


更新：2026-10-14（北京时间）。本地组织运行时及 P0 操作工作台已实现；实际服务的 fixture 最终复验通过。真实 Agent 与首版经营闭环未验收。实现、review、验证与复盘见 [单页完成报告](../../ai-union-completion-report.html)。

## 已完成与证据

运行时、真实 API 与 React 前端已整合到 `dev`，`main` 保持原状态；当前合并验证见 [dev 集成](../../evidence/dev-integration/README.md)。

正式工作台已按用户要求迁移到 React + TypeScript + Vite：七页路由、URL 筛选、查询/轮询、操作表单与回执分模块维护，Python 同源提供构建；首次 `npm ci` 后 `npm start -- --open` 一条命令启动。[005 证据](../../evidence/005-frontend-engineering/README.md)：Linux 下 55 项 Python、10 项前端、60 项实际浏览器、5 项启动检查通过，历史 Node 9 项继续通过。真实模型调用 0。

2026-10-13 后续后端升级：可配置真实 Chat Completions API、私有密钥、默认连接及一次连接测试；CLI 与 HTTP 共用执行链路，真实 API 已纳入评估。API 后端与 React 前端已合入 dev，连接管理表单仍待接入，可先使用 CLI／HTTP 配置。范围见 [005](../../specs/005-real-model-api/spec.md)，运行与前端接口见 [API_MODELS.md](../API_MODELS.md)，新证据见 [005 验证](../../evidence/005-real-model-api/README.md)。真实供应商调用仍为 0。

本日后续增量已补齐管理后台模型设置：组织默认、启动覆盖、持久回执与 CLI 一致性；53 项 Python／53 项浏览器检查通过，真实模型调用 0。[增量证据与复盘](../../evidence/004-organization-console/model-settings-2026-10-13/README.md)、[独立 review](../reviews/2026-10-13-model-settings.md)。下表保留原交付分项，005 接续其前端。

| 范围 | 已有内容 | 证据 |
| --- | --- | --- |
| 组织机制 | Python／SQLite／CLI：章程、组织形成、决定、任职、依赖工作、成果、后续行动、交接、修章、等待与核对 | [001 规格与任务](../../specs/001-org-bootstrap/tasks.md)、25 项机制／接口测试。 |
| 确定性协作 | 两成员、三工作、三文本成果、六次 fixture 调用，恢复后保持等待 | [历史公开记录](../../evidence/001-org-bootstrap/README.md)，真实模型调用 0。 |
| 产品与设计 | PRD v0.2、操作前端设计、软件复用分层、003／004 规格与验收 | [PRD](../PRD.md)、[产品设计](../product-design.md)、[软件复用](../software-reuse.md)。 |
| 高保真原型 | 单 HTML 七视图，创建、运行、暂停、事件、资源、修章、核对与回执的模拟交互 | [操作原型](../../ai-union-dashboard-prototype.html)、48 项观察与 32 项操作交互检查。 |
| 进展展示 | 单 HTML 进展、模拟演示、成果与架构 | [展示页](../../ai-union-progress.html)、43 项单文件浏览器检查。 |
| 开发交接 | 新环境复现、任务顺序、已知问题、源码、生成器和 CI | [开发说明](../DEVELOPMENT.md)、[完整交接](../../HANDOFF.md)。 |
| 实际工作台 | 本机会话、同源 HTTP、版本化幂等命令、运行作业、持久暂停、一致观察、单 HTML 七视图 | [004 验收](../../evidence/004-organization-console/README.md)：47 项 Python、45 项实际浏览器检查；[独立工程复核](../reviews/2026-10-12-console.md)。 |

## 尚未完成

- React 迁移已在 Linux／Python 3.12.14／Chromium／Node 24.19.0 验证；Windows 迁移实机与远端 CI 结果尚未取得，CI 已配置两平台工程检查及 Linux 浏览器验收。
- 创建过程跨文件存储失败时保持 unknown，需要宿主核对分配目录；不自动重建或重放。
- 真实 Codex 组织形成、协作与后续行动试跑，E1/E2 及真实执行器 E3/E4。
- 真实交付、可核验反馈、经营闭环、ERP／CRM 集成，以及 Cloudflare 发布。

没有真实收入、融资、盈利或自维持证据。本机曾发现的 Codex 登录不保证新环境可用。金额与授权逻辑生产采用前仍需独立工程复核。

## 下一步

005 前端工程已完成，使用与架构见 [FRONTEND.md](../FRONTEND.md)。

**下一优先事项：配置用户的 API 凭据，在有限调用范围与费用未知条件下，用独立组织完成真实 API 烟雾及 E1/E2；前端按新增契约接入。** [004 W2–W7](../../specs/004-organization-console/tasks.md)与 [003 观察模块](../../specs/003-runtime-dashboard/tasks.md)的本地 fixture 范围已完成。可立即按 [工作台说明](../CONSOLE.md)启动原工作台，或按 [API 说明](../API_MODELS.md)从 CLI 开展真实测试。

最初开发交接 [DEVELOPMENT.md](DEVELOPMENT.md)保留首轮目标；不再按其“尚未开始”的历史描述重做工程。后续状态以本文、HANDOFF 和迭代 Tasks 为准。

## 旧平台如何承接

远端 main 的五份基线、82 项任务、181 条依赖、离线动作实验与 Node 检查保留。PLAN／OPS／ENG 标识及历史状态未重编号或据此次工作关闭。[原 M0 状态](../kickoff/STATUS.md)描述旧平台范围，不是操作工作台的下一步清单。
