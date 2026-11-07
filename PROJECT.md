# 项目总览：目标、成熟度与路线

**当前需求基线：[Main Chapter V1](docs/UNION_CHARTER_v1.0.md)。** 采用依据与固定版本见[CHARTER_ADOPTION](docs/CHARTER_ADOPTION.md)；重写按[PRD v1.0](docs/PRD.md)、[总体架构/ADR](docs/ARCHITECTURE.md)、[053切片](specs/053-union-rewrite/tasks.md)及严格TDD推进。当前状态、负责人和验收只由下方主账生成视图说明；本次文档重建不升级历史成熟度。

## 1. 产品与目标

| 对象 | 产品定义 | 证据边界 |
| --- | --- | --- |
| AI-UNION / AU | 持续身份、目标、治理、资源与自主闭环的组织；单Agent及组合均合法 | 原试验组织的团队/规划成果只证明其历史场景 |
| ai-union | 开源、独立可用核心；自带基础认证/AU权限/审计 | 现有Python/React/模型/发布工程是复用资产，不宣称已符合全部V1 |
| AI-Union-Platform | 通过版本化核心公开契约提供可选服务的私有商业平台 | 商业账户、托管和付款不自动产生AU治理权 |
| ai-union-corp | 建设和运营上述产品的具体公司 | 仍按原公司真实筹建、工作区、交付、反馈和持续运行证据验收 |

正式开发门槛见[FORMAL_DEVELOPMENT](docs/FORMAL_DEVELOPMENT.md)。不报告按测试、代码或任务勾选数换算的产品完成率。旧两成员团队和小说公司是特定基准，不能成为所有AU的资格门槛；历史任务和真实阻塞继续保留。

## 2. 如何读成熟度

实现状态与验收强度分别记录。以下等级只表示已有证据覆盖范围，不是分数，也不做平均：

| 等级 | 含义 |
| --- | --- |
| V0 待验 | 设计或代码存在，但目标环境/场景未验 |
| V1 受控验证 | 自动测试、fixture、供应商或容器替身、局部本地验证通过 |
| V2 真实局部 | 真实模型或真实依赖下有部分成功，仍有关键未通过场景 |
| V3 真实闭环 | 指定真实任务从目标到交付、反馈、后续行动均通过；记录质量、成本及人工介入 |
| V4 持续运行 | 在约定观察窗口内重复通过，并验证重启恢复、故障处置、资源控制和维护责任 |

到 V3/V4 必须写明任务、环境、观察窗口和证据；某个模块达标不自动使公司或整个平台达标。

## 3. 模块建设状态

