# UNION / ai-union

**UNION——一家开箱即用的 AI 公司。**

你给目标和预算，它自行组织团队、开展业务、交付成果，并向你汇报经营情况。开发主分支为 **`dev`**。

## ai-union 与 ai-union-platform 的作用和边界

以下定义经用户于 2026-10-20 确认，描述产品方向；具体能力的实现与验收状态见[当前状态](docs/ai-union/STATUS.md)。

**ai-union** 是以 AI 为核心、围绕共同目标自主组织和持续行动的协作集体，能够自行调整成员、岗位、流程与能力，并对成果负责。

**ai-union-platform** 为这些组织提供创建、托管、观察、接入等公共服务，提供运行条件，不预设组织的业务、结构和经营方式。

**边界是：平台提供服务，组织依据章程、授权与资源自主决定如何发展和完成目标；平台自身也可以由一个 ai-union 建设和运营。**

本文及历史文档中的“UNION 平台”指 ai-union-platform。完整产品依据见[定义与项目边界](docs/ai-union/DESIGN.md#2026-10-20已确认的作用和边界)。

## 当前实现与运行入口

**2026-10-18：真实筹建已通过，执行循环继续验收。** OpenRouter免费模型成立2人团队、完成3份规划成果并采用后续依赖工作；真实空闲不调用模型，新事件能在同一作业触发派发。修复上下文及工具工作流，142项后端检查通过。累计48次到限后停止；后续工作受阻、事件后的模型提议仍不合规，不能宣称稳定自治或三章经营通过。见 [014实际记录](evidence/014-real-loop/README.md)。

**2026-10-18：移除旧单 HTML 演示，开发统一使用 `dev`。** 已删除独立演示/报告、旧原型源码和专用生成/部署/验收工具，正式入口是 React 工作台。历史证据保留；[退役说明](docs/site.md)。OpenRouter 免费模型普通对话已通过独立实测，API 报告费用为 0；这不代表组织筹建、工具协作或三章业务已验收。见 [测试记录](evidence/011-openrouter-smoke/README.md)。

**2026-10-17：组织筹建与成员 Harness。** API 有限运行现在使用 Deep Agents / LangGraph，支持分批保存与修正筹建草案、事务成立、成员虚拟文件工具循环及检查点恢复。每次模型请求独立计入额度；网页连接测试使用两次调用验证工具往返，总览展示筹建进度。`npm start` 自动准备项目 Python 环境和固定 SDK 依赖。架构与使用见 [组织 Harness](docs/ORGANIZATION_HARNESS.md)，范围见 [010](specs/010-organization-harness/spec.md)。真实供应商与业务质量仍待独立验收。

**2026-10-17：修正 API 与初始化协议。** API 使用普通对话和按职责提供的组织工具，不再要求每一步返回整包 Schema。连接测试接收普通文本，工作正文直接保存；初始化由模型安排成员与任务，程序维护内部标识、任职与版本。旧 API 连接可继续读取，网页已移除 JSON 输出模式。实现与验证范围见 [009](specs/009-agent-conversation/spec.md)；真实供应商仍须单独验收。

**2026-10-16：整体工作台更新。** 通用公司与已有组织共用新版首页、启动引导和八页导航。左侧 **模型与 API** 可直接新增连接，填写 API 根地址、API Key 和模型；支持编辑公开配置、切换/取消默认连接、连接测试及回执。入口是 `/models`，无需先创建小说公司。小说经营面板保留为可选业务试验。使用与验收见 [007 工作台更新](specs/007-workspace-redesign/spec.md) 和 [前端工程](docs/FRONTEND.md)。

**小说公司首版链路已实现（2026-10-16）**：网页创建公司、配置并测试模型 API；一次启动连续完成计划、创作、mock 投稿、模拟订阅结算与经营复盘。三周期后停止，保存负面反馈到后续交付的证据。工程与本地 HTTP 模拟验收已通过；真实供应商运行与三章人工审读仍待验收。

先看可重放效果：安装依赖后运行 `npm start -- --root .union/novel-demo --novel-demo --open`。这是明确标识的脚本演示，不调用模型。真实模型配置、预算含义和恢复步骤见 [小说公司体验指南](docs/NOVEL_COMPANY.md)，验证见 [006 evidence](evidence/006-novel-company/README.md)。

当前首版：一家持续创作同一本小说、交付三章并完成三轮模拟经营的 AI 公司。成员执行循环复用现有 Agent，开发重点是组织层运行。

当前实现：从“组织启动与首次协作”扩展到小说公司经营试验的本地运行时。Python 3.11+、SQLite、CLI；API 成员执行依赖固定版本 Deep Agents / LangGraph。支持目标、版本化章程、临时启动授权、筹建草案、组织决定、岗位与任职、依赖工作、文本成果、任务会话恢复、交接、等待唤醒、重启核对和资源记录。

这是组织层原型。经营策略和岗位由执行器输出形成，代码不预置内容工作流。已有本地 mock 小说平台及试验账本；尚无真实模型闭环验收、真实对外发布或市场反馈证据，也没有真实支付或投资募集。

**P0 本地组织工作台已接入实际服务，fixture 验收通过。** 浏览器可创建、有限运行、暂停派发、提交事件、调整资源、修章和核对执行；Dashboard 读取实际持久记录。正式前端已迁移到 React + TypeScript + Vite，七页路由、服务端数据管理、操作表单和回执分别维护。原前端迁移验证见 [005](evidence/005-frontend-engineering/README.md)，当前组织 Harness 验证见 [010](evidence/010-organization-harness/README.md)。范围见 [004](specs/004-organization-console/spec.md) 与 [003](specs/003-runtime-dashboard/spec.md)，证据见 [工作台验收](evidence/004-organization-console/README.md)。

实现、review、验证与复盘保存在 `docs/` 和 `evidence/`；单 HTML 报告已退役，历史提交和原验收记录保留。

从仓库根目录首次安装，然后一条命令构建并启动（Node 24.19.0、Python 3.11+）：

```sh
npm ci --ignore-scripts
npm start -- --root .union/console --port 8766 --open
```

浏览器从本机一次性链接建立发起人会话，默认仅配置 fixture。正式源码在 [web/console](web/console)，Vite 构建由 Python 同源提供；[工程与架构](docs/FRONTEND.md)、[工作台使用说明](docs/CONSOLE.md)包含开发、操作和恢复流程。独立单 HTML 演示已删除，后续只维护正式 React 工程。

**真实模型 API 后端已接入。** 可配置 Chat Completions API 地址、模型、私有密钥、输出上限与超时，绑定组织默认连接，通过普通对话及组织工具执行。无需 Codex CLI；配置本身不调用模型。React 工作台已整合；API 配置、默认绑定与连接测试已接入网页；CLI／HTTP 入口继续可用。运行步骤与当前契约见 [API_MODELS.md](docs/API_MODELS.md)，原实现范围见 [005](specs/005-real-model-api/spec.md)。组织协作验收来自本地 HTTP 替身；独立 OpenRouter 普通对话实测见 [011](evidence/011-openrouter-smoke/README.md)，尚不代表组织能力通过。

产品与设计基线：[统一 PRD v0.6](docs/PRD.md)、[产品设计说明](docs/product-design.md)、[软件复用与 AI 适配](docs/software-reuse.md)。原型的历史设计验收和截图保存在 `evidence/design/`，后续页面和交互以正式 React 工程为准。

业务事实与交易能力优先复用 ERP／CRM／文件／发布等已有系统；ai-union 负责 AI 成员、授权、组织决定、责任、执行与恢复。当前未接入这些业务系统，也不为抽象的 AI 企业预先重建 ERP、CRM 或 MES。

开发集成入口为 `dev` 分支，包含运行时、真实 API 后端和 React 工作台；[集成验证](evidence/dev-integration/README.md)记录本次合并范围。

## 从这里接手

1. [当前状态](docs/ai-union/STATUS.md)与[工程交接](HANDOFF.md)：已实现范围、明确缺口和下一步。
2. [新环境开发与验证](docs/DEVELOPMENT.md)：从新克隆仓库重建模拟场景、运行工程检查、构建正式工作台，不依赖前一个环境。
3. [PRD](docs/PRD.md)、[产品设计](docs/product-design.md)与[005 前端工程待办](specs/005-frontend-engineering/tasks.md)：当前 P0 产品范围及验收。
4. [治理设计依据](docs/ai-union/DESIGN.md)、[最初开发交接](docs/ai-union/DEVELOPMENT.md)与[ADR-0002](docs/decisions/0002-ai-union-direction.md)：产品与路线背景；当前进度以 STATUS／HANDOFF 为准。

## 两条项目线


| 项目 | 目标与当前安排 |
| --- | --- |
| **ai-union** | 构建围绕共同目标协作的 AI 组织。当前优先实现“组织启动与首次协作”，验证目标、组织形成、行动、成果及后续决定的闭环 |
| **UNION 平台** | 为组织提供创建、托管、观察、接入等服务。保留独立规划，按 ai-union 实际需要评估已有工程资产 |

两个项目在产品与计划上拆分，本次仍在同一仓库记录。平台未来可由 ai-union 运作并设置技术委员会，不给每个组织预装相同的委员会或岗位。

## 已确认的运行原则


- 董事会保留最终控制权；治理边界属于章程，董事会可按现行程序修订。经营层在生效授权内自主运行。
- 岗位决定职责、权限与上下文；成员可以兼岗，正式知识和成果由组织或工作持有，能够交接。
- human-free 是描述性特征，不是零人工的资格或验收门槛。
- 首阶段以商业组织为对象。长期追求覆盖各类费用并自维持；融资与经营收入分开记录。
- 当前首版采用真实模型、mock 小说平台与结算，验证反馈后实际行动；真实发布与市场反馈为后续里程碑，盈利不作为首版通过条件。

开发规范与组织运行章程分别管理。上述产品机制不替代真实账号、渠道、工具和预算的配置与授权。

## 运行与查看

从仓库根目录运行，使用已安装依赖的项目 Python（Linux/macOS 为 `.venv/bin/python`，Windows 为 `.venv\Scripts\python.exe`；激活虚拟环境后可直接使用下例的 `python3`）。下面只执行确定性模拟，不调用模型：

```bash
python3 -m unittest discover -v
python3 -m ai_union --root .union/demo init \
  --name "ai-union 本地模拟" --board-name "local developer (test adoption)" \
  --charter examples/charter.local.json --resources examples/resources.local.json
python3 -m ai_union --root .union/demo run \
  --executor fixture --fixture examples/fixture.json --max-steps 8
python3 -m ai_union --root .union/demo status
python3 -m ai_union --root .union/demo evaluate --output .union/demo/evaluation.json
```

最后一条在模拟场景中退出码为 **3**，报告 `status=simulated`、`mechanism_scenario_passed=true`、`real_agent_verified=false`。这不是测试失败，而是拒绝把模拟当作真实能力验收。`run` 正常结束或等待为 0；受阻为 2。已有组织不应再次 init，后续直接 run/status。

`status` 包含目标、成员、岗位、任职、工作、成果、下一步、等待时间和阻塞原因。`context --work-id WORK_ID` 查看工作包和版本清单；`events`、`decisions`、`usage` 查看实际记录。资产在组织根目录的 `assets/`，文件名按 SHA-256 内容寻址；原名称、版本与任务来源存于数据库。

## 真实 Codex 试跑

执行器适配官方 Codex CLI `exec`。当前机器检测到版本 `0.159.0-alpha.3` 和 ChatGPT 登录；此事实不代表已实际调用。建议同一受测版本；其他版本先核对 `exec --help` 与 feature flags。

先配置可用的 Codex 登录和有限调用额度。不要把 token 写入仓库或命令行参数；云环境沿用注入认证、代理和 CA。不要复制模拟数据库进行真实评测，新建独立组织：

```bash
codex --version
codex login status
python3 -m ai_union --root .union/real init \
  --name "ai-union 首轮试验" --board-name "发起人（本地测试采用）" \
  --charter examples/charter.local.json --resources examples/resources.local.json
python3 -m ai_union --root .union/real run \
  --executor codex --max-steps 8 --allow-unknown-cost
python3 -m ai_union --root .union/real evaluate --output .union/real/evaluation.json
```

只有明确接受有限调用下费用未知后才执行真实 run。默认资源为累计最多 8 次调用、每次最多 180 秒；实际 token 由 CLI 回执记录，金额标为 unknown。CLI 不提供已核实的生成 token 或金额硬上限；设置金额硬上限时此适配器拒绝调用。模型可在网页“组织设置 → 模型设置”保存，也可用 `--model` 指定；省略参数使用组织默认，组织未设置时由 CLI 选择默认，具体模型信息以私有执行记录为准。不能保证 8 次调用必然完成真实评测；失败不重置额度或抹除记录。

运行时不开放真实发布工具。Codex 在独立目录、只读沙箱中运行，关闭用户配置、shell、多 Agent 工具、apps、plugins、hooks 和 web search。上下文与结构化响应通过 stdin/文件传递，产物由宿主校验后保存。工具限制的配置与回执检测已通过接口替身测试；真实版本的行为仍须试跑核验。操作系统访问控制是本地信任边界，适配器不是恶意程序的隔离容器。

`executions/RUN_ID/` 保留工作包、JSON schema、最终响应和私有 CLI 日志。若真实 CLI 返回失败，先在本机检查日志并去除秘密后再共享；不要上传整个组织根目录。

## 等待、事件与恢复

`run` 无新事件、无可执行工作时立即返回等待；下次 run 会检查持久化复查时间。要维持等待进程并响应到期或外部事件：

```bash
python3 -m ai_union --root .union/real watch \
  --executor codex --max-steps 8 --max-seconds 600 --allow-unknown-cost
```

空闲轮询不调用模型，默认每秒检查一次。`max-seconds` 在调用之间检查；在途调用仍受单次 180 秒超时约束。进程、登录和连接不会随云环境快照保留，未来任务需要按说明重新启动。多个派发器互斥；董事会变更也使用同一进程锁。

用 `event --id RECEIPT_ID --kind external_feedback --data feedback.json` 导入反馈。数据必须包含 `source` 和显式布尔 `simulated`，并保留可核验来源；输入标记本身不证明市场反馈。重复事件 ID 不重复推进，不同内容使用同一 ID 会被拒绝。

重启把遗留 running 执行转为 unknown/needs_review，阻止盲目重派。Codex 的本地终止不证明远程取消。先核对原 `executions/RUN_ID/` 和服务执行记录，再选择受信入口：

```bash
python3 -m ai_union --root .union/real reconcile \
  --board-key-file .union/real/board.key --run-id RUN_ID \
  --resolution confirmed_not_executed --reason "填写核对来源与结论"
```

仅确实未执行时用 `confirmed_not_executed`，否则用 `abandon`；已有成果暂需核对后作为事件导入，尚不支持自动重连/恢复远程会话。调用占用不会退款。

## 董事会入口

init 生成权限为 0600 的 `board.key`，数据库仅保存加盐摘要。Agent 上下文不含此凭据，填 `actor=board` 不授予权限。保管此文件，丢失无法自动恢复；有操作系统/数据库访问的人仍属于受信本地管理员。采用示例章程时，应明确它只授权本地测试，不等于真实经营或外部账号授权。

```bash
python3 -m ai_union --root .union/real amend \
  --board-key-file .union/real/board.key --charter revised-charter.json \
  --reason "填写修章决定与依据"
python3 -m ai_union --root .union/real resources \
  --board-key-file .union/real/board.key --config revised-resources.json \
  --reason "填写追加投入或风险调整依据"
```

章程仅支持 `text`、`allowed_operations`、`allowed_tools`、`reserved_matters`、`board_can_amend`。正文与执行字段由采用人共同确认，不解析任意自然语言授权；不支持的字段拒绝。修订遵守旧章程的修章入口权限，新规则不能授权自身采用。撤回工具权限使未完成工作暂停，在途工作待核对；历史决定和成果保留旧依据。内部决策岗位由 `set_policy` 指定，成员可兼岗；多席位以独立岗位表示。

工程规格见 [specs/001-org-bootstrap](specs/001-org-bootstrap/)，当前结果及下一步见 [HANDOFF.md](HANDOFF.md)。

## 正式前端与历史记录

日常开发和体验使用 [React 工作台](docs/FRONTEND.md)。独立进展页、设计原型、旧实际单页和 HTML 完成报告已按用户要求删除，其源码、生成/部署/验收工具同时退役。历史截图、验证记录和 Git 历史保留，见 [说明](docs/site.md)。

## 检查旧平台工程资产


以下命令保留旧平台计划与离线实验检查，并加入 React 前端类型、测试及构建检查；组织机制和实际浏览器验收另见上面的开发说明。使用 `.nvmrc` 指定的 Node.js 24.19.0：

```sh
npm ci
npm run check
```

旧平台实验没有第三方依赖，不需要账号或 API Key，不产生真实支出。`npm test` 使用临时数据库和子进程，退出时清理。Node 可能输出 SQLite 实验性 API 提示。当前测试执行 TypeScript，但尚未配置完整静态类型检查。

`spikes/action-safety` 验证动作授权、整数预算预约、并发争用、幂等参数绑定及模拟外部动作的查询恢复。它可以按需要复用，不代替组织能力、PostgreSQL/Temporal、身份认证、沙箱或生产支付验收。资金与权限实现仍需另一工程角色复核后才能采用。

## 旧平台材料

- [原 M0 状态与任务映射](docs/kickoff/STATUS.md)
- [原范围草案](docs/kickoff/SCOPE.md) · [离线验证记录](docs/kickoff/VALIDATION.md)
- [ADR-0001：离线动作实验](docs/decisions/0001-offline-action-spike.md)
- [82 项原任务目录](docs/kickoff/tasks.json) · [首批 GitHub Issues 映射](docs/kickoff/github-issues.json)
- [原项目方案](docs/baseline/UNION项目方案.md) · [工程任务](docs/baseline/ISSUES.md)
- [运营方案](docs/baseline/OPERATIONS_PLAN.md) · [规划与运营任务](docs/baseline/OPERATIONS_ISSUES.md)
- [原启动路书](docs/baseline/UNION_项目启动路书_v0.1.md)

五份 UNION-B1 输入快照、PLAN/OPS/ENG 编号和原验证证据保留。原 M0 门槛继续用于原平台范围，不作为新组织原型的统一前置条件；本次不据此关闭旧任务或宣称其验收完成。

## 许可与公开范围

仓库保持现有 public 可见性。未改变开源许可证或贡献权利安排，未附加未经决定的开源授权。请勿提交密钥、客户资料或真实资金凭据。
