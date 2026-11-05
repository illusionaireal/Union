# 057：S05 本地治理、撤权与责任交接

2026-11-05。用户授权完整 U-069 / S05 / 在线 #24，起点为 `rewrite/charter-v1` 的 `d9ff5ad23201ee0813707a00f65a0b0d9012a3ee`。依据 [S05 契约](../../specs/053-union-rewrite/s05-contract.md)、[plan §9](../../specs/053-union-rewrite/plan.md)与 [ADR-0006](../../docs/decisions/0006-charter-policy-adoption.md)，直接延续已交付 S01。

G01–G10 的受控工程、最终浏览器、安装候选及独立复核已经通过；主账与 Git/在线交付收据在完成后随本页记录。任务状态只由 `management/project.json` 拥有，本页记录具体证据。真实治理、AI 成果、用户实际验收和持续运行未由本片完成。

## 可用行为与边界

普通核心参与者可独立登记、登录、恢复密码，创建自己的准备态 AU；登记本身不授予旧组织、平台或其他 AU 权。`local_governance.v1` 支持单一当前治理者/最终决定方、明确保留事项、预先确认的超时继任或单主体超时退出、旧规则修章、撤权和责任交接。初始治理根不随接班改写，当前访问与原提交者回执查询分别授权。

人类内部记录用例贯通 Member、责任绑定、Work、有限 Mandate 再委托、本地尝试、文字提交和采用。每次行动与接受重验当前身份、任职、目标、Work、Charter、政策、授权祖先链及期限。撤权后的迟到文字只收存为 `not_adopted`，明确 `effect=evidence_only`，不能完成 Work 或覆盖已采用结果。交接保留原 Work、已完成归属、未完责任和在途历史。

一个 AU 事务关联当前状态、所有 Charter、完整命令摘要、审计和回执；`governance_origin` 保留原 state/Charter 字节，创建 payload/receipt 与采用不改。成功首次治理采用才升至 AU schema 2；合法初次规则拒绝可在 schema 1 保留原回执。认证 schema 0/1 仅通过停服工具显式升至 2。读取不迁移、不续期、不派发，不声称跨认证库/AU 库全局事务。

被测系统真实模型调用 **0**。只使用新建临时测试库，没有迁移真实 AU 或部署。测试脚本模拟人类的保留治理和内部业务劳动，外部工程代理完成实现及验证；这不是 AU 自主改善、真实人工成本度量、用户研究或真实业务治理证据。本地治理激活仍不启用模型、资源、对外承诺或 AI 自主业务；AI Execution 的实际 Agent Definition 绑定属于后续 S03。

## 契约与行为证据

| 契约 | 覆盖与落点 |
| --- | --- |
| G01 | `test_core_participants`、identity/upgrade/release：独立账号、无附赠权限、逐账号限流、owner 重置不删其他账号、稳定主体、auth 0/1 显式升级及回退 |
| G02 | `test_governance`：首次合法采用/激活、旧规则拒绝、未知/不完整配置、未确认后继；schema 1 读取不升级，初次拒绝仍可查原回执 |
| G03 | `test_governance_succession`、`test_governance_responsibility`：按旧规则修章，同一行动与接受处实际生效；正文不能自授权，初始根/原创建/Charter 历史不改 |
| G04 | `test_governance_succession`：独立确认正常接班、已确认超时继任、单主体超时退出、旧治理权不复活；当前/后继账号缺失显示不可用并禁止激活/行动 |
| G05 | `test_governance_responsibility`：内部 Work→授权→尝试→提交→采用；旧任职/目标/Work/Charter/policy/期限及跨 AU 反例；迟到内容与成果采用分开 |
| G06 | 同一生产命令的有限 A→B→C 再委托、撤父级传播、新行动及旧结果接受拒绝，无关 Work 继续 |
| G07 | 原 ID 责任交接、原任职失效、未完/在途/已完成历史保持；来源主体失去登录能力不阻止新治理者交接原责任 |
| G08 | `test_governance_persistence`：各采用阶段失败回滚、同 ID 去重/冲突、响应丢失后只查原请求、原回执与当前访问分开、完整命令及全部历史 Charter 损坏拒绝 |
| G09 | `test_governance_release`、实际安装候选：auth/catalog 与 AU schema 分别声明；旧候选不得选择/回滚/启动已采用 schema 2 的 AU；S01/legacy 正确行为保留 |
| G10 | React 正式行为测试、独立 UI 反例、真实 Chromium、固定 npm/Python 全量；最终浏览器包含全部 21 种命令和慢刷新反例，结果见下表 |