<!-- management:modules:start -->
| 模块 | 已实现 | 验收范围 | 下一缺口 | 证据 |
| --- | --- | --- | --- | --- |
| 组织治理与状态 / ai-union | V1稳定核心主体、本地治理、旧规则修章、可信接班/超时退出、有限授权与原Work责任交接；legacy版本化章程/决定等机制保留 | S01/S05受控工程及实际浏览器已验证；legacy真实筹建只证明原场景，V1真实业务治理未验 | 真实模型工作中的治理修订、撤权和责任交接未验；计划指向S06/U-070，但主账acceptance尚需显式补入。企业身份集成仍未验，不作近期单AU成果前置。 | [specs/001-org-bootstrap/spec.md](specs/001-org-bootstrap/spec.md)、[evidence/014-real-loop/README.md](evidence/014-real-loop/README.md)、[evidence/022-au-contract-implementation/README.md](evidence/022-au-contract-implementation/README.md)、[specs/053-union-rewrite/s05-contract.md](specs/053-union-rewrite/s05-contract.md)、[evidence/057-s05-governance/README.md](evidence/057-s05-governance/README.md) |
| 筹建与自我调整 / ai-union | 分批筹建草案、成立事务、组织更新工具 | V2：试验组织真实成立 | 当前公司成立；证明初始化之后仍能按目标扩展和调整 | [specs/010-organization-harness/spec.md](specs/010-organization-harness/spec.md)、[evidence/014-real-loop/README.md](evidence/014-real-loop/README.md) |
| 成员执行循环 / ai-union | Deep Agents / LangGraph、工具调用、任务检查点 | V2：规划文本交付 | 有效业务成果、长任务可靠性、失败后的正确后续动作 | [docs/ORGANIZATION_HARNESS.md](docs/ORGANIZATION_HARNESS.md)、[evidence/014-real-loop/README.md](evidence/014-real-loop/README.md) |
| 模型连接 / 公共接入 | AU独立多连接/导入导出、版本化目录、四协议、受限凭据、岗位/回退、上下文/媒体及四类费用 | V2历史局部；043新增范围V1受控验证与独立权限费用复核 | 真实供应商各协议工具往返、私有订阅最终账号至AU执行、真实自托管与整体031对标仍未验 | [docs/API_MODELS.md](docs/API_MODELS.md)、[evidence/011-openrouter-smoke/README.md](evidence/011-openrouter-smoke/README.md)、[evidence/027-gateway-management/README.md](evidence/027-gateway-management/README.md)、[evidence/043-usable-model-access/README.md](evidence/043-usable-model-access/README.md) |
| 开发工具 / 当前公司业务能力 | 可选 Docker 工作区、宿主/章程/岗位授权、持久命令回执及核对 | V1：SDK 与容器替身；独立权限复核通过默认关闭接入 | 真实容器与模型编程；网络、提交、部署仍需各自明确接口与授权 | [evidence/016-member-workspace/README.md](evidence/016-member-workspace/README.md) |
| 记忆与上下文 / ai-union | 组织记录、成果、交接信息、任务检查点及虚拟文件 | V1，真实运行暴露上下文问题 | 长任务上下文管理、知识检索与经验复用闭环；不能等同成熟学习系统 | [docs/ORGANIZATION_HARNESS.md](docs/ORGANIZATION_HARNESS.md)、[evidence/014-real-loop/README.md](evidence/014-real-loop/README.md) |
| 协作、唤醒与恢复 / ai-union | 工作依赖、交接、有限 watch、暂停、未知结果核对 | V2：真实空闲零调用、同一作业事件唤醒通过 | 诊断和生命周期已实现；模型有效事件处理、真实后续交付及持续运行待资源复验 | [evidence/014-real-loop/README.md](evidence/014-real-loop/README.md)、[evidence/020-organization-diagnostics/README.md](evidence/020-organization-diagnostics/README.md) |
| 工作台与观察 / 核心及可选平台 | React 八页导航、本地多组织、模型配置、事件/工作/成果/回执、只读成员运行状态/会话/工作区摘要 | V1：checkpoint观察仅lstat、不打开原库；定向50/全量260与独立94项通过，独立长结论因额度中断 | 检查点存在性当前无true生产来源；跨来源非原子、热配置、真实续拍/崩溃/供应商迟到、真实恢复、浏览器与整体复核未过；公共账户/多租户未实现 | [evidence/007-workspace-redesign/README.md](evidence/007-workspace-redesign/README.md)、[evidence/016-member-workspace/README.md](evidence/016-member-workspace/README.md)、[evidence/029-member-runtime-observation/README.md](evidence/029-member-runtime-observation/README.md)、[evidence/030-runtime-recent-run/README.md](evidence/030-runtime-recent-run/README.md)、[evidence/031-member-work-state/README.md](evidence/031-member-work-state/README.md)、[evidence/032-runtime-workspace/README.md](evidence/032-runtime-workspace/README.md)、[evidence/033-checkpoint-observation/README.md](evidence/033-checkpoint-observation/README.md)、[evidence/034-unregistered-runtime/README.md](evidence/034-unregistered-runtime/README.md)、[evidence/035-dispatch-observation/README.md](evidence/035-dispatch-observation/README.md)、[evidence/036-runtime-http-observation/README.md](evidence/036-runtime-http-observation/README.md)、[evidence/037-session-revisions/README.md](evidence/037-session-revisions/README.md)、[evidence/038-activity-boundaries/README.md](evidence/038-activity-boundaries/README.md)、[evidence/039-wal-observation/README.md](evidence/039-wal-observation/README.md)、[evidence/040-checkpoint-metadata/README.md](evidence/040-checkpoint-metadata/README.md) |
| 托管与运维 / platform | 有限 service/watch 入口、systemd 模板、就绪检查 | V1：工程入口；真实托管 V0 | U-041观察已受控实现但浏览器/独立复核未过；U-042单机受限托管未实现；U-008目标服务器安装、访问及U-009真实重启/备份恢复仍待资源和依赖，告警与资源到限停机待验 | [evidence/015-corp-startup/README.md](evidence/015-corp-startup/README.md)、[specs/028-member-runtime-management/plan.md](specs/028-member-runtime-management/plan.md) |
| 预算与经营记录 / 运行时及业务 | 调用额度、用量与未知费用记录、小说 mock 账本 | V1；真实运行曾按调用上限停止 | 真实成本核对与可执行预算控制；无真实支付/收入能力 | [evidence/014-real-loop/README.md](evidence/014-real-loop/README.md)、[evidence/006-novel-company/README.md](evidence/006-novel-company/README.md) |
| 质量与评估 / 工程支撑 | 机制回归、模拟与真实标记、E1/E2 检查及证据留存 | V1；真实完整业务验收未通过 | 首个真实任务及指标口径已定义，U-006/U-019/U-020真实采集和效果待验 | [specs/014-real-loop/spec.md](specs/014-real-loop/spec.md)、[evidence/016-member-workspace/README.md](evidence/016-member-workspace/README.md) |
| 目标公司实例 / ai-union-corp | 固定身份、目标、阶段章程、只读诊断、正式工作台入口 | V1：准备入口；运营 V0 | 真实筹建 → 研发交付 → 反馈 → 持续运营 | [specs/015-corp-startup/tasks.md](specs/015-corp-startup/tasks.md) |
| 项目管理与组织改进 / 工程支撑 | 单一主账、生成视图、管理检查、维护/评审/改进流程及评估协议；053重写PRD/架构提案/垂直切片和交接规则 | V1：管理规则受控验证；真实自主改进未验收 | U-065待处置重写需求/ADR及首片契约；U-033诊断/U-034申请/U-035时间记录已实现，U-019真实自主改善仍待验 | [evidence/017-project-management/README.md](evidence/017-project-management/README.md)、[evidence/053-rewrite-checkpoint/README.md](evidence/053-rewrite-checkpoint/README.md) |
| 跨 AU 协作与组织演进 / ai-union | AU关系与委托契约已定义；现有本地目录可复用，跨AU执行/派生/重构尚未实现 | V0：规划，运行未验 | U-028先满足真实单AU交付/恢复依赖，再实现双边委托和演进 | [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md)、[specs/025-au-delegation-contract/spec.md](specs/025-au-delegation-contract/spec.md) |
| 可选管理工具服务 / platform | 工具服务契约完成，仓库管理与观察可复用；尚未服务化或接入付费工具 | V0：服务规划，运行未验 | U-026依真实需求接首个免费工具；U-032付费开通和结算另验 | [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) |
<!-- management:modules:end -->

