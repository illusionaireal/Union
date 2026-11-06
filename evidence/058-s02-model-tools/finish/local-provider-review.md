# S02 / U-072 / #21 新指定连接的独立只读复核

2026-11-06。复核者：外部工程子代理 `s02_real_acceptance_review`。

## 发现优先

**本次新增真实验收范围内，未发现 Critical 或 Important 阻断缺陷。** 结论依据私有驱动静态审阅、安装实例的只读 SQLite 核对及公开证据交叉验证；不授予资源、合并或整卡完成权限。

需保留三项边界：旧临时账号的密码登录/恢复未由本次证明；新验收 AU 不能称为旧 AU 的恢复或迁移。`actual_model` 和金额仍未知，模型别名中的 `free` 不是价格证据。真实页面的 14 项检查由协调者执行，本复核读取其记录，没有再次运行浏览器或模型。

## 范围与依据

- `working-tree`，基点及当前 HEAD 为 `41ae2daa022fe42835a3ab767a529d2f7cdcabe1`，分支 `rewrite/charter-v1`。核心范围是 `real-local-provider.json`、`local-provider-readcheck.json`、S02 契约末尾资源选择，以及私有 `verify-local-provider.py`；预存无关编辑不纳入评价。
- 依据根 `AGENTS.md`、`CONTEXT.md`、S02 契约 M01–M10 与用户最新资源选择、ADR-0005/0006 的 S02 节，以及 Charter D-01/D-02/D-04/D-05、A-01/A-03/A-04、R-01–R-07、K-03/K-04、X-02(a)。新资源覆盖旧 Codex 选择，未放宽两次推理、每次 512 输出 tokens 及费用未知条件。
- 本次没有产品行为改动。既有协议、权限、费用、保密、恢复、UI 与安装复核作为已有证据使用；579 项 Python、192 项前端、88 项 modeld、66 项浏览器检查未在本复核重跑。

## 新证据核对

| 检查点 | 核对结果 |
| --- | --- |
| 普通主体与治理 | catalog 中新账号为 `account_kind=core`、`platform_admin=0`；创建记录、初始治理根、当前治理者及最终决定方均绑定公开证据中的同一 principal。治理为 active/local_governance.v1，具备保留事项和超时退出程序。驱动经正常注册、创建、治理及模型命令操作，无伪造会话或直接写领域数据库。对应驱动 200–239 行及真实证据 8–21 行。 |
| 责任与有限资源 | 实际 Member、binding、Work、不可再委托的 Mandate、`core.model_check` v1 与 check 的标识/版本一致；创建计划及显式 grant 均为 2，用途 connection_check，明确接受未知费用。每个 core payload 与 modeld 原 payload 一致，`generation.maxOutputTokens` 均为 512。对应真实证据 22–26 行。 |
| 两阶段实际工具 | 首轮原结果只有一个 read_document，document_id 精确匹配 check；原工具调用 ID、assistant 消息和工具 JSON 回执完整进入第二轮。资料摘要正确；首轮无正文和校验码，第二轮两者都有；最终模型原文与公开回答完全一致，没有后续工具调用。实际工具回执只有一条。校验码由 `ai_union/application/model_access.py:118` 的随机生成产生，驱动未硬编码该值。对应真实证据 77–78 行。 |
| 调用与用量 | modeld 全库只有 3 个请求：旧 AU 一个 interrupted，新 AU 两个 completed；新 ID 与公开证据一致。两次输入/输出分别为 403/62、310/56，来自各自原结果，公共投影未将累计流用量再相加。币种、整数金额缺失，保持 unknown。对应真实证据 27–76、82–87 行。 |
| 原历史与占用 | 原 AU state SHA-256 仍为 `aa2b631418b7e469881292cc5e2d03afa953f29653d47934e2a17dace73060d0`，与 `installed-recovery.json:22` 完全一致；原 Work 为 open、check 为 unknown、诊断为 provider_authentication_failed、原 attempt/未知用量保留，工具数为 0。现行规则仍保留旧验证的 2 个预约位置；新验证占用自己的 2 个位置，不能把预约数说成实际派发数。驱动 92–101、261、281 行还逐项比较旧 state/attempt/tool/request/event 事实。 |
| 重启与采用 | 驱动 262–281 行先显式采用默认，再重启两端、清除内存 cookie 并使用正常密码登录，核对同 principal、同 check、默认及请求集不变。私有运行记录为 verified；当前数据库与公开结果一致。本复核未自行重启服务。 |
| 真实页面 | 已读 `finish/real-browser/checks.json`：14 项，1440/390 宽度，实际回答/责任/未知费用、刷新与默认保持；model_commands=0、additional_inference_requests=0、请求总数仍为 3。公开截图遮盖真实端点，断言使用原 DOM；这不等于对授权用户隐藏其配置地址。 |

所有复核数据库连接均使用 `mode=ro`。最后一组 12 项直接配对断言全部成立；公开新证据及契约不含所选密钥或真实端点。私有原始正文、凭据及安装配置没有写入本报告。

## 身份保留与兼容判断

本次是**另行命名的隔离接入验收**：新 AU 的目标及公开证据明确关联旧失败 AU；旧标识、责任、用量及占用保留，新成功未覆盖旧失败。它符合本限定场景的历史保留要求，不构成业务迁移，也不能据此宣称旧主体已恢复访问。新账号登录/恢复材料已保存在宿主私有记录。

私有驱动首次因错误携带浏览器 Origin 被 modeld 返回 403，发生在注册、AU 创建和新增推理之前。修正后仅允许从该 preflight 失败阶段续接，并先核对账号未建立、AU 数为 1、请求数为 1；运行记录保留此次失败及新增调用为 0，未重放旧 attempt。

本次仍由原 GovernanceStore/应用拥有 AU 事实和有限流程，modeld/Journal 拥有单次推理及原始用量；未引入第二个 SDK loop、协议 fallback 或重复写入者。旧 Chat/Responses/Go 路径按已有兼容依据保留。资源选择没有形成新的持久架构决定，未发现需补 ADR 的 Design Defect / Implementation Drift。

## 评估与建议

有效做法是通过正常核心接口行使权限、用原请求和实际工具回执核对结果，并将成功与旧失败分别保留。新增证据可支持所选兼容网关的有限两次推理/一次资料工具往返及重启持久化；不能证明网关背后的具体权重版本、一般自主业务、其他 profile、部署或持续运行。

建议协调者在最终文档与主账中沿用上述新旧区分，保留旧失败和未知费用，不重新运行真实 driver。最终 M01–M10 汇总、任务状态和交付决定由协调者完成；本报告仅为 advisory review，证据强度 B。

本次读取快照：`verify-local-provider.py` SHA-256 `ddff923eb6053544d4dae8dcd8e50d03d484ec73d76eb9ad0ea27b620d581d00`；`real-local-provider.json` SHA-256 `9a3215c60cb2a112c0a1527c53e75eeecc3a390de27a6ffdf11f35c7693c6e8e`。

协调者交付补记：上述真实结果快照的原始字节仍保存在宿主；公开 JSON 按仓库规则将 CRLF 归一为 LF，已验证解析内容完全相等。复核时的哈希保留为历史依据，实际交付文件哈希与换行映射见 real-acceptance-summary.json。
