# U-101 / #55：独立 HTTP 客户端创建与查询

2026-11-11。本轮为已有公开协议补充可重复运行的独立进程集成验证，不修改
核心业务实现。输入固定 `cb3fa500847f8dc3ce75488f85fd40d49e69082c`，
不包含普通 checkout 的 U-086 改动或原作者未交付的 U-092 候选。

实施 actor 为 Codex session `01a1c746-eb38-7711-ad90-290392a05d89`；在线成员
`codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`。这是工程
集成实施，不是产品 AU 成员，也不是本候选的独立权限评审。

[冻结合同](contract.md)定义 C01–C08；
[测试客户端](../../tests/test_public_core_client.py)仅使用 Python 标准库，
不导入核心/内部测试 helper、不读 SQLite、启动票据或 AU 私有目录。
真实临时 Core 由另一个进程通过既有 CLI 启动，业务准备和检查均使用 HTTP。
服务根目录与所有合成账号由本次测试创建；进程结束后清理。未调用真实模型。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m unittest tests.test_public_core_client -v
```

Linux/macOS 使用项目固定环境的 Python 运行同一模块。不需要平台账号、
仓库凭据、外部服务、已有 AU 或正在运行的业务部署。标准 `unittest discover`
也自动包含这 7 项测试。临时服务清除继承的 `UNION_*` 配置并禁用 API 执行器，
不会借用宿主真实模型连接。客户端直连测试进程的回环端口，不使用系统代理。

| 可观察结果 | 对应测试 |
| --- | --- |
| 正常创建、协议/版本、受信治理根、未激活能力及公开回执关联 | `test_prepared_creation_protocol_versions_and_public_audit_link` |
| 普通参与者可独立创建；跨账号读取/同 ID 重放被拒，缺失与无权 ID 不泄漏差异 | `test_ordinary_account_creates_own_au_but_cannot_read_or_replay_another` |
| 新登录会话同请求返回原回执，改变内容返回 `id_conflict` | `test_same_principal_new_session_replay_and_conflict_preserve_original` |
| 伪造身份/profile/激活、错误创建版本和布尔资源上限不消耗请求 ID | `test_invalid_identity_version_and_types_do_not_consume_request_id` |
| 未认证、跨 Origin/Host/Fetch-Site 拒绝，正常请求可随后创建 | `test_anonymous_and_cross_origin_requests_cannot_create` |
| 丢弃响应正文后 GET 原回执找到同一 AU，只发送一次创建 POST | `test_discarded_response_is_recovered_by_original_id_without_second_post` |
| 终止/重启临时进程，正常密码登录仍保持主体、AU、版本及回执 | `test_restart_and_normal_login_preserve_principal_au_versions_and_receipt` |

## 实际接口和边界

1. 正常账号使用 `POST /api/auth/login`，保留服务返回的 Cookie；测试空宿主
   首次设置/普通注册分别使用 `/api/auth/setup` 与 `/api/auth/register`。
2. 创建是 `POST /api/commands` 的 `kind: create_v1`，五字段外层及最小合成
   章程见测试的 `creation()`。`organization_id`、`base_version` 均为 null。
   本轮不把五字段章程当作完整治理已经激活。
3. 列表是 `GET /api/session` 中按主体过滤的 `organizations`；单项读取是
   `GET /api/v1/aus/{id}`。与 [U-103 审计](../U-103/README.md)一致，没有为
   旧卡片描述额外实现集合 URL。
4. 原创建回执是 `GET /api/v1/receipts?id={request_id}`。客户端检查 HTTP
   和 `receipt.status`；200 本身不等于成功。响应丢失后先查原 ID，不能换 ID
   或自动再创建。此次模拟的是丢失响应正文，未模拟远端业务取消或存储 unknown。

公开审计检查包括 request ID、actor、created_at、AU ID、协议/版本和治理根。
两个测试账号用于验证隔离，不是 AU 必须有两名成员的产品要求。拒绝结果是
客户端实际观察，不冒充服务端持久拒绝日志。客户端没有读取私有
`creation_adoptions` 表，不重新宣称跨数据库事务/故障恢复已经验证。

首次 7 项全部 GREEN，已有正确实现保留，没有撤掉代码制造 RED。
本机 Python 全量 **824 项、8 跳过、0 失败/错误**（含新增 7 项和实际 SDK 的回环替身检查），
`npm run check`（37 管理、306 Node、363 前端）通过；生成视图、管理与计划检查通过。
固定 SDK 准备遇到 Git SHA 缩写、Windows 长路径和冻结锁文件检查失败，原日志与
失败树保留；随后只读复用已核对的同 pin/同记录补丁/同源码依赖，全量通过。
没有修改补丁或锁文件来绕过检查。工具链、源码绑定与日志摘要见 [validation.json](validation.json)。
测试和本机运行结果只属于 controlled；完整工作命令归 #56，独立使用归 #58，
新产品体验归 #64–#69，父 #30 未完成。本候选仍须准确 head CI 和非实施工程
角色的身份/权限复核；在线状态以 Kanban 为准，不由此文件宣布 done。
