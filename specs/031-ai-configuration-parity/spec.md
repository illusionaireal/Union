# AI 配置能力对齐（U-047）

2026-11-02进展：043新增真实目录数据、文件/环境凭据边界、多协议、岗位回退、上下文裁剪、多模态事件、四类费用及期末分摊。当前工程/真实验收逐行状态见[043矩阵](../../evidence/043-usable-model-access/matrix.md)。以下2026-11-01条目保留原对标依据和当时状态，不把历史“未实现”作为新实现结论；整体不低于目标仍须按矩阵完成真实验证。

2026-11-01。目标：AI 接入配置能力**不低于** opencode、pi、hermes、openclaw 中的任一家，同时不放弃 UNION 的治理边界。本文是对照判据与验收口径，不是完成报告；目前只有 M1 的模型目录机制受控验证（见 U-048），其余里程碑未实现。

## 1. 「不低于」的判据

以第 2 节对照矩阵逐行验收：每一行必须给出 UNION 的落点与测试方法。允许「等价但形态不同」（例如用组织状态命令代替编辑配置文件），不允许「缺失后声明不适用」。任何一行缺失即判未达标，不得以「已在别处支持」替代。

对照依据是 2026-11-01 在部署机上实测的四套软件配置，不是其宣传文档：

| 软件 | 实测配置形态 | 关键事实 |
| --- | --- | --- |
| opencode 2.2.5 | `opencode.json` + `opencode.db` 的 `credential` 表 | 235 个内置供应商；模型带 capabilities/cost/limit；按供应商的 key/env/oauth 三种认证 |
| pi 1.3.0 | `~/.pi/agent/models.json` + `auth.json` | 内置目录 + pi.dev 远程目录；30+ 环境变量；OAuth 回调可粘贴；Bedrock/Vertex 环境凭据；llama.cpp 本地 |
| hermes | `config.yaml`(504 行) + `.env`(25 键) | `model` + `fallback_providers`(3) + `custom_providers`（`base_url` + `key_env`）；TTS/STT/浏览器/渠道 |
| openclaw | `openclaw.json` | `auth.profiles` + `models.providers`(merge)；primary + 3 个 fallback；按 agent 分配模型；本地 embedding |

## 2. 对照矩阵

| 能力 | 四家现状 | UNION 目标 | 落点 | 状态 |
| --- | --- | --- | --- | --- |
| 供应商目录 | 235 / 内置+远程 / 若干 / 内置+自定义 | 可离线加载的版本化目录，覆盖主流供应商与模型 | `ai_union/catalog.py` | **M1 已实现（机制）**，目录数据待运维快照 |
| 模型元数据 | 上下文、输出上限、单价、能力、模态 | 同上，且未知一律显式 unknown，不猜测 | `catalog.validate_record` | **M1 已实现** |
| 认证方式 | key / env / oauth / 云环境凭据 | key、env 引用、文件引用；OAuth 仍由平台托管账号承担 | `api_connection` 扩展 | M1b（凭证字段，需独立复核） |
| 凭证卫生 | 多数明文落 JSON | 不回显、不进公开配置、不进命令日志；仅存组织私有库 | `reject_saved_secrets`、`stored_command` | 已实现，M1b 不得回退 |
| 多连接 | 多家支持多连接 | 已支持，保持 | `list_connections` | 已实现 |
| 角色级绑定 | opencode/hermes/openclaw 支持 | planner/worker/reviewer 各自绑定连接 | `execution_config.roles` | M2 |
| 故障回退 | 普遍 primary + 2–3 fallback | 有界回退链，且只在「明确未发出」或「明确失败」时切换 | `model_api` + 回执字段 `fallback_used` | M2 |
| 协议族 | openai/anthropic/google/bedrock/vertex | 至少 chat_completions + anthropic_messages + responses + 本地 loopback | `model_api` adapter 注册表 | M3 |
| 多模态输入 | 多家支持图片/PDF | 按目录能力判定，不支持则拒绝并说明 | `catalog.capability` + 工作包校验 | M3 |
| 本地/自托管 | pi llama.cpp、hermes local | 允许显式声明的内网 HTTP 端点（当前仅回环允许 HTTP） | `validate_config` 的 local 判定 | M3 |
| 上下文管理 | 压缩/裁剪/记忆检索 | 按目录的 context 上限做裁剪与压缩 | `agent_protocol` + `catalog` | M4 |
| 成本口径 | 单价目录可直接算 | `cost_basis` 四类，金额可空，见第 3 节 | `model_connections.billing` + 回执 | M5 |
| 变更审计 | 多数无 | 命令 + 回执 + 事件 + 版本冲突 + 幂等 | 现有实现 | 已实现（领先） |
| 权限与隔离 | 单用户 | 组织私有 + board/platform_admin 分级 | 现有实现 | 已实现（领先） |

## 3. 成本口径（为什么现在可以先不补金额）

成本核算的本质是「一次调用的费用归属」，不是「一个 token 的单价」。三类供给方式的成本结构不同，硬套单价会产生错误账：

