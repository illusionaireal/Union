# S01：稳定核心身份、治理根与创建/重开契约

> 2026-11-13体验解释：本合同的稳定身份、受信创建、准备态、原请求/回执和legacy隔离继续有效。旧页面/兼容创建入口可达不再是新产品要求；U-111依[U-110](../../docs/product-design.md)接新默认入口，U-115退役旧UI。保存旧数据不要求维持旧导航，不读取时迁移；本条不改变现有领域/持久化协议。

日期：2026-11-05。工程任务U-066；要求来自PRD F01/F03/F09/F11/P15/F17，Chapter D-01、A-01/A-04、R-01/R-02、X-02(a)，以及ADR-0005/0006。本文件的 S01a–S01c 已实现并通过 T01–T12 的受控验收，见 [056 证据](../../evidence/056-s01-core-creation/README.md)；原 S01a 证据保留在 [055](../../evidence/055-s01a-catalog-integrity/README.md)。以下为冻结契约，实现不代表完整治理或业务自治已经启用。

## 1. 用户结果与实施顺序

用户在独立核心登录后，创建带明确初始治理主体的AU，刷新、重启后能安全重开同一个AU。新AU处于`inactive`准备态；目标、章程内容和资源计划可读取，业务自治、实际资源授予和外部承诺尚未启用。S05在启用前补齐受影响的最终决定方、保留事项、失能继任/恢复/退出及实际执行规则。

一个S01按三个内部步骤顺序实施，U-066只有全部验收后才能完成：

1. **S01a 兼容完整性**：修复旧目录映射/读取身份校验，保留原创建回执、幂等及unknown。它是可提交的部分工程结果，不是V1创建完成。
2. **S01b 稳定主体与V1创建**：显式升级核心身份存储，稳定principal绑定创建者/治理主体；单一创建意图连接分配、AU状态和目录登记。
3. **S01c 隔离及用户闭环**：旧执行/写入入口不能操作新profile；React/HTTP完成创建、回执、重开、失败与恢复，独立权限复核。

首片不迁移旧AU、不实现多主体治理/成员执行/外部资源使用。新AU未启用的范围须由后端拒绝并在界面解释，不能只禁用按钮。

## 2. 两个明确的兼容profile

| 范围 | 识别与写入规则 |
| --- | --- |
| `legacy_v0` | 已知完整旧存储，可能无显式profile字段；按旧授权/章程/版本工作。旧`create`对新request ID仍明确创建legacy AU，原调用者不被暗中升级 |
| `core_v1` | 新状态明确`runtime_profile: core_v1`和`schema_version: 1`；只有窄V1创建/读取用例可用，旧Engine/CLI/runner/模型配置写入拒绝 |

未知profile、未知schema、缺治理根或不完整状态拒绝，绝不回退legacy。profile在AU持久状态中有唯一权威，目录中的profile仅作路由提示，必须与实际状态复核。

当前React通用创建改发`create_v1`；小说`company`兼容入口和已有客户端仍发`create`，明确标为旧兼容范围。退出旧创建须另有实际调用者迁移和退役证据；本片不删除历史客户接口或双写同一AU。

## 3. 受信核心主体与显式升级

`owner_account`增加随机、不可复用的`principal_id`（UUID），与用户名、会话ID和platform_admin分开。服务端从经过验证的登录会话绑定principal；新V1不接受旧临时host board session、board.key或平台管理员身份替代principal。

- 首次设置新账户时生成principal；改密和使用有效恢复码恢复保留该ID。
- 新会话只在验证账户后签发，并绑定其principal。旧无principal会话在升级时失效，重新登录；不能在读取AU时按同名username补归属。
- `reset_owner`删除账户后再次认领产生新principal，旧AU根和创建意图仍保留原ID。账户重置不成为AU治理恢复后门，旧根无法验证时保持无权访问。
- 旧身份库采用显式、版本化的升级命令`python scripts/upgrade_core_identity.py --root <console-root> --services-stopped`，已随S01b交付。它取得console文件锁，要求操作者确认已停止、创建私有一致备份，再在一个catalog事务中补principal、扩展catalog字段和身份schema标记、清除旧登录会话。新脚本显式加入`release_package.py`的包清单；安装后的候选包也已验证可执行该升级。
- 新建空库直接创建新schema；已有旧库未经升级时，新版本写服务拒绝启动并提示升级步骤，不能在登录/读取时静默迁移。
- 升级重跑幂等、principal不变；迁移事务失败还原旧库。仅在没有升级后写入时允许用升级前一致备份回退；已有新身份/AU/回执后禁止用旧备份抹去新事实。候选包声明所需catalog/auth schema，代码采用/回滚必须检查兼容，不能让旧二进制写新schema。

