# 028：成员执行与托管管理规格

2026-10-30 · 产品需求来自“每一个员工的Agent应该部署在哪里”及本轮计划请求。实施路线、文件落点和前置条件见 [plan.md](plan.md)；状态以 [主账](../../management/project.json) 为准。

## 目标与边界

平台提供托管、观察和工具接入，AU按自身目标组织成员、安排工作。员工身份持续存在，执行会话和运行进程可更换；创建员工不要求新建服务器。成员所属AU保持唯一，独立公司和企业内部部门使用同一机制。

首版单机，每AU一个有效派发器，员工串行共享执行服务。存储、会话及授权隔离不等于进程/容器物理隔离；当前团队共享业务目录也不提供岗位间文件保密。任何并发/多租户隔离扩展另立规格。

## 用户流程

1. 宿主登记或安装 AU 执行服务，不改写成员身份或自动开始消费。
2. 发起人在组织“执行与资源”中查看运行位置、宿主活性、派发状态、预算和工作区可用条件，按已有运行授权启动。
3. “成员与岗位”显示员工当前/待执行工作、任务会话及最近结果；空闲员工仍有身份和职责。
4. 浏览器关闭后托管服务继续监听；服务断开时保留最后状态和检测时间，停止把旧心跳当成在线证据。
5. 停止/恢复按当前任务与外部执行证据核对；没有重复执行，也不清空错误、预算或历史。

## 拟定公开契约（实施前冻结）

扩展既有 `/api/snapshot?organization_id=...`，兼容旧字段；读取无副作用，全部引用受组织会话范围检查。

| 投影 | 最小字段及说明 |
| --- | --- |
| `runtime` | `runtime_id?`、公开名称、`mode`（embedded/managed_local/external/unregistered）、`instance_id?`、`observed_at?`、`liveness`（confirmed/unconfirmed/unknown）、`dispatch_state`、`active_run_id?`、`capabilities` |
| `member_execution[]` | `member_id`、有效任职引用、当前/待执行工作引用、最近run摘要、`work_state`、`reason_codes[]`、`session`摘要、`workspace`摘要；状态取自宿主记录而非模型自报 |
| `session`摘要 | 不透明ID、最近更新时间、是否存在检查点、接续条件/待核对原因；不包含消息/文件/私有路径。存在检查点不能单独确认恢复安全 |
| `workspace`摘要 | `mode`（virtual_only/shared_business）、有效授权与配置revision、所需能力及阻塞原因；不输出挂载路径、镜像凭据、Docker参数或其他成员私有内容 |
| 平台托管目录（U-042） | 仅 runtime_manage 会话可跨AU观察/控制；普通 AU 页面仅看本组织公开摘要。宿主专属路径、PID和服务单元映射保持私有 |

员工工作状态采用有依据的组合：`executing`、`ready`、`waiting`、`blocked`、`idle`。组织暂停、预算耗尽、依赖未满足、能力缺失通过原因字段解释；历史unknown或running缺活性标为需核对/活性未确认，不能以idle覆盖。组织决策轮单列，避免将所有员工显示为“正在思考”。

### 2026-10-31：成员工作状态的局部契约

`current_work_id` 表示该成员行的代表工作，不是“正在执行”的承诺；只引用仍属于本人的未完成工作。同级沿用持久状态既有遍历顺序，不从ID或时间猜测业务优先级。以下选择是观察规则，组织仍自主安排工作，Engine/runner调度及授权不改变。

| 优先级 | 代表事实 | 状态 / 主原因 |
| --- | --- | --- |
| 1 | 本人有未核对unknown执行，或本人工作needs_review | blocked / run_requires_reconciliation或work_needs_review |
| 2 | 本人running工作匹配当前宿主确认的running记录 | executing；否则blocked / activity_unconfirmed，匹配failed记录用run_failed |
| 3 | 本人存在依赖均已交付的pending工作 | 按下述AU派发门槛判断，否则ready |
| 4 | 本人blocked/failed工作 | blocked / work_blocked或work_failed |
| 5 | 本人依赖未满足的pending工作 | waiting / dependency_pending |
| 6 | 本人paused工作 | waiting / work_paused |
| 7 | 无上述事实 | idle，代表工作为空；delivered/cancelled不作为当前工作 |