| basis | 适用 | 金额来源 | 可实时？ | 记录方式 |
| --- | --- | --- | --- | --- |
| `metered` | 按量付费 API | 目录单价 × 用量 | 是 | 每次调用直接记金额 |
| `subscription` | 包月/席位（ChatGPT、Go、Bedrock 承诺量） | 周期总费用按周期内用量占比摊 | 否，只能期末回填 | 调用先记用量与 basis，期末生成分摊凭证 |
| `owned` | 自部署 GPU / 自有主机 | 折旧 + 电费 + 托管费，按占用时长摊；不可得时用等价云 API 的影子价并标 `estimated` | 否 | 调用记用量与 basis，期末按机器时间分摊 |
| `unknown` | 未提供计价依据 | 无 | — | 金额留空，**不得记 0** |

规则：

1. **用量必测、金额可空、basis 必填**。`usage` 是客观事实（`prompt_tokens`/`completion_tokens`/`cached_tokens`），任何时候都能记录；金额允许为空。
2. **一次调用只记一次账**。分摊是期末对已存在调用生成凭证，不修改原始调用记录，也不产生新调用。
3. **未知不是零**。`cost_status ∈ {known, estimated, amortized, unknown}` 必须显式保存；现有回执的 `{"cost": null, "cost_status": "unknown"}` 保留此语义。
4. **不跨组织合并**。共享预算的父子组织可聚合统计，但一次请求只向一个明确资源来源记账。
5. **口径变更留版本**。单价、折旧率、分摊规则都带版本与生效时间，历史凭证不重算。

因此本项可以后补金额而不返工，但**字段与枚举必须先落地**（M5 只补数据与分摊算法）。若现在就强行引入单价，订阅与自部署两类会长期记错账，比 unknown 更糟。

## 4. 里程碑

| 里程碑 | 内容 | 验收 |
| --- | --- | --- |
| M1 | 模型目录机制：快照加载、schema 校验、三态能力查询、凭据字段拒绝、读路径容错 | 25 项机制测试通过；未知模型在连接投影中显式为 null；目录损坏不中断连接列举 |
| M1b | 凭证引用：`api_key` 支持 `env:` / `file:` 引用，解析发生在派发时，密钥不落库 | 需独立权限复核；落库内容不含密钥；引用失败给出明确拒绝而非空密钥 |
| M2 | 角色绑定与回退链 | planner/worker/reviewer 绑定不同连接；主连接 401 后按序回退并在回执记 `fallback_used`；已发出未知的调用**不**回退 |
| M3 | 协议适配与本地端点 | 同一组织下 chat_completions 与 anthropic_messages 各完成一次工具往返；内网 HTTP 端点仅在显式声明时允许 |
| M4 | 上下文管理 | 超过目录 context 上限时按策略裁剪并记录丢弃量，不静默截断 |
| M5 | 成本口径落地 | 四类 basis 各有一条真实或受控样本；`unknown` 不被记 0；分摊凭证可追溯到原始调用 |

### 已实现进度

- **M1（U-048）**：目录机制受控验证——快照加载、schema 校验、三态能力查询、凭据字段拒绝、读路径容错。
- **M1b（U-049）**：凭据环境变量引用受控验证——连接只保存变量名，密钥不落库；内联密钥与环境引用二选一；解析失败按变量名报错且不回显值。**独立权限复核仍未进行**，恢复路径与真实供应商调用未验。
- **M2a（U-050）**：角色绑定与解析期回退受控验证——planner/worker/reviewer 可分别绑定，未绑定继承默认，回退链不超过三条且校验，不可用连接按链下移并记录 `fallback_from`；**运行期失败切换（M2b）与前端入口未实现**。

- **M2b（U-051）**：运行期失败切换受控验证——仅在 401/403/429/明确 4xx/重定向/连接被拒时沿链切换并重建请求体；5xx、发送后断开与超时仍判为未知且不切换，回执记录 `fallback_from` 与每次尝试。每角色独立回退链与前端入口未实现。
## 5. 与现有约束的关系

- 目录**不含凭据**：`validate_record` 拒绝任何形如 key/token/password 的字段，不透传供应商地址。
- 回退不削弱 unknown 规则：只有「明确未发出」或「明确失败」才切换；已发出但结果未知的调用仍须人工核对，不得自动重试。
- 目录缺失或损坏时按 unknown 处理，不阻塞模型管理（读路径容错，配置路径严格报错）。
- 不引入厂商 SDK；协议适配只用标准库，避免把供应商行为写进组织状态。

## 6. 未实现与风险

- 目录数据本身尚未提供：当前 `UNION_MODEL_CATALOG` 未配置，所有能力查询返回 unknown。这不是缺陷，是显式状态。
- 回退可能掩盖真实故障，因此回执必须记录切换原因与最终使用的连接版本。
- 协议适配会扩大响应解析面，须复用现有边界校验与失败分类，不新增「猜测成功」的路径。
- 成本分摊依赖期末数据，期间账目只能是 `estimated` 或 `unknown`；对外报告必须标注。
