# U-103 / #57：外部调用者与 V1 公开契约审计

2026-11-11（北京时间）。被审源码固定为
`f5996086d89c72bc16e363b1e8c69675504c1a69`；不包含原作者尚未交付的 U-092
候选或普通 checkout 的 U-086 改动。实施 actor 为 Codex 工程审计会话
`01a1c70f-f9aa-7891-b9d7-031153852447`；在线成员为
`codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`，均不是产品 AU 成员。

## 裁定与范围

在本次仓库输入中，**没有检出平台或外部业务管理调用者绕过公开契约，直接读写
V1 AU 私有表的实际调用链**。不据字符串命中虚构迁移卡，也不据此宣称 A-04、
P-07 或整个 S11 已完成。独立客户端的完整黑盒验收仍属 #55/#56，核心独立使用
仍属 #58，父 #30 的验收保持；新体验与旧前端退役分别归 #64–#69。

这是当前源码与已有行为保障的独立核查，不是对私有平台仓库、已部署外部工具、
任意动态程序或宿主文件权限的全面安全审计。未运行真实模型、部署或身份维护
命令，没有新增/移除 AU 权限。合法 legacy 路径仍属历史能力，不成为新 UX 要求。

依据为 [Charter](../../docs/UNION_CHARTER_v1.0.md) A-01/A-04、P-07、S-03，
[ADR-0005](../../docs/decisions/0005-au-runtime-boundaries.md)、
[S01 契约](../../specs/053-union-rewrite/s01-contract.md) 及
[当前产品审计](../../docs/reviews/2026-11-11-kanban-charter-product-audit.md)。
粒度为一个约 2 小时的只读审计结果；真实前置只有已完成 #20。在线 #57 v2
无人负责且 ready，统一适配器认领 HTTP 200 后 v3/progress；来源修订 1091。
认领、负责人和后续状态仍以实时 Kanban 为准。

## 输入与复现