catalog升级新增：`creations.profile`（旧行legacy_v0）、`creator_principal_id`/`allocated_au_id`（旧行null），`organizations.profile`路由提示及独立auth/catalog schema版本。旧行保留payload/receipt原文，不回填创建者、治理根或AU ID。同步调整`Console._create`、`Identity.setup`等裸`INSERT ... VALUES`写者，使用明确列名/新列值；以真实旧库升级后legacy创建和账户认领仍成功的测试保护兼容。

## 4. 请求与返回

### 4.1 保留的旧协议

现有`POST /api/commands`命令外层严格为`id, organization_id, base_version, kind, data`。`kind=create`要求有效全局board会话、`organization_id=null`、`base_version=null`，不要求platform_admin。

`data`必需`name,goal,board_name,charter,resources`，可选`company,controller_ref`。charter为原五字段；Console resources仅`max_calls`正整数1–10000和`timeout_seconds`正整数1–3600；bool不是整数。name/board_name非空且不超过200字符，goal/charter正文非空且不超过100000字符；外层长度、标识符约束沿用当前验证。

Engine/CLI原资源契约更宽，不在本片统一收窄或扩张，也不把其旧float费用字段采用为V1账本。company保持独立小说基准；controller_ref仅描述，初始state.version可能从0增至1。普通/company创建初始state=0、charter=1、policy=0，创建回执base_version仍null。

### 4.2 新创建协议

新增公开版本化命令`kind=create_v1`，继续使用`POST /api/commands`及相同五字段外层。`organization_id/base_version`必须null。`data`精确为`name,goal,board_name,charter,resources`；本片不接受company/controller_ref或客户端提供creator/governor/profile/active/authority_source。

name/goal/显示名称和基础字段校验同旧边界；board_name仅显示名称。五字段作为首片明确支持的章程输入子集保存，**不据此宣称V1治理程序已执行**。resources只是资源计划，不发出任何资源授予、预约或模型调用。合法外层请求先查询/鉴权原意图；存在则比较原payload并重放或返回409，不重新经过当前data验证器。仅新请求在意图分配前完成字段、类型、长度、结构化枚举纯校验；失败返回400，不新增意图。正文只做有界文本校验，不声称已检测任意语义冲突或未知自然语言规则。旧create保持历史顺序。

服务端把当前principal写入创建意图及`governance_root.creator_principal_id`和`governor_principal_id`；首片两者相同、根不可变。新AU保留唯一`state.id`及state/charter/policy版本；新增`runtime_profile=core_v1`、`schema_version=1`、`autonomy_state=inactive`、`resource_state=planned`和governance_root。不再生成新V1的board.key或使用board_hash作为管理权。

创建采用记录关联请求ID、principal、AU ID、profile、charter_version=1及时间；该记录证明准备态创建/根绑定，不证明自治规则、恢复程序或资源已启用。不增加与state/charter竞争的第二套治理版本数字。

### 4.3 回执与重开

回执外层继续`{receipt: ...}`，基本字段为`id,organization_id,base_version,kind,actor,created_at,status,message`。状态保留`accepted/succeeded/rejected/unknown`；accepted返回202，其余持久结果返回200。新成功文案明确“AU已准备；治理根已绑定，自主行动尚未启用”。

`actor`供审计展示，权限使用意图中的principal。旧创建回执继续`GET /api/receipts?id=<request-id>`；新创建使用`GET /api/v1/receipts?id=<request-id>`，两者都**不传organization_id**，包括unknown正文已有AU ID的情况。客户端按持久保存的原请求kind选择查询路径，不自动改查AU命令表。

重放create_v1或查询新回执时，先验证存储意图principal再读取内容/比较payload。新回执端点对不存在、legacy行或无权V1行均返回同一403 `not_authorized`；旧端点遇到core_v1行与缺失行一样返回原409“未找到此请求”，不能用旧接口绕过或探测新回执。旧无principal创建行只走原legacy访问规则。

新增`GET /api/v1/aus/<au-id>`用于core_v1重开，只读返回：

```json
{
  "protocol": "core.au.v1",
  "au": {
    "id": "org_example",
    "name": "示例",
    "goal": "用户目标",
    "version": 0,
    "charter_version": 1,
    "policy_version": 0,
    "runtime_profile": "core_v1",
    "schema_version": 1,
    "autonomy_state": "inactive",
    "resource_state": "planned",
    "governance_root": {
      "creator_principal_id": "服务器绑定的UUID",
      "governor_principal_id": "同一UUID"
    },
    "board_name": "显示名称",
    "charter": {},
    "resources": {"max_calls": 10, "timeout_seconds": 180}
  },
  "capabilities": {"read": true, "autonomous_business": false, "charter_enforcement": "not_activated"}
}
```

