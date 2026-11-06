# S02：模型连接、有限授权与资料工具往返

2026-11-06，U-072 / 在线 #21，`rewrite/charter-v1`。**工程、浏览器、隔离安装及用户新指定连接的真实资料工具往返已通过。** 实现提交为 `41ae2daa022fe42835a3ab767a529d2f7cdcabe1`。用户在原 Codex 连接认证失败后提供本机兼容 API 和 `group/deepseek-v4.1-flash-free`；安装包经普通核心身份完成两次推理、一次实际资料读取、默认采用和重启核对。原 Codex 失败仍保留，不被新连接成功覆盖；整卡状态与验收范围以主账为准。

用户现在可在 React 的“模型与 API”页分别保存连接、授予有限调用、允许读取本次文本、提交资料验证和采用默认连接。验证有持续的 Work、责任成员、Mandate、Agent Definition 和独立调用记录。受控浏览器验收实际经过核心 HTTP、SQLite、modeld 和固定 SDK，模型发出读资料请求后，程序读取文本并把工具回执交回第二次推理；这是接入检查，不是任意目标的自主业务成果。

## 本次证据

| 范围 | 结果与依据 |
| --- | --- |
| 整库检查 | `npm run check` 通过，前端 192 项；Python 579 项中 574 通过、5 项平台跳过。[汇总](finish/verification.json) |
| modeld | 显式 8 个测试文件共 88 项通过；保密 focused 48 项，独立复核 49 项及 5 个反例/正常探针通过。[保密复核](finish/modeld-review.md) |
| 身份、恢复、用量 | 独立 Python 47 项；最终原事件/并发 8 项及旧实现的两个确定性失败对照。[复核](finish/python-review/review.md) |
| 协议、持久版本 | 显式 Responses、旧 Chat/Go、原生工具配对和 schema 0/1 复核通过；发布/schema 5 项通过。[复核](finish/protocol-review.md) |
| 前端 | 独立 51 项组件测试和类型检查；真实 Chromium 66 项，覆盖 320/390/1024/1440、键盘、断网、丢回执、身份和 AU 切换。[浏览器记录](finish/browser-final/checks.json) |
| 安装 | 隔离导出本次源码，重新构建并安装；86 个交付文件、190 份源码哈希核对通过。浏览器所验前端与安装包资产相同。[安装](finish/candidate-install.json) · [清单](finish/installed-manifest.json) |
| 真实连接 | 所选 `gpt-6-astra` / Responses / `max`，每次最多 512 输出 tokens。仅派发 1 次请求，认证失败，没有可采用回答或工具执行。[原结果](finish/real-result-unconfirmed.json) |
| 实际重启 | 安装包重启后查询同一原请求；原 AU/Work/attempt/事件保持，无新增推理。不兼容的 AU/modeld schema 声明均被拒绝。[恢复](finish/installed-recovery.json) |
| 新指定真实连接 | 用户指定模型经既有 Chat Completions profile 完成 2 次真实推理、1 次 `read_document`；第一轮 403 输入/62 输出 tokens，第二轮 310 输入/56 输出 tokens。两次输出均低于 512，费用缺失保留 unknown。[真实结果](finish/real-local-provider.json) |
| 真实结果的页面与恢复 | 安装包重启后正常密码登录同一核心主体，回答与默认连接保持。实际 Chromium 14 项只读检查，1440/390 宽度、答案/责任/费用显示及刷新通过；无新推理。[页面](finish/real-browser/checks.json) |
| 本轮独立复核 | 只读核对实际 SQLite、原资料/工具/回答、请求次数、历史状态哈希及权限/费用边界。[复核](finish/local-provider-review.md) |
| 最终记录 | 主账以 `real` 记录 U-072，线上 #21 `done`、HTTP 200 读回；WIP 按主账口径为 5/6，其他任务不变。管理 8 项及工作记录结构通过。[验收汇总](finish/real-acceptance-summary.json) · [Kanban 回执](finish/kanban-real-acceptance.json) |

