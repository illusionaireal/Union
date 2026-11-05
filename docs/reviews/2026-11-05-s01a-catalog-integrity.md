# S01a 目录、身份与持久化独立复核

首次复核发现一项重要问题 R1，协调者已修复，独立复验通过；当前评审范围内没有未解决的重要问题。本文保留原发现及解决证据，是咨询式工程复核，不授予合并、部署、U-066 完成或 V1 符合性结论。

## 发现

### R1：重要——表名存在不足以确认完整 legacy 存储（已修复并复验）

- 位置：首次送审的 `ai_union/adapters/au_catalog.py:14`–`15`；后续写入位置为 `ai_union/console.py:55`–`62`、`539`–`541`。
- 分类：`Implementation Drift`，`scope: both`。S01 契约 §2、§4.3、§6 要求拒绝不完整状态，且在生命周期 AU 写入前校验；首次送审的解析器只验证核心表名，未验证这些表供现有读取/写入者使用的必需列。
- 真实反例：在临时 Console 中正常创建 AU，原 `engine()` 和 `snapshot()` 均成功。关闭服务后保留 ID、profile、state、当前章程和 meta，仅执行 `DROP TABLE events`、`CREATE TABLE events(data TEXT NOT NULL)`。将暂停状态设为 false 后重启 Console：重启和 `engine()` 仍接受该 AU；`snapshot()` 随后抛出 `OperationalError: no such column: consumed`；`close()` 又将该损坏 AU 的暂停状态从 false 改成 true。
- 影响：不完整数据库被当作已确认兼容的 AU 装配；用户直到后续读取才得到存储错误，生命周期仍能修改它。这与已有“整个表缺失则拒绝”的行为不一致，也使“已验证完整旧存储”的声明过宽。
- 建议：在同一个只读解析事务中校验必需核心表列；已存在的 `commands` 也应校验恢复/回执所需列。合法 CLI AU 可以没有 `commands`，不能因此误拒。覆盖 open、startup、close，加入后一个 AU 缺列时前一个合法 AU 不先被恢复/暂停的反例；保持原合法存储和 CLI 范围通过。
- 状态：首次发现时未解决；经协调者补充严格 RED/GREEN 后，评审者已复核最终代码、重跑回归及独立反例，现为已解决。

独立临时库探针的实际输出：

```text
valid_open: True
valid_snapshot: True
incomplete_events_open: accepted
incomplete_events_snapshot_error: OperationalError no such column: consumed
before_close_paused: False
after_close_paused: True
```

该探针只操作 `TemporaryDirectory` 内的新库；没有读写实际 AU 或保存私有数据。

最终修复位于 `ai_union/adapters/au_catalog.py:11`–`27`：`LEGACY_TABLES` 定义现有核心表必需列，在原只读事务中读取 `PRAGMA table_info` 并验证；`commands` 仅在已存在时检查 `id/payload/receipt`。必需列与当前 `Engine.create()` 的实际表一致，没有要求新 V1 Schema 或改变旧 CLI 创建契约。

协调者的 `red-review-columns.log` 保存 events/runs/commands 缺列的 15 个真实失败，`green-review-columns.log` 保存随后 23 项通过。评审者再次独立运行这 23 项，全部通过（24.536s）；又在独立临时库中把损坏 AU 放在目录最后，对 events/runs/commands × open/startup/close 执行 9 个探针，全部在 AU 写入前拒绝，前一个合法 AU 和后一个损坏 AU 的数据库逻辑内容及非 WAL/SHM 文件均保持不变：

```text
events/open: rejected=True, both_unchanged=True
events/startup: rejected=True, both_unchanged=True
events/close: rejected=True, both_unchanged=True
runs/open: rejected=True, both_unchanged=True
runs/startup: rejected=True, both_unchanged=True
runs/close: rejected=True, both_unchanged=True
commands/open: rejected=True, both_unchanged=True
commands/startup: rejected=True, both_unchanged=True
commands/close: rejected=True, both_unchanged=True
late_malformed_matrix: 9/9 passed
```

## 评审身份、范围与依据

评审日期：2026-11-05。评审者：Codex 独立工程子代理 `/root/s01a_identity_review`。这是工程工具身份，不是产品 AU 成员、治理主体或任务主账所有者。

