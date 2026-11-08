# 053：Main Chapter V1 重建与实施计划

日期：2026-11-05。规范：[Chapter V1](../../docs/UNION_CHARTER_v1.0.md)，用户依据及固定版本见[采用记录](../../docs/CHARTER_ADOPTION.md)。本计划替换旧规划的实施入口；旧材料只通过Git历史追溯，代码/历史证据仍可用于核查复用。

## 1. 目标、架构与当前范围

目标是交付独立可用的ai-union核心，让单Agent或按目标形成的组织能够真实行动、交付、反馈、恢复和改进，并通过公开契约与可选平台及其他AU协作。先解决规范来源和工程所有者，再按用户结果实现，不按五层图拆成五个服务。

保留Python、SQLite、React及现有Harness/模型服务作为增量重组载体；技术选择见[总体架构](../../docs/ARCHITECTURE.md)和ADR-0005/0006。规范采用不证明这些既有实现已符合V1。

U-065/S00 原检查点只交付重建后的 PRD、架构/ADR、切片、S01 精确契约、AGENTS、Kanban 和 Git 记录。用户后续授权完整 U-066/S01，实施顺序与边界见 §8，受控结果见 [056](../../evidence/056-s01-core-creation/README.md)。本轮没有运行真实模型、迁移真实 AU、部署或改变仓库可见性/许可证。

## 2. 接手必读与依据锁定

1. 根[AGENTS](../../AGENTS.md)、[HANDOFF](../../HANDOFF.md)最新条目及[本轮证据](../../evidence/054-charter-v1-rebuild/README.md)。
2. [Chapter V1](../../docs/UNION_CHARTER_v1.0.md)和[采用记录](../../docs/CHARTER_ADOPTION.md)；规范来源是main提交`b2a30f3af4ad69a679c4860468d744dd285a0098`，不是本地旧main或旧DESIGN。
3. [PRD v1.0](../../docs/PRD.md)、[40条追踪](charter-traceability.md)、[总体架构](../../docs/ARCHITECTURE.md)、ADR-0004/0005/0006。
4. [tasks](tasks.md)、[S01契约](s01-contract.md)、所选用例对应源码/测试；先读范围和兼容，不能仅按文件名猜实现。
5. [主账](../../management/project.json)、[管理方法](../../management/README.md)、[在线Kanban](../../management/KANBAN.md)及实际Git状态。

意图锁定为V1规范与用户选择的开发顺序。原AU身份/历史/成果/预约/未知执行、React和已验证行为保留；不保留相冲突的旧产品定义。版本、权限、兼容或启用条件改变时先回到该契约/ADR，不用临时fallback绕过。

## 3. S00交付及下一最小实施单元

[S00处置](s00-review.md)已把来源遗漏和产品冲突展开为可审查变更。PRD Q-01由用户指定main解决；Q-02/Q-03形成有界工程方向，Q-04真实运行参数和Q-05许可证/发布操作仍在其实际入口前决定。

S00 后的首片 U-066/S01 按[首片契约](s01-contract.md)顺序完成兼容完整性、稳定核心主体及 V1 治理根创建/重开。只完成内部第一步不得关闭整个 S01。错误目录映射等真实缺口的 RED 已保留在 055，完整三步与回归证据在 056；已正确的幂等/unknown 保护不为制造失败而破坏。S01 之后的计划顺序是 S05/U-069，再满足 S02/U-072 和 S03 的前置；当前状态仍查主账。

开工前核对真实branch/HEAD、远端和已有修改；本轮发布分支`rewrite/charter-v1`，`dev`仍是日常开发主线。重新认领并处理在制容量，不把原阻塞卡退回待办来隐藏占用。

## 4. 顺序与启用门槛