第3级依次检查：全AU任意unknown→blocked/run_requires_reconciliation；任意未确认running→blocked/activity_unconfirmed；已确认running→waiting/dispatch_busy；预算受限→blocked/budget_limited；暂停派发→waiting/dispatch_paused。门槛不将其他人的依赖等待或真正空闲统一改成blocked。

本人unknown对应仍属本人的未完成工作时可引用该工作；决策执行没有work_id，或原工作已交接他人时，代表引用为空，不借用他人工作。needs_review不因run仍running且有活性而变成executing。已结算blocked/failed不会掩盖另一项依赖满足的pending；未知记录必须通过既有受信接口核对，读取不执行核对或重放。

原因字段只输出稳定代码，不拼入私有错误/日志/路径。recent_run仍取该成员最新持久执行，公开runs顺序不变。会话只关联本人run；工作交接不移交原执行会话，代表工作的run仍属旧成员时，新成员行返回空会话摘要，不回退到无关历史。工作区和检查点/恢复语义由后续切片验收，本契约及局部回归不关闭U-041。见[031证据](../../evidence/031-member-work-state/README.md)。

### 2026-10-31：代表工作与工作区许可摘要

`workspace.available` 表示宿主配置启用、代表工作的有效任职及当前章程/岗位许可的交集；不表示Docker健康、已安装镜像、当前命令可执行或会话可安全恢复。真正的workspace.available(package)/authorized/execute仍独立核查正式running工作包、版本、暂停、有效任职与命令回执等门槛，本切片不修改这些授权路径。

| 条件（由上至下） | 摘要 |
| --- | --- |
| 未配置或旧库没有工作区记录 | virtual_only、revision为空、available=false、workspace_unconfigured；读取不建表 |
| 已配置但enabled=false | shared_business、保留实际revision、available=false、workspace_disabled |
| 本成员无有效任职 | available=false、no_active_assignment |
| 没有代表工作current_work_id | available=false、no_current_work；即使仍有一个或多个有效岗位也不猜选当前工作身份 |
| 代表工作关联任职失效或成员/岗位不一致 | available=false、workspace_not_authorized，不回退到其他岗位 |
| 代表任职有效，当前章程与该岗位均允许workspace_execute | available=true、无原因；否则workspace_not_authorized |

直接以代表工作的assignment_id/position_id判断，不能任选首个任职或对全部岗位权限求并集。交接后使用新工作的有效责任归属；其他岗位的许可不能借给本工作。暂停或needs_review工作仍可能具备上述静态许可，但真实执行授权继续拒绝不满足运行门槛的命令。此摘要不决定组织岗位、任务或工具选择，不新增字段或真实权限，不输出目录/镜像/私有回执；见[032局部证据](../../evidence/032-runtime-workspace/README.md)。检查点/部署描述、实际浏览器和完整观察边界仍待验收。

### 2026-10-31：检查点存在性与接续提示

2026-11-01 040现行契约：`session.has_checkpoint`保留boolean或null。无本人run/匹配会话、旧库无会话表，或固定检查点路径在元数据探测时明确缺失为false；任意存在文件（DELETE/WAL/空/损坏/其他会话或namespace）、权限/I/O异常、符号链接/非目录父项/特殊目标均为null。true及前端对应分支保留协议兼容，本观察实现没有true生产来源。false不保证随后仍缺失，null不表示没有检查点，任何观察值都不授予真实恢复权限。