## 严格 TDD 与独立修复

以下日志保留真实缺口的 RED，未破坏已经正确的代码或测试制造失败：

| RED | 实际缺口与后续 GREEN |
| --- | --- |
| `red-g01.txt` | 普通参与者与显式身份升级缺口；`green-g01.txt` 40 项、最终 Python |
| `red-g02.txt` | 新治理采用/激活尚不支持；`green-g02.txt` 18 项及最终回归 |
| `red-g03-g04.txt` | 旧程序修订、普通接班与超时恢复/退出；`green-g03-g04.txt` 10 项 |
| `red-g05-g07.txt` | 责任/授权/再委托、行动/采用和交接缺口；`green-g05-g07.txt` 22 项 |
| `red-g08.txt` | 完整历史/命令一致性缺口；`green-g08.txt` 17 项 |
| `red-g09-corrected.txt` | 实际已采用 AU schema 未阻止旧候选；`green-g09-and-review.txt` 35 项。初次 `red-g09.txt` 还含夹具问题，不作为全部产品 RED 的依据 |
| `red-review-roles.txt`、`red-review-identity.txt` | 组合角色遮蔽、离任账号丢失后的责任交接、逐账号限流与后继可用性；最终选定 52 项及独立 75 项 |
| `red-review-initial-receipt.txt`、`red-review-null-identifiers.txt` | 初次版本拒绝丢原回执、可空 ID 破坏持久身份；最终选定 52 项及独立 75 项 |
| [UI TDD](ui-tdd.md) | 身份/版本预检、表单/回执/unknown，以及独立发现的提交后核验、缓存、登记恢复码和创建入口反例；对应正式 GREEN 与独立复跑 |

`green-review-roles.txt` 是一次失败的中间尝试，含辅助函数被局部变量遮蔽的两个错误，**不是通过证据**；命名按原执行记录保留。其根因已修复，最终选定及独立回归覆盖这两个交接路径。前期日志不代替最终结果。

[后端独立报告](review-backend.md)记录 1 项 P1、6 项 P2 的原反例、修复和最终 75 项验证；[UI 独立报告](review-ui.md)记录真实组件接缝反例、有效控制、修复复跑与浏览器证据边界。评审意见不单独授予切片完成或真实采用权限。

UI 的 2 项 P1、4 项 P2 已全部闭合：提交后的身份检查不会丢原请求，401/切换主体/撤销 AU scope 不复活旧投影，schema 2 保留创建入口，登记恢复码不被后台身份读取冲掉，预览关键文字可读。新增可读性门槛先在真实 Chromium 观察 RED；局部 CSS 修复后 32 组 / 88 次字号与对比度测量通过，最低对比度 7.127:1。

最终浏览器前的两类脚本问题独立保留：初次版本检查读了折叠详情的 `innerText`；后一次刷新只等 session 和已有连接提示，导致 v27 打开表单，页面/真实 GET 到 v31 后表单仍正确保留旧快照。后者经实际 GET/选项/版本复现，只修浏览器刷新 helper，等待本次 session、目标 AU 响应及该版本呈现，并保留 600ms 慢读取反例；没有修改产品来迎合脚本。旧 45 项成功、可读性 RED、刷新失败与最终 50 项 GREEN 的时序见 [浏览器说明](ui-browser.md)及独立 UI 报告。

## 最终验证记录

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| 后端选定回归 | 52 项，69.745 秒，exit 0 | `green-backend-reviewed.txt` |
| 后端独立复核 | 75 项，72.948 秒，exit 0；13 个实现文件摘要 | `review-backend.md` |
| Python 全量 | 525 项，520 通过、5 平台相关跳过，329.817 秒，exit 0 | `python-full.txt` |
| npm 完整检查及前端 | 最终 CSS 后 exit 0；14 文件 / 141 项前端、类型检查与构建；宿主管理 25 项、动作安全 9 项 | `npm-check-final.txt` |
| 实际 S05 / S01 / legacy 浏览器 | S05 最终 50 项 / 全部 21 种命令 / 45 次 POST；S01 30 项、legacy 71 项通过；S05 四宽度、88 次文字测量通过 | `ui-browser/checks.json`、`ui-browser/readability.json`、`browser-s01/checks.json`、`browser-legacy/checks.json` |
| 暂存源导出、实际构建/安装与库外运行 | 最终候选 79 文件 / 162 源摘要、实际依赖/导入/config preflight、9 项隔离导入、auth 0/1 升级/幂等/回退与 2 项治理烟雾通过 | `candidate-install.json`、`candidate-final-smoke.txt` |
| 安装后的完整相关回归 | 前候选 166 项，136.507 秒，exit 0，无跳过；最终候选仅 S05 CSS 不同，54 个 Python/随包脚本逐字节一致 | `candidate-backend-regression.json`、`candidate-installed-python.txt` |
| Aegis、主账与候选原管理工具 | bundle/check 通过；主账 record 与容量恢复后管理 25 项通过；精确暂存源使用原已提交管理工具 8 项及历史计划检查通过 | `aegis-check.txt`、`management-closeout.json`、`management-final.txt`、`candidate-management-final.txt`、`plan-final.txt` |