| 顺序 | 用户结果 | 依赖与出口 |
| --- | --- | --- |
| S00 | V1要求、架构、任务和第一片可接手 | 本次文档/契约/看板/Git检查点 |
| S01 | 核心身份下创建明确治理根的准备态AU并安全重开；保留旧记录 | U-066；无自主业务或真实模型调用，兼容与新建结果分开 |
| S05受控工程→S02 | 治理和资源具备可执行启用条件，再配置合法模型/工具并往返 | U-069整卡完成后交付U-072，U-067等待两者完成；真实AU调用/业务通过治理、授权和资源检查 |
| S03 | 单Agent或目标所需团队承担责任并执行工作 | S01、S02调用契约及S05适用启用条件；两成员只作专门协作基准 |
| S04 | 成果→反馈→后续改变 | S03；正式采用/证据/知识纠正，真实出口另验 |
| S05真实出口与S06 | 真实修章/交接、局部故障恢复、持续监督和主动观察 | V1真实治理独立取证；U-070共享身份/事件/意图契约，独立工作不得被无关unknown全面停住 |
| S07与S08 | 授权内自改进；独立可维护发布和持续运行 | U-073/U-074；真实工作/效果及明确环境/预算/窗口，不以文档或包构建替代真实通过 |
| S09 | 每profile的真实能力兑现 | U-075在S02基础上按profile独立推进，保留其余未验项 |
| S10 | 双AU承诺、递归派生与重组 | U-076按C系列分段启用，维护责任/授权/资源和失败边界；旧工程仅作复用参考 |
| S11 | 平台或外部管理经公开契约使用独立核心 | U-071从S01接口开始设计，在S03契约具备后整体交付；逐用例重绑并退出内部表/模块旁路 |

这是依赖设计，当前优先级、认领、状态和验收只由主账维护；在线12张V1卡使用相同U编号和证据，18张旧建议已归档。新卡只依赖本批V1任务，旧工程的供应商、公司、主机排期不构成新需求前置。[tasks](tasks.md)提供每片的文件、测试和失败反例。

## 5. TDD、复杂度与协作

**TDD Route: strict**。依据：2026-11-04用户明确要求，最新V1重建不撤销它；即使宿主Aegis默认off，行为改动仍执行严格路线。文档和生成视图只做结构/一致性检查。

每个行为单元先确认缺少或错误行为导致的RED，再最小GREEN，最后REFACTOR并保留回归。既有正确行为不删除、不故意打坏。正常/越权/重复/迟到/中断/重启成对验证，依赖方与调用方一起验。

开始编辑前说明用户需要、现有所有者和最小边界。当前Engine/Console混合多职责，新责任不得继续无界堆入；用本片实际用例迁出纯规则/应用所有者。只有将真实代码迁入具体模块时才建立该目录及局部AGENTS，不生成空壳或泛化端口。

可以在契约和文件归属确定后委派独立实施/复核；同一事务/Schema/公共类型顺序集成，协调者独占主账、索引和Git变更。开发子代理不是产品AU成员，不证明组织已经自主开发。权限/费用和身份迁移在采用前需要另一个工程角色的独立复核。

## 6. 验证与证据

使用`.nvmrc`指定Node 24.19.0和项目锁定Python环境。Windows设置`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`，Python命令替换为`.venv\Scripts\python.exe`。

```sh
git status --short --branch
git log -3 --oneline
npm run management:status
npm run management:render
npm run check:management
npm run check
python3 -m unittest discover -v
```

运行时切片根据实际变更追加`npm run test:workspace`、`npm run test:model-access`、`npm run test:model-service-browser`、`npm run test:model-service`或发布包测试；S01的具体选择见首片契约。文档检查不运行无关UI截图流程来凑证据。

新证据目录独立保存脱敏结果和范围，私有数据库/凭据/宿主路径/执行日志留在宿主。检查构建不代表组织循环、真实供应商、真实容器、发布或持续运行。待提交候选也必须能通过自身已提交工具的管理检查，不能只依赖同工作区他人未提交的脚本。

## 7. 交接与恢复

S00经独立需求/架构复核、文档与回归检查后，通过主账record、在线Kanban版本更新、提交和推送形成检查点；原WIP容量恢复，原外部阻塞保留。真实远端SHA和下一步在本轮证据/HANDOFF记录。

重入时先比较用户最新指令、固定基线、当前HEAD和任务认领。新证据发现旧结论错误时，修正当前依据并复查相关活动工作；不把历史副本重新作为优先规范。来源/身份/兼容/恢复契约不一致时回到对应所有者解决，仍可继续不依赖该问题的已授权工作。