评审范围为 `working-tree`；分支 `rewrite/charter-v1`，基线与实际 HEAD 均为 `36ec591458cde470771326335bb281eedf159321`，送审目标 `WORKTREE`。生产范围仅 `ai_union/console.py`、`ai_union/corp.py`、`ai_union/adapters/au_catalog.py` 及该目录 AGENTS；测试范围仅 `tests/test_catalog_integrity.py`、`tests/test_catalog_http.py`。其他开工前修改、未跟踪资产和模型子模块不属于本次评审交付。

最终复验所读生产文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `ai_union/console.py` | `c7d3007731f3291bba70e56aaf7a001d49f11bf2cb54f6bbacdc3093bab93683` |
| `ai_union/corp.py` | `4c43b4c6d8bfeb107251996fd308a29ebf528864fd71cd198921579c6544fba2` |
| `ai_union/adapters/au_catalog.py` | `005dfc4dd9871b9d8f9b06cfbbca7c09a494fd34bb4aff18ceb403d197cd832b` |

使用已采用 Main Charter V1 来源 `b2a30f3af4ad69a679c4860468d744dd285a0098`，读取根 AGENTS、当前 README/PROJECT/STATUS/HANDOFF/DEVELOPMENT 入口、采用记录、相关 D-01/A-01/R-01/R-02/X-02 条款、PRD F01/F03/N03、ARCHITECTURE、ADR-0005/0006、CONTEXT、053 plan/tasks/追踪表和完整 S01 契约。按 `aegis:requesting-code-review` 的 findings-first 流程复核；HTTP 错误/恢复使用 `aegis:ui-ux-governance` 的证据边界，交接声明遵守 `aegis:verification-before-completion`。

仅评审 T01–T04/S01a：目录兼容完整性、原创建/幂等/unknown 和旧 controller/company/资源契约。S01b 稳定 principal、V1 创建与升级，以及 S01c 旧执行入口隔离和新用户闭环均未纳入完成要求。未把 legacy_board 当作所有未来 AU 的唯一治理形式，也未把显示名称/controller_ref 当作治理授权。

## 已核对的结果

- `Console.engine()` 先验证会话与组织范围，再查询目录和读取 AU；`session_info()` 先过滤受限会话的组织，未因其他无权 AU 的坏映射而读取它。新增 HTTP 测试验证了错误映射返回 409、无其他 AU 名称/凭据/宿主路径泄漏，并保留合法 AU 的可读性。
- 目录的权威是定位关系，实际 AU 数据库拥有 ID/profile。解析器拒绝组织根外目录、ID 错配、未知 profile/schema、不完整顶层 state、缺失当前章程或 legacy authority，以及 R1 所列必需表列缺失；目录 profile 提示必须匹配。Windows 实际文件 symlink 反例在两次独立执行中均通过，未跳过。
- 当前所有读取 catalog folder 后构造 Engine 的消费者已收口到 `Console._catalog_engine()` 或使用同一 `legacy_directory()` 的公司发现。交互、列表、启动和关闭之间未另设容错回退。启动/关闭先收集并验证整批 Engine，再进入 AU 恢复/暂停写事务；晚出现坏映射和晚出现缺列表的反例均已验证。
- `_create()`、`receipt()` 和原分配→建库→登记顺序未修改。原 payload/receipt、创建 unknown、原请求 ID 查询、未登记目录保留、重启不重建已由新旧相关测试覆盖；没有添加跨 catalog/AU 库/文件的全局事务承诺。
- 公司发现保留原创建请求成功回执与目录登记比对，移除了仅为检查 ID 而调用 `Engine.state()` 写事务的旧路径。controller_ref 初始 version=1、普通/company 初始 version=0，charter=1/policy=0，以及 Console 与 CLI 不同资源范围均在独立测试中通过。
- `adapters` 中已有真实目录解析责任和局部 AGENTS；没有空壳领域服务、第二个状态写者或迁移框架。既有 ADR-0005/0006 足以覆盖本次边界，无需为该局部修复新增 ADR。保留 legacy 入口的原因及退出条件仍由 S01b/S01c 和后续实际调用者迁移拥有。

## 实际验证与限制

所有独立 Python 命令使用 `.venv\Scripts\python.exe`，设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、`PYTHONDONTWRITEBYTECODE=1`，使用 `-B`。评审者没有修改实现、测试、主账、看板或 Git。