固定 Node **24.19.0**、Python **3.13.14**、Bun **1.4.2**，Python 显式 UTF-8。本机另一套 `~/.bun/bin/bun.exe` 实测为 1.3.13，不用于候选 preflight；采用实际核实的固定 Bun。modeld 没有代码变化，候选复用已核对 SHA 的 S01 构建，并逐项核对源摘要与 payload，不改宿主的预存子模块。

最终候选 archive SHA-256 为 `cd0c571691ddfaa2c7afb06a5e783625ac785df6ec875c730714a44a51819a11`；执行 166 项回归的前候选为 `76c8f675ec4c133edafcb45e92852d04bf3806756238dff1c92b1095677d1f55`。166 项没有在最终 CSS 包重跑；其适用范围由相同 Python/脚本字节及最终包自身安装、升级与烟雾检查支撑。首次隔离回归未显式添加 `-X utf8`，中文输出乱码，原日志保留在 `candidate-installed-python-initial.txt`；完整 166 项随后以 `-I -B -X utf8` 重跑通过，最终证据使用该次记录。

## 所有权、兼容与交付

新规则分别在 `domain/governance.py` 和 `responsibility.py`，应用在 `application/governance.py`，唯一治理持久化写入者为 `adapters/governance_store.py`。Console/HTTP 只装配。Catalog 原 creator 已退出当前 AU 授权判断，但保留原创建回执归属；旧 Engine/CLI/runner/model 路径继续拒绝 V1。legacy profile 有现存用户数据及回归，因此按声明兼容保留；后续逐用例完成身份/责任迁移并重绑调用者后才退役对应实现。

新增规则/应用/存储分别为 232/234/131/149 行，按实际职责分工，未引入双写、双派发、自动读迁移或通用规则框架。源代码复杂度在本片预算内；当前/历史权限分离与身份升级不作为可随意回退的临时补丁。摘要链只检测本地不一致，不能抵御整体改写程序与数据库的宿主。

完成前核对由 Aegis verification-before-completion 汇总：本片置信度 **B（受控工程）**；代码、实际执行的行为/浏览器/安装测试与独立反例支撑 G01–G10，未覆盖真实模型工作、真实用户研究、实体设备/屏幕阅读器和持续运行。ADR-0006 已回填身份/权限/持久化决定并同步正式基线；工作记录检查仅证明结构。下一高价值证据是 U-072 的真实模型与工具往返。用户最新六项路线质询及“真实另验”承接漏项见[一页近期交付路线](../../docs/NEAR_TERM_DELIVERY.md)，其中待采用的管理调整不冒称已实施。

仅协调者操作主账、在线卡和 Git；仅暂存本轮增量。保留 33 项任务开始前的修改/未跟踪条目，五个预存配置/管理文件哈希已核对未变。宿主未提交的管理适配器不是本次交付内容；最终主账记录已从暂存源导出，用原已提交管理工具独立校验通过。可维护源码、文档与 JSON 的空白检查通过；原测试日志中的行尾空格和空行按实际输出保留，不为格式化改写历史失败。

U-069 已通过统一适配器以 controlled 完成并释放租约，WIP 上限恢复 5；其余 75 张任务卡与起点逐项相同，原五项历史在制仍占满 5/5。没有用此结果升级产品里程碑或把“历史暂停”建议当作已实施。

Git/在线交付待受控验收完成后记录。本片完成后下一计划为 S02/U-072；真实模型/工具的目标与调用/费用范围按该片另定，不在 S05 自动启动。