## 8. 2026-11-05：完整 S01 的实施顺序

用户在 S01a 提交 `1384c09`、收据 `219168d` 后明确要求继续直到完整完成 UNI-020（在线 #20 / U-066）。本节细化已有 S01 契约，不引入后续切片或真实迁移/部署。T01–T04 现有行为与证据保留；完成范围为受控准备态创建、身份/目录安全、重开和兼容。

代码变更必要：现有账户只绑定用户名，Console 启动隐式建表，创建直接调用 legacy Engine；配置或文案无法提供稳定主体和 V1 隔离。沿 ADR-0005/0006 把创建规则、流程和存储迁至实际所有者；Console/HTTP 保留认证和装配职责。没有另一份任务主账。

| 顺序 | 最小行为与所有者 | RED 与验证 |
| --- | --- | --- |
| S01b.1 | `identity.py` 绑定随机 principal；`identity_schema.py` 拥有 auth/catalog 版本、初始化与显式升级；`scripts/upgrade_core_identity.py` 是受锁保护的操作入口 | 新账户→登录→改密/恢复→重启保持 principal；旧库启动先拒绝且无恢复写入；升级幂等、故障回滚、旧会话失效、原 payload/receipt 原文保留、旧创建/认领仍可用 |
| S01b.2 | `scripts/release_package.py` 明确收录升级工具并检查候选的 auth/catalog 兼容；升级前私有备份只在没有后续写入时可回退 | 真实临时旧库、备份/回退、安装后执行升级；缺声明旧候选或不兼容版本不能激活、回滚或启动 |
| S01b.3 | `domain/creation.py` 纯规则；`application/creation.py` 单一创建流程；catalog、legacy 与窄 V1 adapters 各自持有实际存储责任；错误类型独立于 Engine | T07–T09：受信根、先查原意图再比较、不重验已保存请求、纯校验失败不分配；AU 状态/根/章程/审计同事务；每个持久阶段故障、重启和 unknown 原请求查询 |
| S01c.1 | 共用目录核对后按 profile 装配；Engine 构造/写事务及直接 SQL 调用者拒绝 V1；HTTP 版本化读取/回执与 session 投影 | T06/T10/T11：同名重置与跨主体拒绝；旧 CLI/runner/start/amend/模型/连接测试/workspace 不改 V1；混合组织启动、关闭、列表与正常 legacy 控制样本 |
| S01c.2 | `web/console` 身份、API、commands 与准备态页面接入 `create_v1`；小说 company 保持显式 legacy 创建 | T12：创建→回执→刷新/重启登录→原 AU；未激活说明、键盘、320/390px；断网保留原请求 kind/ID 查询，旧输入保留，不自动退回旧 create |
| 交付 | 独立身份/持久化/兼容复核，完整验收及主账/在线卡/Git | 全 T01–T12、固定 npm/Python、实际浏览器、安装候选、Aegis bundle/check；仅本轮增量提交推送并读回远端，按真实证据关闭 U-066/#20 |

TDD Route 为 `Mode: off / Decision: strict / Strict authority: explicit user/project request`；每个新行为观察真实 RED 后做最小 GREEN，随后重构及相关回归。既有正确测试不删除；旧 schema 夹具改用明确列名属于已冻结兼容升级，不降低断言。

复杂度预算：Engine 已超 800 行、Console 混合职责。本片对二者采用迁出规则/流程及装配，禁止新增治理执行框架；新纯规则、创建流程、身份升级和存储各自有单一责任，局部 AGENTS 随代码落地。来源错误、权限/事务边界冲突回到对应契约；测试失败先定位所有者，不能以 fallback、宽松 profile 或删断言过关。

共享 schema、创建与入口集成由协调者顺序完成；独立工程评审者只读复核，不修改主账、在线卡或 Git。完整 S01 通过后停止，S02/S03/S05 等仍按后续任务授权。

实施核对：上述 S01b/S01c 和 T01–T12 已有 [056 证据](../../evidence/056-s01-core-creation/README.md)及[独立身份/持久化、前端评审](../../docs/reviews/2026-11-05-s01-core-creation.md)。最终全量为 Python 481 项（5 平台跳过）、前端 70 项，实际浏览器 S01 30 项/legacy 71 项，实际安装候选 133 项；各自覆盖范围和未验条件保留在证据说明中。任务完成记录与 Git/在线交付读回以唯一主账及本批交付收据为准。