真实外部发布、业务系统接入、支付和商业经营尚无验收，不包含在“已有工作台”或“已有账本”的完成声明中。成员数量、岗位与工具应随目标演进，不能由项目管理表预设成所有组织的固定结构。

## 4. Roadmap：以结果过关

以下是本次提出的执行顺序与验收口径；不是已经通过的里程碑，也不是新增支出、生产部署或组织权限授权。没有基于资源与实际执行数据的工期，因此不编造日期。

<!-- management:milestones:start -->
| 阶段 | 结果 / 退出条件 | 状态 | 证据 |
| --- | --- | --- | --- |
| G0 工程底座 | 本地组织机制、成员执行入口、工作台及受控回归可用；明确模拟/真实边界 | 底座已具备（范围有限） | [evidence/016-member-workspace/README.md](evidence/016-member-workspace/README.md) |
| G1 公司真实成立 | 在现有组织身份下，用已授权模型自主提出并成立团队、岗位和工作；留下真实调用与筹建回执 | 待验收 | — |
| G2 首次有效交付 | 成员在真实隔离工作区完成一个小型产品改动，给出可审查 diff、测试和成果；收到验收反馈后完成一次改进；记录全部人工帮助与费用未知项；另行验收组织主动发现协作问题、试行管理改进并评估效果，不能用外部提醒或复盘文字替代实际改进。 | 待验收 | — |
| G3 受控持续运营 | 安装到目标持久主机；真实任务、空闲、唤醒、重启与恢复均有证据；完成第二轮可验收交付；到限停止，不自动续额 | 待验收 | — |
| G4 外部用户试点 | 一个外部试点组织完成创建、授权、运行、观察及支持闭环；核查身份隔离、备份和故障响应 | 待验收 | — |
| G5 可持续产品经营 | 按真实用户需求形成运营、成本、质量及收入闭环；支付/业务系统按实际需求接入 | 待验收 | — |
| G-AU AU 协作、派生与重构 | 两个已有 AU 委托交付、三层派生及有责任连续性的重构分项验收；不重复消耗资源、不扩大权限、成员保持单 AU 归属，故障后可恢复。 | 待验收 | — |
| G-TOOLS 可选工具服务 | 至少一个免费管理工具可被 AU 选择、启停、导出和替换；付费服务单独验证价格/授权/使用回执和费用核对，模拟不算真实商业验收。 | 待验收 | — |
<!-- management:milestones:end -->