安装候选在提交前从基点 `d5802f8672df88db447e7e0bb86c2f1a5265ad18` 加本次明确归属的文件构建。Git 导出把四个工作区文件的 CRLF 规范为 LF，已逐一证明仅换行不同；清单保存实际构建字节哈希，复核保存工作区原字节哈希。没有将无关预存改动、私有配置、密钥或运行数据库收入候选。

## M01–M10 对照

M01–M04 的核心身份、保存/默认分离、原请求核对、责任与额度准入由 `tests/test_core_models.py`、`test_core_model_boundaries.py`、`test_core_model_http.py` 等覆盖。M05–M08 的两阶段工具/native、权限变化、未知/取消、原事件去重和用量由 `test_core_model_checks.py`、`test_core_model_recovery.py`、`test_core_model_observations.py`、modeld 测试及独立反例覆盖。M09 见原 66 项实际浏览器及新增 14 项真实结果页面检查。M10 的工程、独立复核和安装证据在 `41ae2da` 保持，最后的真实出口由用户明确改选的兼容 API 提供；这不证明原 Codex/Responses 真实连接恢复或其他 profile 已通过。

严格 TDD 的失败反例先于修复。修复包括模型原始字段中的分片凭据、线程启动失败的迟到覆盖、相同事件重放、冲突前已收到的用量、币种与金额被错误拼接，以及安全原生片段延迟释放。浏览器最后一次失败是验收脚本把 `<strong>` 当标题定位；修正定位后完整 66 项通过，未为此改变产品语义。安装验证脚本最初生成了两个额外 `.pyc`，被不可变包检查拒绝；清理仅这两个测试缓存并禁用字节码后，实际启动与恢复通过。

## 新指定连接的实际验收与历史保留

用户提供新连接作为此前两次推理、每次最多 512 输出 tokens、费用缺失保持未知的续接资源。只读模型目录 HTTP 200 并列出指定模型。两次推理通过原核心/modeld/SDK 链，资料正文及动态校验码在第一轮请求中不存在，只有实际工具读取后才进入第二轮请求；最终回答包含“连接设置、资料读取、用量记录”“蓝色纸船”和该校验码。`resolved_model` 是服务返回的路由标识，不能独立证明网关背后的具体供应商/权重版本，`actual_model` 保持未知；模型名含 free 也不据此记零费用。

原私有 driver 没有保存旧临时账号的密码或恢复秘密。本轮通过正常核心注册/创建接口建立明确命名的新验收 AU，其目标与证据关联原失败 AU；没有伪造旧主体会话、修改其授权或迁移旧数据库。新 AU 为 `org-27cfb87f6c434ade9ac8f2fbaaee7abb`，原失败 AU 为 `org-39ba258522e6482c977fb52e28765e99`。合计 3 个真实请求：原 1 个认证失败/结果待核对，新 2 个完成；原 Work、attempt、事件、未知用量和占用逐项不变。新账号恢复信息只存宿主私有目录，正常密码登录与重启持久化已验证。

本轮没有修改产品行为代码。新私有驱动第一次在模型服务健康检查错误携带浏览器 Origin，被既有保护以 403 拒绝；当时账号/AU/新增推理均为 0，修正驱动后显式续接。页面脚本最初误将授权用户可见的连接地址视为泄漏，核对现有页面合同后仅对公开截图遮住私有地址；实际 DOM 上执行密钥保密及回答断言。两项脚本问题都没有重复调用模型。最终使用已有安装包，76 份工程源码哈希与既有验证一致；广泛回归不因纯证据/文档更新重复运行。

原 `finish/verification.json`、失败结果和恢复记录是当时的检查点，保持原字节和当时未完成结论。最新完成证据以上述新真实结果、页面、复核及主账记录为准。私有 driver 的一次性派发标记继续保留；不能重新运行真实请求来重现截图或更新文档。

上述账号和 AU 仅用于隔离接入验收。模型正文没有进入正式业务成果；未执行 S03/S04、其他 profile 的真实验收、真实业务数据迁移、部署或持续运行。人类参与属于用户选定资源及有限授权的保留治理；工程代理的开发与复核不是产品 AU 成员活动。

此前设计核查与 12 卡文案记录分别见 [design-readback.md](design-readback.md) 和 [card-clarity.json](card-clarity.json)，保留其当时的未完成状态，不将历史失败改写为当时已经通过。