[source-inventory.json](source-inventory.json) 记录 166 个非核心候选源码文件与
28 个补充核心/契约/测试锚点，共 194 个 Git blob、字节数和 SHA256。
搜索结果只保存路径和行号，不复制既有宿主地址或私有配置内容。
[reproduce.py](reproduce.py) 直接读取指定 Git 提交，不读当前 dirty 内容，
不导入或执行被审调用者；只创建一个指定的新输出文件。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe evidence/U-103/reproduce.py --revision f5996086d89c72bc16e363b1e8c69675504c1a69 --output u103-new-inventory.json
```

先用 `rg` 搜索实际源码，再用上述清单绑定不可变输入。扫描候选覆盖 scripts、
ops、web、services/modeld、spikes 及可执行配置；排除核心内部实现、测试目录、
测试文件、文档/历史证据和 vendor gitlink。被引用的核心实现与相关测试另列为
锚点。vendor 提交在清单中保留，但没有把上游 SDK 整体当作本项目外部管理客户端。
动态导入两处分别是 Python 依赖准备和发布包依赖自检，未发现加载 V1 私有写入者
的外部调用链。词法搜索不能证明动态代码安全，结论来自下面的用途和调用链核对。

## 调用链与分流

| 调用者 / 命中 | 实际边界、核对依据与处置 |
| --- | --- |
| React API：`web/console/src/api/client.ts`，models/governance/work feature API | 浏览器 `fetch` → 核心 HTTP Handler → 当前身份 → 对应应用服务。V1 命令、原回执和结果读取走公开路由；客户端没有 Python 内部导入或 SQLite 通道。`api/types.ts:1` 的 `ai_union.console` 是注释，不能当作模块导入。UI 不是完整 S11 独立客户端证据。 |
| 开发 CLI/MCP：`scripts/project-management.mjs`、`union-board-mcp.mjs`、`kanban-client.mjs`、`kanban-operations.mjs`、`ops/automation/pick-next.mjs` | CLI/MCP → 统一适配器 → 在线 Kanban；离线 project.json 是开发交付历史，不是 AU 权威状态。没有直写 V1 AU 表的调用。开发账号与产品 AU 成员不混同。 |
| 核心 CLI：`ai_union/cli.py`、`__main__.py` | 包内 CLI → legacy Engine；不是另一个平台服务。Engine 构造和保留句柄的读写/授权边界调用 `check_legacy_runtime`，V1/future/不完整状态拒绝；不能因为 CLI 支持 legacy 就宣称支持 V1 命令。未新增旧 CLI 兼容目标。 |
| 核心内的旧管理门面：`ai_union/model_accounts.py`、`gateways.py`、`subscriptions.py` | 没有仅凭文件在核心目录就跳过检查。账号/网关/订阅门面有自己拥有的配置与回执表；涉及旧 AU 的 model account adoption/events 与 gateway 查询先经 `app.engine`，再进 Engine 事务，V1 被 profile 边界拒绝。这些不能被当作 V1 业务公开契约或新产品已实现证明。 |
| 具体公司场景：`ai_union/corp.py`、`company.py` | corp 的 company_engine 通过 legacy_directory 校验原目录/profile 后构造 Engine；company 是小说实验的纯状态操作，随 legacy Engine 事务采用。保留具体 benchmark，不能从名称推断已有通用平台或 V1 外部公司集成。 |
| 进程启动：`scripts/start-console.mjs`、两份 `ops/systemd/*.service` | 启动包内核心 server/legacy CLI，属于核心进程装配，不是从外部应用调用 AU 私有 writer。服务文件未运行。 |
| 旧 HTTPS 装配：`ops/console-subscriptions/run_frontend.py` | 在同一宿主构造 Console/Server，再转发 HTTP；直接 import 是核心服务装配。宿主 ticket/platform_admin 不携带核心 principal，不能代替 V1 创建/读取授权；对应 `test_host_ticket_and_platform_admin_do_not_substitute_for_core_principal`。保留历史，不以此要求维护旧入口。 |
| 发布/身份维护：`scripts/release_package.py`、`upgrade_core_identity.py`、`reset_owner.py` | 随核心包交付的宿主维护命令，不是私有平台业务 API。发布器在只读连接检查 auth/catalog/AU/modeld 兼容；升级由 identity_schema 执行、需要停服与锁；reset 直接修改身份表，是显式宿主管理操作，不能作为平台 API 或 AU 治理迁移。已有同名 owner 重建不可取得原 AU/回执的行为保障。本次未运行维护写入，也不新增授权。 |
| `scripts/exit22b_host.py` | 验收宿主构造 Console/Server、接线 modeld transport；`prepare` 通过 modeld 管理 HTTP 创建特定 grant，页面仍通过产品 API 采用连接。不能视为独立黑盒客户端，也不能以该 helper 的存在授权真实调用。本轮只读源码。 |
| 8 个导入 tests 的脚本，以及 `validate.py`、模型/安装 check 脚本 | 临时 fixture、行为探针或安装验收；`u086_cancel_recovery_host.py` 的 SQLite 写入用于其测试用例的临时目录。不是实际平台迁移目标，不升级为真实结果。各路径和行号见清单。 |
| `scripts/update_model_catalog.py` | 调用 Catalog 验证公开模型元数据，再写仓库静态数据；不操作 AU 实例或运行态授权。 |
| `ops/dev-orchestrator/union_dev.py` | 自己的外置 state.sqlite 与 settings/runs/calls 表，记录开发执行；没有 V1 AU 表调用链。没有执行或修改该监督器。 |
| modeld 的 `src/journal.ts`、`kernel.ts`、`server.ts` | modeld 请求/用量与自己的凭据/宿主账户存储；是单次模型接入组件的事实所有者，不是直写 AU 治理/工作表。与 AU 的 grant/revision 边界仍必须校验；未据本审计认证所有 provider。 |
| `spikes/action-safety/store.ts` | PLAN-002 离线预算/actions 实验的自有数据库；没有接入 V1 AU 存储的生产调用链，不计作产品金额能力。 |

14 个 core import/entry 命中文件、9 个 storage 命中文件、8 个 test-host import
命中文件、2 个 dynamic import 命中文件均归入上述分类；分类可以重叠。53 个
HTTP/protocol 命中文件包括 React、验收 driver 和公开路由引用，数量不是能力计数。
没有因为路径位于 scripts/ops 就自动判定合法：维护/装配归类依赖其具体调用目标、
包归属、用途和身份拒绝保障；若未来将其暴露为平台远程操作，必须重新审查。

## 给 #55/#56 的准确接口输入

`ai_union/server.py:142–175` 与 `web/console/src/api/client.ts:60–115` 表明：

| 用例 | 当前实际路由 / 语义 |
| --- | --- |
| 创建 V1 AU | `POST /api/commands`，`kind: create_v1`；按 V1 主体与命令字段验证，不以是否含 `/v1/` 判断边界。 |
| 可见组织列表 | `GET /api/session` 的 organizations；不是 `GET /api/v1/aus`。 |
| 单个 V1 AU | `GET /api/v1/aus/{id}`，响应协议 `core.au.v1`，经当前 principal/治理投影。 |
| 原创建回执 | `GET /api/v1/receipts?id=...`，按原请求及有效身份读取；旧 `/api/receipts` 不读取 V1 创建。 |
| 一种工作命令 | `POST /api/v1/work/commands`；选择具体命令后验证 AU/Work/版本/责任/授权与原回执，仍由 #56 验收。 |

本源码没有 `/api/v1/aus` 集合路由。#55 描述中的集合 URL 应按这一事实准备
黑盒客户端，不需要为吻合文字新增一条接口。S01 的原契约已有单项读取；本次
不是发现一个必须新增集合 API 的产品缺陷。认证、同源、版本和错误/审计仍须
成对验证，不能只证明能发请求。

## 验证及后续

本卡只添加审计工具、输入清单和文档，不改行为代码，不破坏正确代码制造 RED。
既有 `tests/test_core_creation.py` 覆盖当前 HTTP 创建/读取、越权、原回执、
宿主 ticket 与 core principal 分离、同名 owner 重建；
`tests/test_core_isolation.py` 覆盖 V1 进入 legacy Engine 和保留 runner 句柄的拒绝；
`tests/test_catalog_integrity.py` 保留目录/状态身份核验，
`tests/test_identity_upgrade.py` 保留停服、锁、原请求和升级恢复边界。
执行结果及摘要见 [validation.json](validation.json)。这些既有检查支撑审计，
不把重复测试计为产品实现或真实业务进展。

查到实际 V1 旁路时才按具体调用者创建 2–6 小时改接/退役卡；本次没有此类发现，
因此没有新增迁移任务。后续触发为新外部调用者、相关公共协议/身份边界变动或
明确提供的私有平台源码；届时重新绑定输入。#40 的具体失败诊断、#46 的三个
恢复反例与 #47/#52 依赖继续保持原责任，不由本审计关闭。