固定使用当前Engine根目录下harness/checkpoints.sqlite3，不接受外部路径；只用lstat探测harness是真目录及固定目标的元数据。不打开原检查点文件/文件头/SQLite，不调用SDK saver/setup/get_tuple/get_state，不查询任何checkpoint内容，不使用immutable/复制库/新锁/独立元数据表。原有Harness写入和真实接续规则不变。历史033的true与039的非WAL查询是当时行为，当前以040为准。

040通过删除原库观察连接，移除039非WAL模式切换/路径替换导致观察连接创建sidecars的入口；旧connect钩子不触达不能包装成转换已经执行。仅可声明本checkpoint观察不因SQLite连接创建/修改sidecars，不保证整个HTTP请求或外部并发不会改变任何文件。组织库与文件系统不是原子快照；存在性可见度缺失、跨来源非原子、真实恢复、浏览器及整体U-041仍待验，见[040矩阵](../../evidence/040-checkpoint-metadata/matrix.md)。

恢复提示按优先级：本人run为unknown/reconciled或会话unknown→requires_reconciliation；run仍running或会话completed→not_available；paused/running/failed候选且原run已结束时，存在记录→requires_validation，无记录→not_available，核查未知→unknown；陌生会话状态→unknown。空会话保持not_available。删除possible；requires_validation仍须现有Harness校验task_key、身份任职、章程/连接/工作区版本及执行状态，观察接口不复制授权或发起重放。

成员页严格区分“存在检查点，接续仍需核对”“未发现检查点”“检查点状态未知”，不把null显示为不存在，不新增恢复按钮。局部证据见[033](../../evidence/033-checkpoint-observation/README.md)，不关闭U-041或证明真实托管恢复。

### 2026-10-31：未登记部署与宿主活性分列

当前没有持久runtime登记/绑定机制，部署摘要固定为mode=unregistered、name=部署位置未登记；runtime_id/instance_id/observed_at为空。不得从Console、CLI或service入口、host owner、PID、心跳或读取时间猜测embedded/managed_local/external或填登记字段。capabilities=[]表示没有已登记实例能力声明，不否定现有串行派发、会话与工作区工程能力。

宿主活性仍依既有activity/锁证据为confirmed或unknown，active_run_id仅取本AU内running且host_confirmed匹配owner的run。无登记不抹去真实宿主活动或成员executing事实；新宿主活性不能认领旧owner的run，活性丢失也不自动recover或重派。派发状态沿用既有算法，不在本切片统一顶层与runtime的派发口径差异。

资源页使用独立部署/宿主活性文案：部署位置未登记；已确认/活性未确认/活性未知；无已确认的活跃执行。不能把活性unknown翻译成外部执行“待核对”，也不把confirmed说成托管在线。其他合法mode的显示映射保持兼容，fixture展示不是已实现登记机制。JSON字段与枚举集合不变，不做迁移、登记、回填或新增控制权限。局部证据见[034](../../evidence/034-unregistered-runtime/README.md)，U-041与U-042不据此通过。

### 2026-10-31：单一派发观察口径

snapshot.dispatch_state与runtime.dispatch_state在同一读取中只计算一次、取同一个值，优先级为：任意持久unknown→needs_review（不论暂停意图）；否则有暂停意图且存在持久running或已确认宿主活性→pause_requested；否则有暂停意图→paused；其余→enabled。owner匹配只决定执行活性/active_run_id，不能消除持久running的暂停待核实。

pause_requested表示“暂停已请求，结束状态尚待确认”，涵盖宿主在run前后或watch等待的活性；无running不能证明宿主已静止，也不代表远程已取消。enabled只表示没有暂停/unknown观察条件，不承诺预算、依赖、权限或工作可执行。此优先级不替代Engine/runner的真实检查，不改next_step、成员状态、恢复或派发行为。