## 9. 2026-11-05：完整 S05 受控治理

用户进一步授权完整 U-069 / #24，起点 `d9ff5ad23201ee0813707a00f65a0b0d9012a3ee`。Goal 是可执行治理、撤权和责任交接的完整受控工程；Architecture/Tech Stack 延续 Python/SQLite、React/TypeScript、既有 HTTP/Identity/发布器。依据 PRD F07/F09/F20、ADR-0006 编码前细化和 [S05 精确契约](s05-contract.md)，不是创建第二个规划基线。

Change Necessity：S01 当前状态故意固定为创建者/准备态；只改说明或保存 DTO 不能执行旧规则修章、可信继任或拒绝旧授权。最小新增所有者为真实治理规则/责任规则、应用和 AU 事务适配器；Console/HTTP 只装配，Identity 保持唯一认证所有者。预评审确认需要 V1 真实本地责任用例，不能以 legacy 测试代替。

| 顺序 | 文件/所有者与最小变化 | 验证出口 |
| --- | --- | --- |
| S05.1 | `identity.py`/`identity_schema.py`、reset 工具及既有 release_package：无权 core 参与者、显式 auth 0/1→2 升级、只重置 owner | G01 真实注册/登录/权限/升级/故障/回退；现有 identity/creation 回归 |
| S05.2 | `domain/governance.py`、`adapters/governance_store.py`、`application/governance.py`；CoreAUStore/CreationCatalog/CreationService/Console/HTTP 只按新所有者装配 | G02–G04/G08：真实 HTTP 采用/修订/交接/超时；原创建快照、审计、回执与失败事务 |
| S05.3 | `domain/responsibility.py` 由治理事务调用，显式本地 Member/绑定/Work/Mandate/尝试/内部结果 | G05–G07：派生授权、行动/接受两边界、旧版本/跨 AU/迟到拒绝、交接原责任 |
| S05.4 | `web/console` 的 API/types/workspace、Identity、PreparedAU 与实际 `features/governance`；局部 AGENTS 随模块落地 | G10：先界面行为 RED；类型/组件检查、真实浏览器闭环、恢复与设备条件；旧 S01/legacy 浏览器 |
| S05.5 | 现有发布器声明 core AU schema、安装后的真实模块/升级验证；文档、主账、在线 #24、HANDOFF 和本次 evidence | G09/G10、固定全量检查、独立工程权限/持久化和 UI 复核、Aegis bundle/check、精确暂存提交推送及远端 SHA |

TDD Route：`Mode: off / Decision: strict / Strict authority: explicit user/project request`。每个行为先观察真实缺口的失败，不破坏已正确的测试。文档/生成视图执行结构检查。命令见 §6；新测试位于 tests/test_governance*.py、tests/test_core_participants.py 和对应前端模块，浏览器沿 scripts 的既有 Playwright Core / Chromium 路径。

Complexity Budget / Owner Fit：Engine 已超 800 行，Console 混合多职责，本片不添加治理业务；后者只装配新应用。Identity/Schema 在现有单一职责内扩展；纯规则分别按治理和责任拆分，事务/历史单一适配器。目标为每新增规则/应用文件约 250–400 行；触及上限先检查职责而非硬拆零碎 helper。共享事务/schema/接口由协调者顺序集成；类型契约冻结后只委派无冲突界面实现，独立复核只读。

Compatibility / Retirement：S01 schema 1 创建/重开原样保留，只有明确采用升级 schema 2；原 creator 授权分支在当前读取中退役，以 AU 当前规则替代，历史创建回执仍保留 creator 归属。legacy profile 只兼容既有行为并继续拒绝 V1。无双写/双派发/读迁移；真实模型、资源、AI Execution、部署和真实业务验收不在此授权。

执行就绪：PRD/ADR/当前代码与独立编码前复核已核对；无缺失用户决策。当前 checkout/上游及既有 dirty 快照见 Aegis work 和本次证据。意图/身份/版本/原创建连续性或兼容证据不一致时先回到契约所有者；不以宽松 fallback 或删测试过关。完成须覆盖全部 G01–G10，不将部分实现关闭 U-069。

