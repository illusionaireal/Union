# 056：完整 S01 核心身份、准备态创建与重开

2026-11-05。用户授权继续完成 UNI-020 / #20 / U-066；从 `219168dfd6e0325cc2950f7dc93fcb8daedff2f6` 续接 `rewrite/charter-v1`。**完整 S01a–S01c 的受控工程验收通过**：核心用户可创建准备态 AU，刷新、服务重启及普通登录后重开同一 AU；旧目录、回执和运行时兼容边界保留。任务状态只由 `management/project.json` 拥有，Git/在线交付另有本目录收据。

父契约为 [S01](../../specs/053-union-rewrite/s01-contract.md)，实施顺序见 [053 plan §8](../../specs/053-union-rewrite/plan.md)，编码前设计见 [ADR-0005](../../docs/decisions/0005-au-runtime-boundaries.md)。已交付 S01a/T01–T04 的原证据保留在 [055](../055-s01a-catalog-integrity/README.md)。

本轮仅在临时测试库实施升级、账户重置和故障注入，使用固定 Node/Python 与 UTF-8。被测系统真实模型调用 **0**；没有迁移真实 AU 或部署。这里证明准备态能力，后续自主业务/资源启用不属于 S01。

## 实现与验收映射

| 契约 | 已验证结果与证据落点 |
| --- | --- |
| T01 | legacy 合法创建、原请求幂等、同 ID 改内容冲突、重启后回执保持；`test_console` 及全量 Python。原 S01a 正确测试保留 |
| T02 | 错映射、越界、AU ID/profile/schema 不一致在交互、启动恢复、关闭的首次 AU 写入前拒绝；`test_catalog_integrity`、`test_catalog_http`、`test_core_entrypoints`。真实 symlink/junction 新旧创建反例由独立评审复验 |
| T03 | 存储/登记失败保留原请求及 unknown，不能重建或换 AU ID；`test_console`、`test_core_creation`、`test_core_creation_failures` |
| T04 | 原 controller/company 版本、CLI 与 Console 不同资源范围保留；`test_au_contract`、CLI/机制回归和实际 legacy 浏览器 71 项 |
| T05 | principal 稳定、旧 schema 显式升级、会话失效、原 payload/receipt 字节、失败回滚及写入后禁止旧备份回退；`test_core_identity`、`test_identity_upgrade`、`test_identity_release`。实际安装候选中执行升级并运行 133 项测试，见 `candidate-install.json` |
| T06 | 同名重置后新 principal 经真实 HTTP 无权读取旧 V1 AU/回执，原主体正常；`test_core_creation` |
| T07 | 客户端伪造治理根/profile/active 被拒，当前受信 principal 原子写入根与采用记录；`test_core_creation` |
| T08 | 意图、目录、AU 提交、最终登记各阶段故障保留原身份和字节；state/root/charter/采用记录使用一个真实 AU 事务；`test_core_creation_failures` |
| T09 | 跨主体重放/查询拒绝，同主体原请求不重验当前 data、不重复创建，改内容冲突；`test_core_creation` 与前端回执匹配测试 |
| T10 | 旧 Engine/CLI/runner/start/amend/workspace/model/连接测试拒绝 prepared V1；保留运行器句柄也先校验 profile；`test_core_isolation`、`test_core_entrypoints`，legacy 合法控制样本保留 |
| T11 | legacy/V1 混合列表、会话投影、冷启动和关闭按 profile 装配，无越权或 V1 写入；`test_core_entrypoints`、`test_core_creation_failures` |
| T12 | 实际 Chromium 创建→回执→刷新→服务重启→普通登录重开；断网、原请求查询、输入/焦点、四种宽度、200 字符名称；`browser-core/checks.json` 的 30 项、前端 70 项及独立反例 |

