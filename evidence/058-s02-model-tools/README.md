# S02：模型连接、有限授权与资料工具往返

2026-11-06，U-072 / 在线 #21，`rewrite/charter-v1`。**工程、浏览器和隔离安装验证已通过；指定 Codex 连接的真实往返尚未通过，整卡未完成。** 本机所选连接的首次推理请求被拒绝认证，随后直连和本机代理的只读认证检查均返回 HTTP 401。未自动重试，也未将未知费用记为零。

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

安装候选在提交前从基点 `d5802f8672df88db447e7e0bb86c2f1a5265ad18` 加本次明确归属的文件构建。Git 导出把四个工作区文件的 CRLF 规范为 LF，已逐一证明仅换行不同；清单保存实际构建字节哈希，复核保存工作区原字节哈希。没有将无关预存改动、私有配置、密钥或运行数据库收入候选。

## M01–M10 对照

M01–M04 的核心身份、保存/默认分离、原请求核对、责任与额度准入由 `tests/test_core_models.py`、`test_core_model_boundaries.py`、`test_core_model_http.py` 等覆盖。M05–M08 的两阶段工具/native、权限变化、未知/取消、原事件去重和用量由 `test_core_model_checks.py`、`test_core_model_recovery.py`、`test_core_model_observations.py`、modeld 测试及独立反例覆盖。M09 见 66 项实际浏览器记录。M10 的工程、独立复核及安装部分通过，**指定真实 profile 的成功往返仍缺证据**，不能以 controlled 关闭整卡。

严格 TDD 的失败反例先于修复。修复包括模型原始字段中的分片凭据、线程启动失败的迟到覆盖、相同事件重放、冲突前已收到的用量、币种与金额被错误拼接，以及安全原生片段延迟释放。浏览器最后一次失败是验收脚本把 `<strong>` 当标题定位；修正定位后完整 66 项通过，未为此改变产品语义。安装验证脚本最初生成了两个额外 `.pyc`，被不可变包检查拒绝；清理仅这两个测试缓存并禁用字节码后，实际启动与恢复通过。

## 后续执行条件

请修复所选 Codex 连接，或指定另一份已授权配置；无需在会话发送密钥。原两次请求范围已记 1 次失败请求，完整新往返需要重新明确两次推理授权，费用没有原始依据时继续 unknown。原失败 AU、Work、请求、资源占用及证据保留；不能重放旧未知 attempt，也不能通过新建组织隐去这次失败。

上述账号和 AU 仅用于隔离接入验收。模型正文没有进入正式业务成果；未执行 S03/S04、其他 profile 的真实验收、真实业务数据迁移、部署或持续运行。人类参与属于用户选定资源及有限授权的保留治理；工程代理的开发与复核不是产品 AU 成员活动。

此前设计核查与 12 卡文案记录分别见 [design-readback.md](design-readback.md) 和 [card-clarity.json](card-clarity.json)，保留其当时的未完成状态，不将历史失败改写为当时已经通过。
