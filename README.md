# UNION / ai-union

**用户给出目标，ai-union 自行形成组织、开展行动，并根据结果持续调整。**

首版目标：一个持续经营线上内容品牌的 AI 内容工作室。成员执行循环复用现有 Agent，开发重点是组织层运行。

当前实现：ai-union 首个迭代“组织启动与首次协作”的本地运行时。Python 3.11+、SQLite、CLI；无运行时第三方依赖。支持目标、版本化章程、临时启动授权、组织决定、岗位与任职、依赖工作、文本成果、后续行动、交接、等待唤醒、重启核对和资源记录。

这是组织层原型。经营策略和岗位由执行器输出形成，代码不预置内容工作流。尚无真实模型闭环验收、对外发布或市场反馈证据，也没有经营平台、支付或投资募集。

**P0 本地组织工作台已接入实际服务，fixture 验收通过。** 浏览器可创建、有限运行、暂停派发、提交事件、调整资源、修章和核对执行；Dashboard 读取实际持久记录。53 项 Python 测试、53 项实际服务浏览器检查通过，真实模型调用仍为 0。范围见 [004](specs/004-organization-console/spec.md) 与 [003](specs/003-runtime-dashboard/spec.md)，证据见 [工作台验收](evidence/004-organization-console/README.md)。

本轮实现、review、验证与复盘见 [单页完成报告](ai-union-completion-report.html)，可离线打开。2026-10-13 的最终复验记录单独保存，历史结果保留。

从仓库根目录启动（Windows 用 `python`，Linux 可用 `python3`）：

```sh
python -m ai_union.server --root .union/console --port 8766 --open
```

浏览器从本机一次性链接建立发起人会话，默认仅配置 fixture。前端为 [ai-union-console.html](ai-union-console.html)，需要同源服务；操作、会话和恢复说明见 [工作台使用说明](docs/CONSOLE.md)。

**真实模型 API 后端已接入。** 可配置 OpenAI-compatible API 根地址、模型、私有密钥、输出模式、输出上限与超时，绑定组织默认连接，通过 CLI 或受信 HTTP 命令测试连接及执行。无需 Codex CLI；配置本身不调用模型。前端页面由独立开发者接入，本次保留原页面。运行步骤与完整前端契约见 [API_MODELS.md](docs/API_MODELS.md)，实现范围见 [005](specs/005-real-model-api/spec.md)。当前证据来自本地 HTTP 替身，真实供应商调用仍为 0。

产品与设计基线：[统一 PRD v0.2](docs/PRD.md)、[产品设计说明](docs/product-design.md)、[操作工作台单 HTML 原型](ai-union-dashboard-prototype.html)、[软件复用与 AI 适配](docs/software-reuse.md)。原型支持七视图、操作表单与预览、回执、有限 fixture 步骤、详情及异常情景。48 项观察交互与 32 项操作交互检查通过；仅模拟浏览器内状态，未连接真实组织服务，模型调用为 0。

业务事实与交易能力优先复用 ERP／CRM／文件／发布等已有系统；ai-union 负责 AI 成员、授权、组织决定、责任、执行与恢复。当前未接入这些业务系统，也不为抽象的 AI 企业预先重建 ERP、CRM 或 MES。

## 从这里接手

1. [当前状态](docs/ai-union/STATUS.md)与[工程交接](HANDOFF.md)：已实现范围、明确缺口和下一步。
2. [新环境开发与验证](docs/DEVELOPMENT.md)：从新克隆仓库重建模拟场景、运行测试和生成单 HTML，不依赖前一个环境。
3. [PRD](docs/PRD.md)、[产品设计](docs/product-design.md)与[004 操作工作台待办](specs/004-organization-console/tasks.md)：当前 P0 产品范围及验收。
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
- 首版需有真实对外交付、可核验外部反馈和下一轮实际行动，收入和盈利先作为观察指标。

开发规范与组织运行章程分别管理。上述产品机制不替代真实账号、渠道、工具和预算的配置与授权。

## 运行与查看

从仓库根目录运行；无需安装 Python 包。下面只执行确定性模拟，不调用模型：

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

## 开发进展网站

单文件交付：[ai-union-progress.html](ai-union-progress.html)。内置样式、脚本、验证快照和三份模拟成果，无需其他文件或网络资源。支持演示播放、架构切换、成果及验证摘要下载。

`site/index.html` 提供中文开发进展、可逐步播放的模拟协作、成果查看及交互架构图。它展示验证快照，浏览器操作不启动模型、不修改组织状态。

`site/` 保留可编辑源文件。更新公开数据后，运行 `python3 scripts/build_single_html.py` 重新生成单文件。Cloudflare Pages 发布准备与当前凭据/网络阻塞见 [docs/site.md](docs/site.md)；实际浏览器验证与截图见 [evidence/site](evidence/site/)。

## 检查旧平台工程资产


以下命令检查旧平台计划与离线实验，**尚不是 ai-union 的启动或验收命令**。使用 `.nvmrc` 指定的 Node.js 24.19.0：

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