实施核对：完整 G01–G10 已有 [057](../../evidence/057-s05-governance/README.md)的行为、独立评审、实际浏览器与安装证据，主账记录为 controlled。S05 人类内部记录不替代 AI Execution；新 V1 模型/工具入口仍由 S02/S03 交付，真实治理与持续运行未在此验收。

用户要求重新核对近期用户结果及管理路线后，新增[一页近期路线建议](../../docs/NEAR_TERM_DELIVERY.md)。它明确整卡 S05 前置是本计划的工程选择，并指出本节 S05 真实出口虽与 S06 并列，U-070 主账验收尚未明确写入治理修订/交接。建议补入该卡及重映射里程碑/历史暂停；未据本页擅自变更未来卡依赖、认领或旧任务状态。

## 10. 2026-11-06：完整 S02 模型与只读资料往返

Goal：交付 U-072/#21 的保存、有限授权、真实工具往返和默认采用。Architecture/Tech Stack：沿 Python/SQLite/React、固定 modeld/OpenCode；复用 Harness 有界协议，治理事务保留单一写入者。Basis：PRD S02、ADR-0005/0006 编码前细化和 [精确契约](s02-contract.md)。本轮主账已认领，HEAD `c31bf0e`；开工快照在宿主 `.union/s02-taskstart.json`，预存修改保留。

Change Necessity：现有模型传输构造 legacy Engine、账号入口要求 platform_admin、有界验证仅在内存，不能靠配置实现 V1 授权/恢复。最小代码责任是 V1 模型领域/应用、私有请求适配器、modeld 的用户 API profile 及原请求取证、正式模型页。无需第二套组织 Engine、通用 Agent loop 或私有平台。

| 顺序 | 所有者/文件与交付 | 验证 |
| --- | --- | --- |
| S02.1 | domain/model_access.py、application/model_access.py、adapters/model_access_store.py；governance/core store 的 schema 3 读写装配，Console/HTTP 窄入口 | M01–M04：真实 HTTP/SQLite RED，身份、资源、并发、原字节/审计与版本 |
| S02.2 | services/modeld/src/api-accounts.ts、kernel/server/journal；独立 API 账号/grant 同事务、完整迟到事实；model_service 的共享协议规则 | M02/M03/M06/M07：实际 modeld/SDK 回环，保存不推理、串 AU/改端点、grant 撤销/迟到用量 |
| S02.3 | application/model_checks.py、有界共享工具往返规则；持久 attempt、资料、工具回执、原请求查询、当前授权/结果/用量 | M04–M08：正常/失败配对，崩溃、取消、重复与两次计量 |
| S02.4 | web/console 的 features/models、Models 入口、API/types 与 V1 read_document 选择；复用现有工作台/表单样式 | M09：组件 RED、实际浏览器/四宽度/键盘、unknown与身份隔离 |
| S02.5 | scripts/release_package.py schema 3；文档/证据/主账/Kanban/HANDOFF/Git | M10：相关回归、npm check、Python discover、实际安装；指定授权模型真实往返；独立复核，精确提交推送及远端 SHA |

TDD Route：Mode off / Decision strict / Authority explicit user/project request。每个新行为先观察真实 RED 再最小 GREEN，现有正确断言保留；文档用一致性检查。共享 schema/事务/主账/Git 由协调者顺序集成，契约冻结后可委派界面与独立只读复核。执行路线为协调者实现后端、独立界面实施及独立复核；用户已经授权 S02，无需再批准常规实施决定。

Complexity/Owner Fit：Console/Engine 只装配，禁止继续塞模型业务。新纯规则、应用、执行编排和私有存储各按单一责任约 250–400 行审查；超出先分析职责，不为行数压缩代码。旧消息/结果验证由共享 helper 收敛，旧 Engine/Harness 客户保留；不得双写、双循环或从主模型失败扫描其他凭据。新 state/raw 请求分别由唯一写入者保存，同一 AU 事务可联合提交。