公司诊断的paused blocker必须读实际engine.paused()，不能由非enabled摘要反推；unknown仍保留unresolved_execution，不能误报用户暂停。该诊断本来多源读取，不宣称原子快照。前端保持读取同一快照的两处字段，仅调整pause_requested文案，不新增按钮或控制。局部证据见[035](../../evidence/035-dispatch-observation/README.md)，不关闭完整U-041。

U-042 控制API建议独立 `/api/runtime-commands` 与 `/api/runtime-receipts`，沿用同源验证、幂等、持久回执及基准版本；服务端从固定绑定解析动作目标。定义“服务控制”和“组织运行”两种授权及其组合，不通过网页隐藏按钮实现权限控制。

### 2026-10-31：实际 HTTP 子集与未关闭边界

实际loopback Server/cookie的权限、同ID跨AU隔离、全JSON私有资料排除和稳定fixture只读子集已验证，见[036矩阵](../../evidence/036-runtime-http-observation/matrix.md)。宿主显式创建的global board/observer沿用现有全AU范围；限域会话只能读获授权AU，公开请求中的role/organizations/member/runtime_manage/root/path参数不能扩权。不将全局宿主观察解释成普通成员权限，runtime控制接口仍未实现。

HTTP已覆盖owner退出后未确认，不等同A03心跳时间过期或旧实例迟到回执；观察撤权和历史检查点不恢复，不等同A06真正执行新会话。A06连接revision、工作区revision与任职变化分别通过实际SDK证明旧消息排除、新会话和历史保留之前保持未验。A03/A06全项、WAL并发/跨库/真实恢复、实际浏览器及U-041整体不因本次子集通过而关闭。

### 2026-10-31：A06 实际 SDK 子集

连接revision或工作区revision分别单独变化后，实际Harness以新session/task_key运行，下一回环HTTP请求及新SDK历史不含旧私有草稿；原paused/continued会话、run/用量、非空命令回执和旧thread检查点/writes保留。同版本重开Engine/Executor可续接同thread历史；正式handoff依法同时改变member/assignment/work_version，验证整体交接隔离，不宣称单独证明某个hash字段。见[037矩阵](../../evidence/037-session-revisions/matrix.md)。

正式禁用连接时，锁内新factory解析拒绝且请求/预算/run/session不新增；不证明已有Executor的连接快照热撤销。禁用工作区后SDK不提供工具，伪造工具调用仍不得运行容器；HTTP响应在途仅撤岗位workspace权限时，已提供的工具在执行阶段重新检查并拒绝，收到的模型用量保留。实际SDK配合确定性HTTP及容器替身属于受控验证，不提升真实供应商/工作区/恢复或公司运营等级。已有Executor热更新、在途配置竞态、全部授权组合、A03、WAL/跨库、实际浏览器及U-041整体保持未验。

### 2026-10-31：A03本地时间过期与回执保护子集

host_activity只有在0<=心跳年龄<=5秒且本地runner.lock仍被持有时确认活性；过期/未来时间不确认，但不取消原执行、不释放原锁、不自动recover或重派。原owner仍持锁且run/工作/任职有效时，过期后的合法原回执可以结算。实际首拍/锁、受控时钟及冻结续拍调度的边界验证见[038](../../evidence/038-activity-boundaries/matrix.md)，不把owner退出替代TTL过期。

正常新Runner持锁进入新owner后，先recover旧running为unknown再阻断派发；旧work/progress回执被拒，迟到fail_run不覆盖已结算状态。明确核对fixture从未外部执行后，可发起新run；旧reconciled回执不能替新run交付或污染预算/历史/资产。这是run.status/工作版本与串行启动保护，没有新增或证明独立epoch/owner-token fencing。真实续拍可靠性、进程崩溃、供应商迟到网络响应、跨进程/主机fencing、WAL/跨库、热配置、实际浏览器及U-041整体仍未验。

## 状态与恢复规则

