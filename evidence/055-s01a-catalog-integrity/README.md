# 055：S01a 旧目录与身份完整性检查点

2026-11-05，`rewrite/charter-v1`。本轮交付 S01a/T01–T04 的受控工程实现；U-066/S01 仍未完成。稳定 principal、V1 创建和入口隔离分别留在 S01b/S01c，未升级组织成熟度、真实业务、发布或持续运行证据。

依据为已采用的 [Main Chapter V1](../../docs/UNION_CHARTER_v1.0.md)（来源 `b2a30f3af4ad69a679c4860468d744dd285a0098`）、[PRD](../../docs/PRD.md)、[架构](../../docs/ARCHITECTURE.md)、ADR-0004/0005/0006 与冻结的 [S01 契约](../../specs/053-union-rewrite/s01-contract.md)。从交接 HEAD `36ec591458cde470771326335bb281eedf159321` 续接，没有重置工作区。

## 实现与兼容边界

`ai_union/adapters/au_catalog.py` 是目录定位与实际 AU 身份核对的共同只读入口。Console 的交互打开、列表、启动恢复、关闭，以及公司发现使用同一解析器；先核对服务范围、实际 AU ID、legacy profile、当前章程/资源/authority 和必要表列，再允许构造用于写入的 Engine。生命周期先验证整批目录，所以错误条目在后面时，前面的合法 AU 也不会被提前恢复或暂停。

会话范围检查先于对应 AU 的读取。无权访问的另一个坏 AU 不阻断受限会话读取自己的合法 AU。拒绝信息不包含其他组织名称、凭据或宿主目录；HTTP 使用原有 409/Rejected 边界。缺目录/库、未知 profile/schema、错误 ID、数据库链接或不完整状态不会被自动补建、注册、修复或迁移。

旧创建意图、目录分配、原 payload/receipt、同请求重放及 unknown 查询保留；`_create()` 与 `receipt()` 没有改写。原 controller_ref/company 版本、Console 的严格资源输入与 CLI 的较宽资源契约仍成立。合法 CLI 库允许尚无 `commands`；已存在的 `commands` 必须有恢复所需列。

## 契约与实测证据

| 契约 | 实际验证 | 证据 |
| --- | --- | --- |
| T01 | 原合法创建、同请求重放、改内容冲突、重启；原 payload/receipt 保留 | [原三项基线](legacy-baseline.log)、[新增测试](../../tests/test_catalog_integrity.py)、[全量](python-final.log) |
| T02 | A 错映射到 B：交互、启动、关闭在 AU 写入前拒绝；正确映射成功，后出现坏条目不先改前一个 AU | [首个真实 RED：5 个失败子例](red-mapping.log)、[首个 GREEN](green-mapping.log)、[目录/HTTP 最终回归](green-review-columns.log) |
| T02 边界 | 越界/缺失/链接/ID/profile/schema/不完整状态、章程和 authority；受限会话及 HTTP 错误无信息泄漏 | [边界 RED](red-boundaries.log)、[列表/权限 RED](red-list-authority.log)、[profile/存储 RED](red-profile-storage.log)、[HTTP 兼容](http-compatibility.log) |
| T03 | 原建库/登记失败 unknown 与中断 accepted 的恢复；原请求可查，不重建或自动重放，未登记目录保留 | [原基线](legacy-baseline.log)、[全量](python-final.log)、[安装后候选](candidate-installed-python.log) |
| T04 | controller_ref 初始 version=1；普通/company 初始 version=0；charter=1/policy=0；Console/CLI 资源范围不合并 | [HTTP/真实 CLI 测试](../../tests/test_catalog_http.py)、[相关 109 项](focused-python.log)、[安装后候选](candidate-installed-python.log) |

先运行原有三个正确的创建/unknown 行为，再添加首个错映射测试，观察未修复代码的 5 个真实失败，随后最小 GREEN 和重构。没有删除正确断言或故意破坏代码制造 RED。独立评审发现“表存在但缺少必要列”的反例后，补充缺列测试先观察 15 个失败子例，再修复；见 [评审 RED](red-review-columns.log) 和 [最终 23 项 GREEN](green-review-columns.log)。