示例中的charter须返回已校验保存的完整五字段；示意UUID不是实际响应值。不得返回凭据、账户恢复码、原始私有日志或宿主路径。`/api/session`组织列表按principal过滤core_v1并提供profile用于路由；旧组织列表仍按旧会话范围。没有新协议支持的服务，界面提示版本不兼容，不自动改发旧create。

会话投影新增 `core_protocol: "core.au.v1"` 与 `principal_id: <当前受信UUID或null>`；无主体的宿主会话仍可使用原兼容入口，不能创建或读取 V1。组织项精确增加 `profile: legacy_v0|core_v1`。前端必须同时核对协议和主体后启用普通 V1 创建；缺协议时保留输入并提示服务版本不兼容。

重开校验请求AU ID、目录账ID、实际state.id、profile/schema和治理根一致，并核对有效principal。目录解析必须位于服务的organizations根下，拒绝越界、错误映射和不完整状态，不自动修目录/补根。旧`Console.engine`同样补ID/目录完整性，不能错开另一个AU。

### 4.4 错误分类

| 边界 | 旧协议保留 | 新V1结果 |
| --- | --- | --- |
| 未认证 | 原401 | 401 `not_authenticated`，不读取/分配AU |
| 越权或跨principal | 现有403规则 | 403 `not_authorized`；回执/重开不存在与无权使用同一外部结果，不泄露他人资料 |
| JSON/外层/类型错误 | 原400；现有部分Rejected为409不统一改码 | 400 `invalid_request`，不分配资源 |
| 同ID改内容 | 原409 | 有权访问原意图者得到409 `id_conflict`，原数据不变 |
| 错配ID/未知profile/schema | 原Rejected按现有409映射 | 409 `incompatible_state`；拒绝修改，无fallback |
| 已分配后的确定性拒绝 | 原领域校验失败仍rejected持久回执/200 | 请求纯校验已在分配前完成；分配后发现已有目录等确定存储状态冲突才保存rejected/200，原因可读 |
| 存储暂不可用 | 原503或可持久unknown/200 | 能保存则unknown/200，无法保存则503 `storage_unavailable`；保留原ID供查询 |
| 请求V1业务写入/启动 | 新profile不属于旧协议能力 | 409 `unsupported_capability`，无状态、资源、外部副作用 |

新错误体为`{error: <可读说明>, code: <上述稳定代码>}`，由V1类型化错误投影；不扩大旧文本匹配错误映射的变更范围。HTTP 200表示有回执，不自动表示成功。

## 5. 持久顺序与故障恢复

共享一个创建应用用例拥有原请求、分配及最终登记；按明确profile委托legacy或V1状态存储，不能让新旧路径各自创建同一个请求。

1. 验证会话、外层及请求范围；在catalog锁/事务中查原ID，按profile及principal鉴权。已有请求先比较原payload并返回原回执或409，不重验data；只有不存在的新V1请求才做全部data/charter/resources纯校验，并持久保存规范化请求、principal、预分配AU ID、确定性目录和accepted回执，然后做文件操作。规范化遵守现有`encoded`的对象排序/数组顺序语义，不改历史payload；旧create保持其意图后校验的历史顺序。
2. 检查确定性目录不存在并安全创建。legacy保留key→Engine.create等原顺序；V1没有board.key，使用独立窄存储。V1初始状态、治理根、charter v1、创建审计在**同一个AU数据库事务**中写入。
3. 在catalog事务中登记AU和完成回执；directory/profile是路由提示，AU ID/profile必须与实际存储匹配。assets等文件步骤不与两个数据库假装全局原子。
4. 在任一步中断时保留意图、目录和已写字节；能保存则unknown，重启将遗留accepted改unknown。原请求查询保留，重试返回原结果；不自动补登记、删除、重建或创建另一AU。
5. 没有完成最终登记的AU不出现在正常可用列表；即使文件存在也不能通过猜ID取得权限。后续人工/受控核对有单独权限和审计，本片不提供“换个ID重试”捷径。

此顺序是跨存储可核对流程，不承诺跨库/文件原子事务。旧回执在首次分配catalog就失败时可能无可查行；503须说明保留原ID核对，不能伪造持久unknown。

## 6. 所有者、调用者和旧入口隔离