| 实际执行 | 结果 | 所证明的范围 |
| --- | --- | --- |
| `python -B -m unittest tests.test_catalog_integrity tests.test_catalog_http -v` | 22 tests，18.663s，OK，退出码 0 | 首次送审代码的新增目录/身份/生命周期/HTTP/CLI 兼容场景 |
| 临时合法 AU→缺列 events→重启/打开/读取/关闭探针 | 退出码 0，观察到上方 R1 反例 | 证明现有绿色测试尚未覆盖必需表列缺失 |
| 修复后重新运行同一 unittest 命令 | 23 tests，24.536s，OK，退出码 0 | 最终代码对新增缺列场景及原目录/HTTP/CLI 场景的回归 |
| 损坏 AU 位于目录最后的独立缺列矩阵 | 9/9 passed，退出码 0 | 三种缺列表在 open/startup/close 均拒绝，两个 AU 均未改写 |
| 只读导入 setuptools discovery/config 检查 | `ModuleNotFoundError: No module named 'setuptools'`，退出码 1 | 当前固定 venv 无该构建依赖；没有因此安装依赖或改动环境 |

已阅读协调者保存的 legacy-baseline、red-mapping、red-boundaries、red-list-authority、red-profile-storage、focused-python、http-compatibility 和 refactor-green 日志摘要。它们分别支持原三个正确行为先通过、真实新增缺口先失败、109 项相关回归及 22 项重构回归通过；不把这些日志解释为全量产品验收。

打包静态核对：`pyproject.toml` 的 setuptools.find 使用 `include = ["ai_union*"]`，未关闭 namespace 包发现；当前运行时导入由上述测试覆盖。`scripts/release_package.py:78`–`82` 仅从 `git ls-files` 收录 `ai_union/` 下 Python 文件，因此新 adapter 必须进入候选的受跟踪文件集。评审者未实际构建安装包；候选包与候选管理检查、全量 npm/Python 及实际浏览器结果由协调者独立提供，本报告不代替这些验证。

只读保证限定为 SQLite 只读/query_only 事务不改 AU 业务记录；WAL/SHM 的临时文件活动不等于业务写入。路径解析、SQLite 检查和后续 Engine 事务之间没有文件身份固定或全局锁，不证明能抵抗恶意宿主并发替换、硬链接别名或 TOCTOU；也不证明跨库原子性、所有历史业务记录的语义完整性或新 profile 的直接旧 Engine 隔离。

目录验证失败后的启动锁释放已由测试证明。`Gateways` 构造仍位于新增 `try` 之前，不能据此外推所有启动故障均释放锁。关闭拒绝时保留服务锁和原状态，不是已完成宿主关闭的证明。这里的只读核对也不执行自动修复或自动迁移。

最终咨询结论：R1 已修复并独立复验，S01a 身份/持久化范围内未见未解决的重要问题，可供协调者结合最终全量、浏览器和候选检查证据评估本检查点。置信等级 B：目标与相关回归已验证，上述文件并发替换、完整业务语义及发布证据仍有明确边界。此结论不关闭 U-066，不证明稳定核心身份、完整 V1 创建、真实模型/业务自治、发布或持续运行。

## 追加复核：现有浏览器验证器

2026-11-05，协调者追加授权只读复核 `scripts/check_workspace.cjs` 的验证器修复。评审身份仍为 `/root/s01a_identity_review`；生产 S01a 三文件未变，本段不扩大到新产品行为或 S01b/S01c。

### R2：次要——轮询期限未覆盖单次异步读取（已修复并复验）

首次追加送审时的位置为 `scripts/check_workspace.cjs:19`–`28`。当时 `waitForData()` 在每次 `page.evaluate()` 前检查 30 秒期限，但没有约束该次异步读取；一个迟迟不返回的 fetch/Promise 可以越过期限，甚至使测试一直等待。评审者从实际脚本提取该 helper，仅将 `30000` 缩为 `300` 做有界浏览器探针；异步谓词在 600ms 后返回 true 时，helper 仍在 608ms 成功返回。它当时是轮询窗口，不是完整操作的硬超时。