| 验证 | 结果与覆盖 |
| --- | --- |
| `npm run check` | 主账记录更新和 [render](management-render.log) 后 [最终通过](npm-final.log)：管理/历史计划/行动安全、53 项前端、类型及构建。使用宿主已有管理适配器，不能据此称它已交付 |
| `.venv\Scripts\python.exe -m unittest discover -v` | [447 项，274.322 秒，OK，5 项平台跳过](python-final.log)。生产最终修复后执行；跳过为 Linux 执行位/锁语义及容器宿主场景 |
| `npm run test:workspace` | [最终 71 项，errors=[]，真实模型调用 0](workspace-browser-final-pass/checks.json)；[退出码 0 日志](workspace-browser-final-pass.log)，实际 Chrome 桌面与 320/390px、创建/重开/回执/默认切换/隔离/错误恢复及模拟 Harness 交付 |
| 候选管理检查 | 主账进展/租约最终更新后 [通过，8 项](candidate-management-final.log)。从 Git 暂存区导出独立源码，使用已提交的管理脚本与 package.json，未带入宿主未提交工具 |
| wheel 构建及独立安装 | [构建](candidate-wheel-build.log)、[安装](candidate-wheel-install.log)成功。新 adapter 实际进入 wheel；没有包含未跟踪的 attempt_audit/inference_retry/operating |
| 安装后实际行为 | [26 项通过，17.355 秒](candidate-installed-python.log)：从独立安装目录导入全部三个生产文件，字节匹配候选；在只放 tests/examples 的目录运行，CLI 子进程同样使用安装包 |
| 独立身份/持久化复核 | [评审记录](../../docs/reviews/2026-11-05-s01a-catalog-integrity.md)：23 项回归及 9 个晚出现缺列 AU 的独立探针通过；初始 R1 已修复，无范围内未解决的重要问题 |
| Aegis 工作记录 | [bundle/check 通过](aegis-workspace.log)。只证明工作记录结构和索引，不证明证据充分性、产品验收或运行时治理；空工作分类目录由宿主 helper 的 init 创建 |
| 候选归属与结构 | [核对通过](candidate-audit.log)：任务暂存归属、预存五文件字节、其余 75 卡/模块/里程碑、51 个新增/修改 Markdown 链接、原始日志字节和有限凭据模式检查。旧 STATUS 历史条目已有坏链接，不冒称全仓库链接均通过 |

固定工具链为 Node 24.19.0、npm 11.9.0、Python 3.13.14；Python 显式设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。Node 使用 `.union/tools/node.exe` 启动 npm CLI，避免宿主默认版本。所有 AU、HTTP 和模型替身均为私有临时测试数据。被测系统没有真实模型调用或部署；开发工具费用未在本证据中统计。

安装验证先用 `git checkout-index --all --prefix=<临时源码目录>/` 导出暂存候选，再 `uv build --wheel --python <固定Python> --out-dir <wheel目录> <临时源码目录>`，以 `uv pip install --target <独立安装目录> --no-deps <wheel文件>` 安装。测试目录只复制候选的 tests/examples，并令 Python 与 CLI 的导入指向安装目录。第一次验证夹具遗漏 examples/fixture.json，属于测试环境准备错误，保留在 [setup 日志](candidate-installed-setup.log)，补齐候选原夹具后上述 26 项通过。安装使用复制回退的性能警告不影响字节核对；没有改动项目 venv 的依赖。此处未验证包含 modeld 的完整部署包或真实发布。

## 浏览器验证器修正

当前 UI 与脚本在本轮开始时均是已提交代码，但脚本仍要求旧文案、直接填写折叠高级字段，并假定新增第二连接自动成为默认。现按已有 UI 展开高级设置，验证保存的 `response_format=agent`，明确选择第二默认后再测试切回；保留保存不调用模型、凭据不泄漏、原回执、错误恢复与隔离断言。

重复点击已有预览会与预览前 refresh 竞争；脚本现在提交已展示的当前预览。另有四处 `page.waitForFunction(async ...)` 把 Promise 当成真值：最小实测中，同步 false 在 300ms 超时，异步 false 在 4ms 就返回 false，见 [反例](browser-wait-predicate.log)。最后的交付检查因此曾在作业尚未完成时执行。改为有 30 秒期限、实际 await 数据布尔值的轮询；交付数量、工作终态、六次 SDK 用量断言全部保留，最终 71 项通过。未改 UI 产品代码或业务运行器。

独立复核另指出 R2：单次 evaluate 可越过循环期限。先 [实测 RED](red-browser-deadline.log)，再按剩余时间约束 Promise 并清理定时器；[四项探针](green-browser-deadline.log)与评审者独立四项探针均通过，最终完整浏览器再次 71 项通过。单次永久未决、迟到 true 与持续 false 会超时，按时变 true 正常成功。该超时只限制本地验证等待，不宣称远端调用已取消；R1/R2 均在原评审报告中保留并标明修复证据。

原失败分别保存在 [旧文案](workspace-browser/failure.json)、[重复预览](workspace-browser-final/failure.json)、[默认选择](workspace-browser-recheck/failure.json)、[异步等待](workspace-browser-verified/failure.json)。`workspace-browser-recheck.log` 的采集含 NUL，不能单独作为完成证据，该轮错误以 failure.json 为准。初次全量 `python-full.log` 为评审修复前的 446 项，只是历史；最终结果以 `python-final.log` 为准。

原始日志保留实际换行与 unittest 输出尾空格；目录内 `.gitattributes` 只为 `*.log` 禁用文本归一化和空白格式检查，不改写原始失败/成功内容。源码、测试和文档仍执行正常差异检查。

## Aegis 收口与剩余风险

要求与架构对齐：`aligned`。本轮落实已有 ADR-0005/0006 的目录边界，没有新架构决策。修复轨为身份/存储验证；退役轨为收口 Console 和 company 的分散目录打开路径。legacy 创建及执行仍因兼容契约保留，后续授权的 S01b/S01c 负责新 profile 的入口隔离和逐调用者替换。