| 责任 | 本片目标文件/边界 |
| --- | --- |
| 身份与catalog升级 | `identity.py`、`scripts/upgrade_core_identity.py`及候选包schema兼容检查；主体由认证所有者签发，AU不自己创建账户 |
| 创建纯规则/状态构造 | 实际迁入`ai_union/domain/creation.py`，不依赖Console/Engine/SQLite/Harness；移出的旧校验由兼容包装委托，避免复制规则 |
| 创建应用所有者 | `ai_union/application/creation.py`：意图/顺序/回执与profile选择；只定义本用例实际需要的存储契约，无通用端口框架 |
| V1窄存储 | `ai_union/adapters/core_au_store.py`：创建/只读，不导入或调用旧Engine；legacy存储保留Engine而受应用用例统一调用 |
| 入口/投影 | `console.py`/`server.py`绑定受信身份、调用用例、投影回执；React身份/命令/API层读取profile及能力 |
| 旧运行时边界 | `engine.py`构造/打开入口识别profile并拒绝core_v1；未知/不完整不当作legacy，不提供任意`allow_v1=True`通行开关 |

目录和局部AGENTS只在实际迁入上述代码时创建。本片不把其余Engine逻辑搬到空壳服务。所有旧入口必须验证：`cli.py`、`runner.py`、Engine `_board/apply_decision/_reserve`、allow_paused连接测试、workspace、模型管理/采用、修章及直接SQL写者不能触达core_v1。Engine构造拒绝是主边界；直接SQL拥有者必须显式遵循profile分流并由测试保护。

Console启动恢复、组织列表、session_info、关闭/维护循环必须统一使用**先只读核对ID/目录/profile、后按profile装配**的解析入口；不能先直接按catalog.folder开Engine并写恢复/暂停。错误映射到另一合法legacy AU也要在首次写入前拒绝，不能只在交互重开时检查。准备态V1不因启动/关闭而被旧Engine改写；损坏记录给出诊断并保留，不以跳过完整性校验维持运行。V1读取用独立只读事务，旧snapshot/修改入口明确拒绝新profile。

## 7. 严格TDD与验收矩阵

TDD Route: strict。下列验收已按真实 RED → 最小 GREEN → 重构回归执行；具体测试、原始失败与最终结果见 [056 验收映射](../../evidence/056-s01-core-creation/README.md)。已有正确测试保留，没有故意破坏实现制造 RED。

| ID | 必须观察的行为 | 测试落点 |
| --- | --- | --- |
| T01 | 旧合法创建、同请求、改内容、重启仍正确 | 保留`test_creation_is_durable_and_does_not_overwrite`及相邻console测试 |
| T02 | 错误目录映射/越界/实际AU ID不一致拒绝，正确重开成功；启动恢复/关闭同样在写入前拒绝错映射且不改另一合法AU | 新console/http及服务生命周期行为；源码确认的缺口先实测RED |
| T03 | 原存储失败/登记失败unknown可用原ID查询，不重建 | 保留`test_creation_storage_failure_is_unknown_and_not_replayed`、`test_creation_registration_failure_keeps_unknown_receipt_queryable` |
| T04 | 旧controller_ref版本与company、不同Console/CLI资源范围保留 | `test_au_contract`、console/机制/CLI相关回归 |
| T05 | 身份升级幂等、正常恢复保留principal、旧会话失效、迁移失败回滚；升级后legacy创建/认领成功；安装包含升级工具且不兼容激活/回滚拒绝 | 新身份/升级/发布包测试，真实临时数据库和安装后的候选包而非只mock返回值 |
| T06 | 同名重置后新principal不能读旧V1 AU或回执；原principal正常会话可读 | 身份+HTTP跨边界测试，不能只测对象相等 |
| T07 | 客户端伪造root/profile/active拒绝；默认服务器principal可靠落盘 | V1创建、HTTP正常及越权反例 |
| T08 | 根/charter/审计同事务；在意图/目录/AU提交/catalog登记各处失败不形成可运行空壳 | 故障注入+重启，核对原意图、AU ID、unknown与字节/条数 |
| T09 | 跨principal重放/查询被拒；same principal同请求不重复、改内容冲突 | catalog/HTTP持久行为 |
| T10 | prepared V1经旧CLI/runner/start/amend/连接测试/workspace/model管理均拒绝且资源/文件/外部调用不变 | 真实入口成对测试；legacy合法控制样本仍成功 |
| T11 | 服务启动/关闭、列表/观察可混合legacy与V1且无越权、无V1副作用 | console/identity/http重启集成 |
| T12 | React创建→回执→刷新/重启登录→重开；未激活提示、断网原请求查询、旧输入保留 | 实际浏览器，桌面/320/390、键盘及命令提供者测试；0真实模型调用 |

执行：相关Python模块和新增测试先局部RED/GREEN，再`npm run check`、`python3 -m unittest discover -v`、`npm run test:workspace`及升级/发布相关测试。Windows显式UTF-8。权限/身份/持久化独立复核后才采用；全T01–T12有证据才关闭U-066。

首片不要求真实模型账户或外部部署。它交付受控准备态能力；只有S05/S02/S03等满足其启用条件后才可声明V1自主工作，不能用S01的成功回执代替完整治理与真实闭环。