- 持久事实（成员/任职/任务/run/预算）仍由 Engine 管理；运行活性来自当前实例心跳和锁；服务管理器返回状态作为单独证据。三者不相互覆盖。
- 只读观察不调用恢复方法。启动时由持锁派发器沿用 Engine.recover；未知外部模型/工具结果需要既有核对流程，不能直接以任务checkpoint重放。
- 旧数据库采用兼容投影。宿主显式绑定才保存新的runtime配置；未登记信息保持unknown。读取不能产生“员工已经部署”记录。
- 检查点、组织数据库、正式资产和私有配置独立于可重建进程；不把业务容器可写目录当成员记忆的唯一来源。迁移/备份沿用既有一致性要求，不能只拷贝单个SQLite文件。
- 运行模式切换需要旧派发器退出和未知记录清理；新实例必须有自己的身份与活性依据，不接受旧进程迟到回执替新实例宣告成功。

## 权限矩阵

| 主体 | AU执行摘要 | AU运行/暂停/核对 | 托管服务控制 | 宿主目录/上游凭据 |
| --- | --- | --- | --- | --- |
| AU观察者 | 本AU允许的摘要 | 无 | 无 | 无 |
| AU board | 本AU摘要 | 沿用已有授权与预算 | 仅board身份不提供 | 仅既有受信配置入口，网页不回显秘密 |
| 宿主授予 runtime_manage 的运营者 | 已授权托管范围 | 仍需相应AU运行权限 | 固定绑定内操作 | 受信私有配置；不作为公开API返回 |
| 普通成员Agent | 沿用其任务上下文 | 沿用岗位工具与组织决定 | 默认无 | 无 |

网关管理权限不授予运行时控制。后续若由运营AU维护平台，须另行将固定动作工具绑定到其有效岗位和宿主授权，不能仅因目标写了“运营平台”自动放开。

## 验收矩阵

| 编号 | 情景 | 通过标准 |
| --- | --- | --- |
| A01 | 两成员、不同工作共享运行时 | 身份/任职/会话引用正确；单派发器，无跨会话草稿串读 |
| A02 | idle/依赖等待/暂停/额度耗尽 | 各有正确原因，展示成员仍存在；等待和刷新期间模型调用增量为0 |
| A03 | 活跃执行、心跳过期、旧实例迟到 | 活性有依据；过期显示未确认，不声称远程已取消，不启动新执行 |
| A04 | 旧库、未注册环境、无工作区 | 兼容读取、不写迁移副作用、不伪造在线；无代码工具的成员仍可正常做其任务 |
| A05 | 多AU/观察者/伪造成员和控制字段 | 越权拒绝；无路径、密钥、消息、私有日志或检查点正文泄露 |
| A06 | 配置/任职/章程/连接版本改变 | 旧会话不能恢复旧权限；按现有规则创建新会话，保留历史 |
| A07 | CLI、网页、托管服务同时争用 | 一个AU只持有一个派发权；重复控制请求不产生重复服务或模型调用 |
| A08 | 正常停止、运行中停止、重启 | 等待本轮回执和检查点；进程退出与任务结束分开确认；身份/成果/累计预算保持 |
| A09 | 中断/网络结果未知/控制器崩溃 | 保留原回执及占用；查询/核对后接续，不自动重试不确定外部动作 |
| A10 | 托管服务达到预算/运行窗口边界 | 到限停派发；观察窗口重启不续额；外部服务无控制能力时不出现可执行按钮 |
| A11 | 实际React界面 | 桌面和320/390px可用，键盘与状态说明可读；断网和乱序不覆盖新实例数据 |
| A12 | 真实主机与真实供应商 | 在原公司完成授权调用、空闲等待、唤醒、重启/恢复和日志核对；与替身/工程完成分别记账 |

U-041验 A01–A06、A11及新增观察面独立复核；U-042验 A07–A11及运维权限复核。A12进入既有U-008/U-005/U-009/U-020，不给模拟或一次成功提升真实持续运行等级。实际持续窗口和预算在真实验收前按资源确定。