复杂度收口：`within-budget`。新增 84 行、单一只读责任的 adapter；Console/corp 只接线，测试按边界分为两个模块。没有第二份身份事实、写者、迁移框架或回退。Console 既有混合职责仍是后续逐用例迁移的压力点，本片不声称其整体复杂度已解决。Aegis [工作记录](../../docs/aegis/work/2026-11-05-s01a-catalog-integrity/20-checkpoint.md)是方法与证据记录，不能替代主账或授予产品验收。

置信等级 B：目标与相关回归、真实浏览器及独立安装已验证。只读指 AU 业务记录不被校验事务修改，SQLite WAL/SHM 临时活动不是业务写入。没有全局跨 catalog/AU/文件事务，也不证明抵抗恶意宿主并发替换、硬链接别名或所有历史记录的语义损坏。启动锁释放仅针对目录/身份初始化失败；Gateways 构造仍在保护区之外。关闭拒绝会保留服务锁及原状态，不能解释为宿主已经关闭。

## 主账、协作与交付

唯一任务源仍是 `management/project.json`。本轮通过宿主现有统一适配器认领 U-066；为用户授权的一个实际执行增加容量，上限从 5 到 6，有明确历史理由。U-007/U-041/U-044 的 blocked 与 U-056/U-060 的 doing、原负责人/阻塞/历史保留。U-066 只记录 S01a 工程证据，保持 doing、completion=null；不能为恢复 5 而隐藏已开始工作。交接仅清除本会话 claim，保留 owner/started_at 与 WIP，未调用会退回 ready 的 release。

首次 Git 交付时，匿名 `/api/board` 返回 401，Process/User/Machine 均无 `UNION_KANBAN_KEY`，因此当时没有认领或更新 #20。用户随后提供本轮访问：按 [KANBAN.md](../../management/KANBAN.md) 读取实际 user.id，确认 #20 为无人认领的 ready/version 3；以当前身份 ZBOOK PATCH 认领为 progress 并补入分支、两个已推送提交及 S01a 验证/剩余范围，返回 HTTP 200/version 4。

后续逐字读回发现 Windows 原生 Unicode 参数传递丢失了两处范围分隔符；使用 ASCII 转义 JSON，仅修正该文本，按最新 version 再次 PATCH 返回 HTTP 200。最终独立 GET 读回 version 5、progress、实际负责人/分支/证据全文一致，活动卡仍只有 #19–#30，见 [带日期的在线收据](kanban-sync.json)。Python HTTP 客户端曾被 Cloudflare 1010 拒绝，接入说明指定的原生 curl 在相同授权、代理和正常 TLS 校验下成功；没有关闭 TLS 校验或保存凭据。密钥只经不回显的临时输入和子进程标准输入传给授权接口，未写入仓库、卡片或持久环境。

补同步仅追加文档、主账历史和证据。宿主管理 render/check [25 项通过](kanban-management.log)，导出暂存候选使用已提交管理工具 [8 项通过](kanban-candidate.log)，Aegis [bundle/check 通过](kanban-aegis.log)。生产与测试代码未变，复用上方最终回归，不将宿主未提交工具纳入交付。

项目范围与提交授权属于用户保留的治理决策；用户补充看板访问属于已完成的补救介入。工程子代理只做独立复核，不是产品 AU 成员。没有把开发对话、测试夹具或文档更新换算成组织自主改进。

只提交本轮源码、测试、证据和管理/交接增量。开工前的根配置、管理适配器、package.json、模型子模块和其他未跟踪资产均不纳入交付。下一轮经授权从 S01b/T05 续接，不关闭 U-066 或自动实施后续切片。

## Git 交付收据

实现提交为 `1384c0946526a4c76b7639e78419cd34adc8c692`，消息 `fix(rewrite): enforce S01a catalog integrity before AU writes`；父提交为用户提供的 `36ec591458cde470771326335bb281eedf159321`。本提交包含本轮 146 个源码/测试/文档/证据文件增量，预存编辑未暂存。

`git push origin HEAD:refs/heads/rewrite/charter-v1` 退出码 0；随后 `git ls-remote origin refs/heads/rewrite/charter-v1` 实际返回同一个 `1384c0946526a4c76b7639e78419cd34adc8c692`。实现提交推送读回时，本轮增量已全部提交；仓库整体仍有预存修改和未跟踪文件，不能称为干净仓库。未创建、切换或删除分支/工作树，保留交接分支供后续 S01b 使用，`dev` 未被改动。

本段及 HANDOFF/Aegis 的提交收据已通过 `4ba91cfd66f3b26ce23067a6631feea7905eb4ca` 补入同一分支，已推送并读回同 SHA，没有改变已验证的生产或测试代码。在该 Git 收据的时间点，在线 #20 尚未同步；凭据随后到位后的补同步结果由上方独立 HTTP 收据确认，不把 Git 推送本身当作在线更新证据。