原建议为按剩余期限约束单次 evaluate，并验证永不返回及迟到 true 都超时。协调者已采纳：最终 `waitForData(predicate, argument, timeout = 30000)` 对单次 evaluate 使用剩余时间的 `Promise.race`，在 `finally` 清除 timer，拒绝过期后得到的 ready，且轮询间隔也不超过剩余期限。默认四个业务验证调用仍使用 30 秒；可选 timeout 用于有界验证。局部等待超时不证明远端调用已取消，异常继续走原浏览器/测试宿主清理流程。

协调者 `red-browser-deadline.log` 保留原 helper 在 300ms 期限下等待 600ms 的 true，623ms 仍接受的真实反例；随后 `green-browser-deadline.log` 四项通过。评审者再次直接提取最终 helper，不再改写常量，传入 `timeout=300` 独立运行：

```text
async_false: timeout, 307ms
late_true: timeout, 300ms
never_resolves: timeout, 302ms
eventual_true: passed, 2 polls, 112ms
independent_deadline_probes: 4/4 passed
```

本次 Node 命令退出码 0，`node --check scripts/check_workspace.cjs` 通过。R2 已解决。最终送审验证器 SHA-256 为 `f651d247e07a13c9871ad623dbf07d0af404d29f740a92fd5a65523410c381e3`。

### 等待证据与断言有效性

使用固定 `.union\tools\node.exe`、仓库 `playwright-core` 1.64.0 和独立 headless Chrome 页面重现；没有启动业务服务、调用模型或修改验证器。此前原 helper 的缩时仅存在于探针内存中，初次探针输出保留如下：

```text
sync_false: TimeoutError, 320ms
async_false: returned false, 7ms
helper_async_false_300ms: timeout error, 330ms
helper_eventual_true: 2 polls, 149ms
helper_true_after_300ms_deadline: returned true, 608ms
```

前两项独立确认 `browser-wait-predicate.log` 的根因：本机固定 Playwright 的异步 `waitForFunction` 将 Promise 作为已满足条件，等待其值后可能直接返回 false。新 helper 对 `page.evaluate` 的完成值做判断；四处调用仍使用原状态条件，且终态后保留工作交付、实际成果、调用次数、用量和错误断言，修复了提前断言的问题。

界面对应核对结果如下，相关组件相对 HEAD 无修改：

- `ModelConnectionFields.tsx` 的高级字段位于默认关闭的 `details` 内，先展开后填写符合现有界面；未删去字段保存验证。
- `model.ts` 当前固定保存 `response_format: 'agent'`；以保存结果替代过期中文文案断言仍检验普通模型/工具配置，并继续断言没有输出 Schema 选择器和无模型调用。
- 已有默认连接时，新连接的 `bind_default` 默认不勾选。验证器现在明确勾选第二个连接为默认，再切回第一个；增加了默认选择实际发生的断言，没有只检查按钮存在。
- `CommandForm` 在表单变更时清空预览，并在提交时校验版本/组织。第一处已显式预览并检查密钥不外泄，之后 helper 直接提交该预览；其他未预览的调用仍先预览。避免 helper 再触发一次异步刷新符合当前交互，没有绕过预览或删除秘密检查。

评审者运行 `node --check scripts/check_workspace.cjs`，退出码 0；阅读并解析协调者的 `workspace-browser-pass.log` 和 `workspace-browser-pass/checks.json`，71 项通过、`errors=[]`、`simulated=true`、`real_model_calls=0`。代码使用临时服务和 127.0.0.1 模型替身，保留最终两成员交付两份成果、6 次 SDK 请求与用量对应、故障不自动重试以及浏览器/宿主无未捕获错误的断言。这是现有受控工作区回归，不是新 V1 自治或真实模型证据；评审者没有声称独立重跑完整 71 项。

同时补读协调者最终证据：`python-final.log` 为 447 tests/274.322s、5 skips、OK；候选 wheel 构建日志明确收录 `ai_union/adapters/au_catalog.py`，构建和安装完成，`candidate-installed-python.log` 为 26 tests/17.355s、OK。这些补足了主文当时尚待协调者提供的相关证据，仍与评审者亲自执行的 23 项和 9 个反例区分。

追加咨询结论：验证器主要修复与现有 UI、实际等待缺口一致，没有靠删减交付或调用断言取得绿色结果；R2 也已修复并独立复验，当前未见未解决的证据有效性阻断。最终 helper 修改后的完整 71 项复跑、npm/管理/候选文档和 Git 收口仍由协调者记录；此前 71 项正向结果与这次四项超时探针分开保留。