Compatibility/Stop：schema 1/2 与 legacy 回归；schema 3 显式采用且候选兼容检查。无生产迁移、部署、S03 工作或其他 profile 扩张。真实账号/profile/授权范围在执行前落实；缺失不妨碍已授权工程，不以超时未回复当花费许可。M01–M10 含真实出口全部满足才关闭整卡，工程绿色不替代它。

开工容量按五项历史占用加一个 V1 实际执行位设为 6，并记 U-072 history；不再按每张 V1 卡临时增容再恢复，也不伪造历史任务暂停或完成。正式暂停/承接与里程碑改造仍是独立管理建议。

## 11. 2026-11-06：执行链细化与 U-072 样板

用户最新要求是先把“部署进程、目标到首份交付的代码链、每模块具体改变”说清，再展开当前开发卡。本段是 §10 的设计补充，保留完整 S02 目标；未来 S03/S04/S06 仅细化设计，不因文档变更获准开工。

唯一技术说明在 [ARCHITECTURE](../../docs/ARCHITECTURE.md)：[部署与存储](../../docs/ARCHITECTURE.md#runtime-deployment)、[首份交付时序](../../docs/ARCHITECTURE.md#first-delivery)、[接口/事务/恢复](../../docs/ARCHITECTURE.md#execution-contracts)、[模块改造](../../docs/ARCHITECTURE.md#module-changes)。代码核查和证据边界在 [058](../../evidence/058-s02-model-tools/design-readback.md)。用户反馈卡片过于抽象后，12 张卡的主账正文改为具体功能、操作和演示，由 [TASKS](../../TASKS.md#u-072)生成；U-072 原四块开发细目和其他卡的完整技术验收保留在 [tasks 开发附录](tasks.md#开发细节与完整验收依据)，不另建状态账本。

已确认 S02 使用 ModelServiceClient 和持久两阶段协议，没有接入旧 Engine/runner/HarnessExecutor。它读取用户提交的单份文本；宿主目录工具是 S03 拟议资料适配器。下一次 S02 行为修改先在现有契约细化结构化诊断和事件用量字段，再按严格 TDD 修复特殊字符/跨分片凭据过滤、线程启动失败恢复、中断用量展示和具体错误。安全反例仍 RED、浏览器可读性仍失败；最终安装与真实 profile 未验证，不能写成只等真实账号。

S03 的共享 Harness/单次调用提取必须先冻结 step_ref→attempt/原请求的持久关联、模型事实与采用恢复、父子预约和兼容调用者；S06 再按同一 Runtime 所有者承接独立槽位与恢复监督，不追加第二个调度器。对应可演示子功能见 [tasks S03/S04/S06](tasks.md)，具体后续机制须在对应契约及编码前 ADR 细化中确定。


## 12. 2026-11-08 审查处置：执行优先与安装拆分

本节细化工程协调，不授权未来产品切片自动开工。S03 下一出口为复用 ModelServiceClient 的有界自动尝试：开始责任 → 预约步骤 → 单次推理/目录工具 → 提交成果 → 完成尝试；fake 严格 TDD 后做已授权真实验收。手动入口保留为补救，不继续扩张外围表单。

S06 的实施前置调整为 S03 自动执行尝试与 S05 治理，不强制等待 S04 反馈；S07 保留 S04 依赖。S06 设计需测量同 AU 串行事务耗时、状态字节数、回执/步骤增长、并发冲突和恢复时间，依据明确运行目标提出拆表 ADR。原审查举例的 1 MB/1 万条不是强制迁移阈值，不因预研执行数据迁移。

S08 保留一个 U-074 父卡，先验收独立环境安装、固定版本构建、认证与 S02 一次往返；再验收连续使用、升级/恢复与停止/退出。早期安装由部署协调者推进，持续出口仍等待相关工作/监督/反馈能力，子项通过不关闭父卡。S11 的只读契约设计和完整外部执行分开验收；后者保留 S03 依赖，不因里程碑标签宣布提前实现。

rewrite → dev 的集成检查点见审查处置页：先保证 S03 真实自动/中断出口、操作看板一致性、跨平台链接边界和候选全部 CI，再处理 dev 独有变化。原历史 spec/证据保持原 ID 和路径。