核心认证拥有 principal 签发，`identity_schema.py` 拥有 auth/catalog 初始化与显式升级。`domain/creation.py` 拥有纯规则，`application/creation.py` 是两种 profile 的唯一创建流程；catalog、legacy 与 V1 adapters 分别持有实际存储。AU state 拥有 ID/profile/治理根，目录仅作路由提示。V1 不生成 board.key，不调用旧 Engine 创建，不授予资源或派发业务。

## 严格 TDD 与发现修复

下表是实际观察的产品失败；修复后再执行相应 GREEN 和回归。原 S01a 首个错映射的 5 个失败及独立缺列的 15 个失败子例保留在 055，没有重写历史或人为破坏正确代码。

| 有意义的 RED | 缺口与最终覆盖 |
| --- | --- |
| `red-principal.log` | 账号没有稳定主体；`green-principal.log`、最终全量 |
| `red-identity-upgrade-corrected.log` | 5 个显式升级/启动拒绝缺口；`green-identity-upgrade.log`、实际安装升级 |
| `red-core-creation.log` | 新创建协议尚不支持；`green-core-creation.log`、HTTP/故障回归 |
| `red-core-isolation.log`、`red-retained-runner.log` | 7 个 profile/保留句柄失败及 runner 边界；`green-core-isolation.log`、`green-core-entrypoints.log` |
| `red-core-ui-command-corrected.log` | 普通创建仍走旧命令；`green-core-ui-command.log`、T12 |
| `red-core-review.log` | 创建分配越界及采用记录关联不足；`green-core-review.log`、独立真实链接反例 |
| `red-release-auth-review.log` | schema 弱校验和认证存储异常；`green-review-regressions.log`、独立 47 项 |
| `red-upgrade-receipt-review.log`、`red-schema-marker-review.log` | 升级回执投影失败、marker 缺损；对应 GREEN 和安装回归 |
| `red-core-compatibility-ui.log` | 兼容入口不可达、模型空页承诺错误；`green-core-compatibility-ui.log`、T12 |
| `red-core-ui-review-expanded.log` | 7 个身份/回执/恢复失败，同时保留 1 个合法同主体控制样本；最终聚焦 21 项及独立 9 项 |
| `red-core-preflight-cancel.log` | 用户取消身份预检后仍发 POST；`green-core-preflight-cancel.log` 的 21 项 |
| `red-core-name-browser.log` | 实际浏览器发现合法长名称被裁切；最终四种宽度内容检查及截图 |

其他原始 RED/attempt 日志保留过程诊断，部分包含夹具初始化、React act 批处理、旧文案或异步等待错误；不把这些准备错误计算为产品缺口。旧浏览器脚本只更新新入口的已采用行为，原模型/组织隔离/有限运行断言继续通过。

独立评审见 [完整报告](../../docs/reviews/2026-11-05-s01-core-creation.md)：后端 **47 项 / 54.082 秒 / OK**；前端正式聚焦 **21/21**、隔离反例与控制样本 **9/9**，实际 Chrome 正常/长名称四宽度通过。原发现均关闭，已审范围没有阻断项。`independent-ui.json`保留最终测试名称、状态与布局测量的脱敏投影。

## 最终验证