**Now：G1/G2。Next：G3。Later：G4/G5。** G-AU 与 G-TOOLS 是独立能力目标，不是 G5 后的时间阶段；具体交叉依赖见开发路线。 开始 G3 验收前根据已有运行数据约定观察窗口、任务样本与资源上限。一次成功和多个文档成果均不能替代持续运行证据。是否合并 `main` 另按候选发布范围、回归与已知限制决定；本页不表示已经合并或上线。

## 5. 统一待办与当前看板

任务唯一主账为 `management/project.json`，保留 U 编号；以下视图由 `npm run management:render` 生成。实际负责人和所需责任角色分开，未认领不虚构为公司成员。

<!-- management:tasks:start -->
数据日期：2026-11-08；在制 7/8，就绪 2，阻塞 7，完成 38。这是工作项统计，不是产品完成率。

| 任务 | 内容 | 优先级 / 阶段 | 状态 | 实际负责人 | 依赖 |
| --- | --- | --- | --- | --- | --- |
| [U-001](TASKS.md#u-001) | 建立项目管理基线 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-002](TASKS.md#u-002) | 接通真实模型与工具协议 | P0 / G1 | 阻塞 | 待认领 | — |
| [U-003](TASKS.md#u-003) | 原公司自主筹建 | P0 / G1 | 待依赖 | 待认领 | U-002 |
| [U-004](TASKS.md#u-004) | 定义首个真实研发任务 | P0 / G2 | 完成 | Codex（外部工程代理） | U-018 |
| [U-005](TASKS.md#u-005) | 验证真实隔离工作区 | P0 / G2 | 阻塞 | 待认领 | — |
| [U-006](TASKS.md#u-006) | 完成真实研发交付与反馈 | P0 / G2 | 待依赖 | 待认领 | U-003, U-004, U-005 |
| [U-007](TASKS.md#u-007) | 修复真实执行阻塞 | P0 / G2 | 阻塞 | Codex（外部工程代理） | — |
| [U-016](TASKS.md#u-016) | 搭建可维护的项目管理骨架 | P0 / G0 | 完成 | Codex（外部工程代理） | U-001 |
| [U-017](TASKS.md#u-017) | 定义组织自主改进验收协议 | P0 / G2 | 完成 | Codex（外部工程代理） | — |
| [U-018](TASKS.md#u-018) | 核查组织观察与调整能力缺口 | P0 / G2 | 完成 | Codex（外部工程代理） | — |
| [U-019](TASKS.md#u-019) | 真实验证组织自主改善管理 | P0 / G2 | 待依赖 | 待认领 | U-003, U-004, U-005, U-017, U-018 |
| [U-021](TASKS.md#u-021) | 规划同构 AU、组织演进与工具服务路线 | P0 / G0 | 完成 | Codex（外部工程代理） | U-016 |
| [U-022](TASKS.md#u-022) | 定义同构 AU 最小契约 | P0 / G2 | 完成 | Codex（外部工程代理） | — |
| [U-023](TASKS.md#u-023) | 实现最小核心缺口与兼容迁移 | P0 / G2 | 完成 | Codex（外部工程代理） | U-022, U-018 |
| [U-033](TASKS.md#u-033) | 补齐有界组织诊断视图 | P0 / G2 | 完成 | Codex（外部工程代理） | U-018 |
| [U-044](TASKS.md#u-044) | 搭建NAS常驻Astra/Sol外部开发调度器 | P0 / G0 | 阻塞 | Codex（外部工程代理） | — |
| [U-045](TASKS.md#u-045) | 在AI-UNION前端配置Go及ChatGPT订阅 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-046](TASKS.md#u-046) | 修复Go账号授权及ChatGPT远程浏览器回调 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-047](TASKS.md#u-047) | 定义 AI 配置能力对齐判据与成本口径 | P0 / G0 | 完成 | 外部工程代理（OpenCode） | — |
| [U-048](TASKS.md#u-048) | 实现模型目录与三态能力查询（M1） | P0 / G0 | 完成 | 外部工程代理（OpenCode） | — |
| [U-049](TASKS.md#u-049) | 实现凭据环境变量引用（M1b） | P0 / G0 | 完成 | 外部工程代理（OpenCode） | U-048 |
| [U-050](TASKS.md#u-050) | 实现角色绑定与可用性回退（M2a） | P0 / G0 | 完成 | 外部工程代理（OpenCode） | U-048 |
| [U-051](TASKS.md#u-051) | 实现运行期失败切换（M2b） | P0 / G0 | 完成 | 外部工程代理（OpenCode） | U-050 |
| [U-052](TASKS.md#u-052) | 完成0–5批登录与模型接入工程 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-053](TASKS.md#u-053) | 确认正式开发阶段及交付发布门槛 | P0 / G0 | 完成 | Codex（外部工程代理） | U-052 |
| [U-054](TASKS.md#u-054) | 准备正式候选版安装升级与回滚验收包 | P0 / G0 | 就绪 | 待认领 | U-052, U-053 |
| [U-055](TASKS.md#u-055) | 脱敏部署文档并记录环境硬编码整改范围 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-056](TASKS.md#u-056) | 发布正式开发与NAS试运行网页文档 | P0 / G0 | 进行中 | Codex（外部工程代理） | U-055 |
| [U-057](TASKS.md#u-057) | 改为首次访问认领管理员并补重置入口 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-061](TASKS.md#u-061) | 设计真实可用的统一模型接入与订阅执行链 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-062](TASKS.md#u-062) | 实现正式模型服务与完整接入能力 | P0 / G0 | 待依赖 | 待认领 | U-061, U-060 |
| [U-063](TASKS.md#u-063) | 修复 PR #12 的跨平台与浏览器检查 | P0 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-064](TASKS.md#u-064) | 形成UNION重写规划与可交接检查点 | P0 / G0 | 完成 | codex/rewrite-planning-20261104（外部工程代理） | — |
| [U-065](TASKS.md#u-065) | 写清第一版要做的功能和开发顺序 | P0 / G0 | 完成 | codex/rewrite-s00-20261105（外部工程代理） | — |
| [U-066](TASKS.md#u-066) | 登录后创建组织，刷新或重启仍能打开 | P0 / G1 | 完成 | codex/gpt-6/session-01a1a9fa-d89d-7091-ba52-c31a1df00b23 | U-065 |
| [U-008](TASKS.md#u-008) | 部署持久服务 | P1 / G3 | 阻塞 | 待认领 | — |
| [U-009](TASKS.md#u-009) | 演练恢复与资源控制 | P1 / G3 | 待依赖 | 待认领 | U-006, U-008 |
| [U-010](TASKS.md#u-010) | 接通发布、观察和回滚 | P1 / G3 | 待依赖 | 待认领 | U-006, U-008 |
| [U-011](TASKS.md#u-011) | 验证运行中的组织调整 | P1 / G3 | 待依赖 | 待认领 | U-006 |
| [U-012](TASKS.md#u-012) | 定义运行指标口径 | P1 / G3 | 完成 | Codex（外部工程代理） | — |
| [U-020](TASKS.md#u-020) | 采集并复盘真实运行指标 | P1 / G3 | 待依赖 | 待认领 | U-006, U-012, U-035 |
| [U-025](TASKS.md#u-025) | 定义可替换的工具服务契约 | P1 / G-TOOLS | 完成 | Codex（外部工程代理） | U-018, U-022 |
| [U-026](TASKS.md#u-026) | 接入首个免费管理工具服务 | P1 / G-TOOLS | 待依赖 | 待认领 | U-025, U-006 |
| [U-027](TASKS.md#u-027) | 定义 AU 关系与委托协议 | P1 / G-AU | 完成 | Codex（外部工程代理） | U-022, U-018 |
| [U-028](TASKS.md#u-028) | 实现并验证两个 AU 委托交付 | P1 / G-AU | 待依赖 | 待认领 | U-027, U-023, U-006, U-009 |
| [U-029](TASKS.md#u-029) | 实现可递归的受控 AU 派生 | P1 / G-AU | 待依赖 | 待认领 | U-028 |
| [U-030](TASKS.md#u-030) | 实现跨 AU 职责与成员交接 | P1 / G-AU | 待依赖 | 待认领 | U-029 |
| [U-034](TASKS.md#u-034) | 建立资源与工具申请记录 | P1 / G2 | 完成 | Codex（外部工程代理） | U-018, U-033 |
| [U-035](TASKS.md#u-035) | 补齐工作生命周期与指标证据 | P1 / G3 | 完成 | Codex（外部工程代理） | U-018 |
| [U-037](TASKS.md#u-037) | New API 网关登记、观察及 AU 连接接入 | P1 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-038](TASKS.md#u-038) | New API 托管实例运维控制 | P1 / G0 | 待依赖 | 待认领 | U-037 |
| [U-039](TASKS.md#u-039) | 真实 New API 与 AU 工具往返验收 | P1 / G0 | 阻塞 | 待认领 | U-037 |
| [U-040](TASKS.md#u-040) | 规划成员执行与托管管理 | P1 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-041](TASKS.md#u-041) | 展示成员执行状态与运行位置 | P1 / G0 | 阻塞 | Codex / GPT-6.1 Sol（外部工程代理；GPT-6 Astra规划） | U-040 |
| [U-042](TASKS.md#u-042) | 实现单机AU持久托管与受限控制 | P1 / G3 | 待依赖 | 待认领 | U-041 |
| [U-058](TASKS.md#u-058) | 订阅授权结果在刷新后保持可见 | P1 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-059](TASKS.md#u-059) | 展示 Go 订阅的工作区、额度与可用模型 | P1 / G0 | 完成 | Codex（外部工程代理） | — |
| [U-060](TASKS.md#u-060) | 把 OpenCode Go 订阅接成 AU 可用模型连接 | P1 / G0 | 进行中 | Codex（外部工程代理） | — |
| [U-067](TASKS.md#u-067) | 输入一个目标，让 AI 交出第一份成果 | P1 / G1 | 进行中 | dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7 | U-066, U-069, U-072 |
| [U-068](TASKS.md#u-068) | 给第一版提意见，让 AI 交付修改后的第二版 | P1 / G2 | 待依赖 | 待认领 | U-067 |
| [U-069](TASKS.md#u-069) | 设置负责人、修改规则、撤销权限和交接工作 | P1 / G2 | 完成 | codex/gpt-6/session-01a1a9fa-d89d-7091-ba52-c31a1df00b23 | U-066 |
| [U-070](TASKS.md#u-070) | 任务卡住或重启后，找回进度并继续处理 | P1 / G3 | 待依赖 | 待认领 | U-068, U-069 |
| [U-071](TASKS.md#u-071) | 让外部管理工具通过接口操作组织 | P1 / G0 | 待依赖 | 待认领 | U-066, U-067 |
| [U-072](TASKS.md#u-072) | 填好模型连接，让 AI 读取一份资料并回答 | P1 / G0 | 完成 | codex/gpt-6/s02-2026-11-06 | U-066, U-069 |
| [U-073](TASKS.md#u-073) | 让 AI 试用新的做法，比较效果再决定是否保留 | P1 / G0 | 待依赖 | 待认领 | U-068 |
| [U-074](TASKS.md#u-074) | 安装后能持续做事，也能备份、升级和恢复 | P1 / G0 | 待依赖 | 待认领 | U-068, U-070, U-071, U-072, U-073 |
| [U-075](TASKS.md#u-075) | 接入其他模型服务，逐个验证是否真的能用 | P1 / G0 | 就绪 | 待认领 | U-072 |
| [U-076](TASKS.md#u-076) | 让组织合作交付，并能交接、合并或拆分 | P1 / G0 | 待依赖 | 待认领 | U-068, U-069, U-070, U-071 |
| [U-079](TASKS.md#u-079) | NAS 部署值守接入：五分钟巡检与可追溯交接 | P1 / G0 | 完成 | codex/deployment-coordinator/01a1b7fe-81cb-7ec0-8459-d85fd97a9ba7 | — |
| [U-080](TASKS.md#u-080) | 修复工作台浏览器 CI 的 V1 空态契约失配 | P1 / G0 | 待验收 | codex/deployment-coordinator/01a1b7fe-81cb-7ec0-8459-d85fd97a9ba7 | — |
| [U-013](TASKS.md#u-013) | 评估成员执行器选型 | P2 / G0 | 候选 | 待认领 | — |
| [U-014](TASKS.md#u-014) | 定义外部试点 | P2 / G4 | 待依赖 | 待认领 | U-009, U-010, U-011, U-019 |
| [U-015](TASKS.md#u-015) | 按需求接入业务系统 | P2 / G5 | 候选 | 待认领 | U-014 |
| [U-024](TASKS.md#u-024) | 按实际需要支持轻量工作组 | P2 / G2 | 完成 | Codex（外部工程代理） | U-022, U-018 |
| [U-031](TASKS.md#u-031) | 逐项验证 AU 拆分合并及归属调整 | P2 / G-AU | 待依赖 | 待认领 | U-030 |
| [U-032](TASKS.md#u-032) | 接入付费工具与费用核对 | P2 / G-TOOLS | 待依赖 | 待认领 | U-026, U-020 |
| [U-036](TASKS.md#u-036) | 按需求支持成员退出与任职解除 | P2 / G2 | 候选 | 待认领 | U-018, U-023 |
| [U-043](TASKS.md#u-043) | 按真实瓶颈评估成员并发与Worker | P2 / G3 | 候选 | 待认领 | U-042, U-009, U-020 |

完整验收条件、阻塞与证据见 [TASKS.md](TASKS.md)；主账为 [management/project.json](management/project.json)。
<!-- management:tasks:end -->

020–025已完成首个真实任务定义、有界诊断、生命周期/指标口径、同构AU兼容接入、可选申请流程及工具/委托契约。**当前就绪任务为0，不等于没有可执行验收/修复**：040撤掉所有原检查点库观察连接，只保留元数据探测，代价是DELETE也未知且当前无true生产来源。下一批先冻结A06旧HarnessExecutor在连接禁用/revision变化后的生效点，再做实际SDK/回环HTTP复现，不自动扩检查点元数据。跨来源非原子、热配置、真实恢复、浏览器及整体复核未过；独立94项已通过，但长结论收尾额度中断。U-002/U-005/U-008/U-007真实资源阻塞保持。见[040证据](evidence/040-checkpoint-metadata/README.md)。不提升产品目标完成度；资源到位后仍须真实筹建/交付/改善与持续运营。

## 6. 适合当前规模的管理方式

采用**目标里程碑 + 单一优先级待办 + 轻量看板 + 证据验收**。产品路线、组织运行时工程和公司运营分别可追踪，共用目标与优先顺序。

### 每项工作如何管理

链路为：目标 → 里程碑 → 模块 → 工作项 → 变更/成果 → 验收证据。工作项最少记录：ID、为什么做、验收条件、负责人、优先级、状态、依赖/阻塞、成果链接及证据。

状态使用：候选 → 就绪 → 进行中 → 待验收 → 完成；发生阻塞则明确标注阻塞原因、解除责任及原状态。完成意味着**该工作项声明的范围已被验收**：适配器代码完成，不等于真实集成完成；集成成功，不等于持续运营。

建议初始同时推进一个主要交付和一个解除阻塞的工作项；包括待验收与受阻事项一起审查，不能通过把任务移到“阻塞”就不断开启新工作。大任务按可验收成果拆小。责任角色可以一人承担多个，涉及权限/资金等既有复核要求仍保留独立评审。

### 更新节奏与决策

- 每次变更完成或获得运行证据：维护者更新主账对应模块、任务和里程碑并重新生成视图；日期流水只记变化、原因及证据。
- 每周或每个里程碑结束：短评审一次，只看实际交付、未解决失败、资源/成本与下一工作批次；这是建议节奏，尚未配置自动任务。
- 产品负责人决定目标优先级及资源取舍；工程负责人对实现和验证负责；验收角色判断是否达到结果。公司成立后可自主承担适用工作，人类董事会保留章程规定的最终控制。
- 路线变化记录原因和取舍；重大执行器、存储、托管选择写 ADR，不在聊天里悄悄更换目标。
- 当前采用仓库主账及自动生成的总览/看板。需要多人并发协作时，可将工作卡迁入 GitHub Issues/Projects；迁移时明确唯一主账，本页只汇总，不维护两份独立状态。

看板的工作流、在制工作限制和基于历史周期时间的交付预测，可参考 [The Kanban Guide](https://kanbanguides.org/the-kanban-guide)。本项目暂不以未经测量的“速度”承诺工期。

### 看哪些指标

| 指标 | 记录口径 / 当前基线 |
| --- | --- |
| 目标验收 | G0 已具备；G1–G5 未通过；不换算为 1/6 完成度 |
| 真实交付质量 | 按预先定义验收条件计算已接受交付/真实尝试；当前公司 0 次尝试，成功率无数据 |
| 反馈闭环 | 被采用反馈是否在下一成果体现；当前公司无记录 |
| 人工介入 | 记录原因、次数、耗时与替成员完成的工作；不能用“自主”隐藏人工补位 |
| 运行可靠性 | 空闲/唤醒/重启/恢复各自验收；记录故障、未决执行及恢复耗时 |
| 成本与资源 | 已知模型/主机成本、未知费用、调用额度分别展示；未知不能写成 0 |
| 交付流动 | 进行中数量、任务阻塞年龄、从开始到验收的周期；积累样本后再做时间预测 |

## 7. 历史记录如何解释

不改写原迭代证据和老任务的当时状态；看当前情况时按以下映射阅读：

| 历史位置 | 当前解释 |
| --- | --- |
| 001 tasks 的 Dashboard 未完成 | 本地观察与工作台后续由 003/004/005/007 交付；不代表公共托管已完成 |
| 005 API tasks 的真实 smoke 待验 | 011/014 已有部分真实模型证据；完整业务验收仍未通过 |
| 006 小说 tasks 全部勾选 | 工程及模拟范围完成；真实三章经营并未通过，且不是当前公司的启动门槛 |
| 009/010 执行协议与 Harness 完成 | 实现与受控验证完成；真实连续业务能力仍看 014 的失败与未完成项 |
| 015 实际开发/运维未完成 | 016 补上可选工作区工程接入与复核；真实 Docker、模型开发及发布运维依然待验 |
| README/PRD 旧“当前首版”小说描述 | 以 2026-10-20 用户确定的公司目标为准；早期内容保留为历史范围 |

本页是汇总入口；产品定义以用户确认要求为准，验收事实以具体证据为准。若出现冲突，修正汇总并留下更正记录，不从较乐观的文字推断能力已通过。

本次基线与检查：[2026-10-27 项目管理基线](evidence/2026-10-27-project-baseline/README.md)。

2026-10-28 管理骨架与规则验证见 [017 证据](evidence/017-project-management/README.md)。

2026-10-28 后续开发规划与产品约束同步见 [018 证据](evidence/018-au-development-roadmap/README.md)。

2026-10-28 核心契约与观察/调整核查见 [019 证据](evidence/019-au-core-contract/README.md)。