| 检查 | 结果 | 范围与原始证据 |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m unittest discover -v` | **481 项，281.564 秒，OK，5 平台跳过** | `python-full.log`；身份、权限、事务、CLI/HTTP、legacy 与发布相关回归 |
| `npm run check` | **退出 0；70 项前端通过** | `npm-check.log`；管理/视图、历史、动作安全、类型、测试和正式构建 |
| `node scripts/check_core_creation.cjs` | **30 项通过** | `browser-core/checks.json`；真实本地 HTTP/Chromium，1440/1024/390/320、键盘和恢复 |
| `npm run test:workspace` | **71 项通过** | `browser-legacy/checks.json`；回环模型替身，真实供应商调用 0 |
| 暂存候选导出→ZIP→实际安装→库外运行 | **74 个包文件逐项校验，安装后 133 项 / 76.117 秒 / OK，无跳过** | `candidate-install.json`、`candidate-installed-python.log`；明确包含升级工具，auth/catalog schema 1 |
| 最终主账、历史和候选管理检查 | **宿主适配器 25 项、候选原管理工具 8 项通过；历史结构检查退出 0** | `management-check.log`、`candidate-management.log`、`plan-check.log`；仅 U-066 改变，其他 75 项及模块/里程碑保持原值 |
| Aegis bundle/check | **通过** | `aegis-check.log`；只证明工作记录结构，不替代 T01–T12 或独立评审 |

工具链为 Node **24.19.0**、Python **3.13.14**；Windows 设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`，`UNION_PYTHON` 指向项目 `.venv\Scripts\python.exe`。宿主默认 PATH 的 Node 24.14.0 没有被用作本轮验证解释器。modeld 候选以 **Bun 1.4.2** 构建；核对固定 vendor HEAD 和记录补丁后，在导出的候选中重新构建，未改动工作区子模块。

安装源由 `git checkout-index` 导出，只有本轮所有的源文件进入暂存候选。隔离测试目录不含 `ai_union` 源码，导入路径实际指向安装目录。未暂存的管理适配器、包脚本和历史运行时辅助文件没有混入候选；候选用原已提交管理工具再做独立结构检查。初次 modeld 缓存锁只存在 CRLF/LF 字节差异，未覆盖旧产物，改用核对后的候选构建。

截图：[`prepared-1440.png`](browser-core/prepared-1440.png)、[`prepared-320.png`](browser-core/prepared-320.png)、[`create-mobile.png`](browser-core/create-mobile.png)。协调者另行查看桌面/320px 原图，信息与未激活状态可读；截图不是对所有设备或全部可访问性的证明。

## 边界、兼容与下一步

- 这是 **controlled** 验收，置信 B。S01 覆盖的 F01/F03/F09/F11/P15/F17 子集具备证据；不关闭完整 F09、真实组织成果、S08 发布或持续运行门槛。
- 治理根与资源计划已保存；执行规则、治理失能/继任/退出、授权资源和自主业务仍未激活。下一计划为 **S05/U-069**，之后才满足 S02/U-072、S03 的前置。本轮不继续实施这些卡。
- AU 内创建事务已验证；catalog、AU 库、文件不构成全局事务。unknown 保留原请求等待核对，本片不提供自动补登记、删目录重建或换 ID 重试。
- SQLite 只读业务查询不保证 WAL/SHM 无活动；受支持发布器和文件锁不防恶意宿主绕过。实体设备、屏幕阅读器、真实用户研究、跨主机持久运行均未验。
- legacy 创建/CLI/company 仍有实际调用者，按明确 profile 保留；纯规则和创建流程已收口到单一所有者。后续调用者迁移及兼容证据齐备后才退役 legacy，不增加双写或自动 fallback。
- 复杂度本片内已治理：Engine 837→811 行、Console 544→520 行，创建规则/流程实际迁出；新责任有局部 AGENTS。行数仅佐证，实际改进是消除重复规则与流程。Engine 其余多职责按后续用例迁移，未宣称整体重写完成。

Git 只提交本轮增量；根配置、管理脚本、子模块及历史未跟踪修改继续保留。主账通过现有统一适配器记录，该宿主预存工具自身不属于本次交付。在线卡只更新 #20，写前读取真实负责人/version，完成后保留脱敏读回收据。

提交前[范围核对](delivery-checks.json)确认：46 个源码/测试文件与已验证候选一致，安装目录 74 个载荷摘要正确，其中 35 个打包源码摘要与暂存源相符；Chapter V1 原字节不变，新增相对文档链接有效。预存 AGENTS 适配器说明未暂存，其他配置/工具原字节保留；仅 U-066 的任务记录改变。密钥精确匹配扫描为 0。
