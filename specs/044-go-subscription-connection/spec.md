# 044：OpenCode Go 订阅接入 AU 执行（方案）

2026-11-03。用户指出 `/models` 上“可用模型可选”但没有执行能力，要求先给方案。本文只描述设计与验收，不包含凭据读取或真实调用；两者都需用户明确授权后才执行。

## 现状与差距

- 已上线（U-058/U-059）：Go 授权状态、最近授权时间、工作区、额度窗口、30 个可用模型只读展示。
- 未实现：选择模型后没有任何执行效果。原生账号服务不提供本机 OpenAI 兼容路由（`/v1/*` 返回网页），AI-UNION 的模型连接走 HTTP 适配器，两者未打通。
- 因此当前“可选”只是选择与复制，不写入配置、不发起调用。这是差距，不是能力。

## 现场探测事实（2026-11-03，只读）

| 项 | 结果 |
|---|---|
| 原生服务 | opencode v2.2.5，`/openapi.json` 共 138 条路由 |
| 本机推理路由 | 无。`/v1/models`、`/v1/chat/completions` 均返回网页 |
| Go provider | `package=@opencode/ai/providers/openai-compatible`，`settings.baseURL=https://opencode.ai/inference/go/openai/v1` |
| 模型对象 | 含 `headers: {x-opencode-org-id: <30 字符>}`，**不含** Authorization |
| 凭据 | `GET /api/credential` 返回 3 条，字段 `active/id/integrationID/label/value`；`/api/credential/{id}/activate` 可切换 |
| 额度 | `/api/experimental/usage/limits` → `workspace{id,name,usageURL}`、`go.{rolling,weekly,monthly}{percent,limited,resetsAt}` |
| 模型目录 | `/api/model` 68 个；`opencode-go` + `type=chat` + `enabled` 共 30 个 |
| 官方默认模型 | `/api/model/default` → `iceman-contributor-free` |
| AI-UNION 连接字段 | `base_url / model / protocol / api_key_env / api_key_file / auth_type / billing / context_policy …`，**没有自定义 headers** |
| 请求头生成 | `model_protocols.encode_request` 生成 Bearer 等鉴权头，连接配置无法追加头 |

结论：Go 订阅对外是**标准 OpenAI 兼容端点**，所需材料是一个 Bearer 凭据加一个非机密的组织头。缺的不是协议，而是“凭据如何安全落位”和“连接如何带上第二个头”。

## 方案 A（推荐）：直连官方推理端点

### 拓扑

```
AI-UNION 组织连接
  base_url = https://opencode.ai/inference/go/openai/v1
  protocol = openai_chat_completions
  model    = <用户在 /models 选中的模型 id>
  api_key_file = opencode-go.token          # 宿主凭据引用，不入库
  headers  = {x-opencode-org-id: <组织标识>} # 非机密
        │
        ▼
宿主私有文件 /volume1/docker/union-dev/ui-private/model-credentials/opencode-go.token (0600, uid 10001)
        ▲
        │ 一次性 root 脚本，从原生服务 active 凭据导出，只写不打印
原生账号服务 union-go-auth (127.0.0.1:4097)
```

### 改动点

1. **宿主准备脚本**（root，一次性，不进 Web 应用）
   - 读取原生服务 active 凭据，写入宿主私有文件（0600、uid 10001、目录 0700）。
   - 校验：文件不是符号链接、大小 ≤4096、权限正确、内容非空。
   - 容器追加 `UNION_MODEL_CREDENTIAL_DIR=/private/model-credentials`（重建容器，保留现有全部环境变量）。
   - 不打印、不写日志、不回显、不提交。

2. **连接配置支持受限请求头**
   - 新增可选字段 `headers`：最多 2 个；名字白名单当前仅 `x-opencode-org-id`；值限 ASCII 可见字符、长度 ≤128。
   - 明确拒绝 `authorization`、`cookie`、`host`、`content-length`、`content-type`、`transfer-encoding` 等。
   - 校验在 `validate_config` 内完成，旧连接不带该字段仍可读。

3. **协议层注入**
   - `model_protocols.encode_request` 接受连接头并合并到最终请求；Bearer 仍由凭据生成，不允许连接覆盖鉴权头。
   - 现有“wire 中不得出现凭据”的守卫保留：如果 header 值意外等于凭据，拒绝派发。

4. **创建连接的动作**
   - 平台管理员在 `/models` 的 Go 卡片里选中模型后点击“用此模型创建连接”。
   - 后端校验：模型 id 必须出现在原生目录的 `opencode-go` 列表内；`x-opencode-org-id` 取自原生目录，不接受客户端传入。
   - 连接归属当前组织；默认不设为默认连接；不自动测试、不自动派发。
   - 已存在同名/同模型连接时拒绝重复创建，提示改用编辑。

5. **前端**
   - 保留工作区/额度展示；把“只读选择”改为“创建连接”，创建成功后跳到已保存连接并提示“需要显式测试才验证模型能力”。
   - 失败时按类别提示：凭据缺失/已轮换（401）、额度受限（limited=true）、端点不可达。

### 安全与凭据边界

- 凭据仅存宿主文件；数据库、回执、日志、导出、浏览器均不含。
- Web 进程只按 `api_key_file` 读取，不提供任何“查看/下载凭据”的接口。
- headers 白名单避免任意头注入与请求走私。
- 连接仍受组织范围、岗位绑定与导出规则约束；跨组织不可读。
- 若用户不愿让 AI-UNION 持有凭据，本方案不成立，改走方案 B 或放弃。

### 失败与额度语义

| 情形 | 处理 |
|---|---|
| 401 / 403 | 明确拒绝，不重试；提示“凭据可能已轮换，需要宿主刷新私有文件” |
| 429 / 5xx / 发送后断开 / 超时 | 结果 unknown，不自动重试，保留原回执并要求核对（沿用现有 action-safety） |
| `limited=true` | 派发前警告；默认不硬拦（是否硬拦需单独决定） |
| 计费 | `basis=subscription`：先记用量，不记金额；百分比不是 token 上限，不能当硬配额 |
| 模型被下架 | 目录刷新后连接保留但标记不可用，不自动改模型 |

### 验收

- 单元/组件：header 白名单与拒绝、协议合并、Bearer 不被覆盖、文件引用越界、wire 不含其他头、401/429 语义、回执与 DB 无凭据。
- 真实集成（需授权）：**一次** `max_tokens≈1` 的请求，记录请求数=1、耗时、返回类别与 token 用量；不重试、不建组织、不写业务成果。
- 浏览器：选模型 → 创建连接 → 出现在已保存连接 → 工具往返测试结果可见。
- 回滚：停用/删除连接、删除 token 文件；组织数据与其他连接不受影响。

## 方案 B（备选）：经由原生会话代理

把 AU 的模型调用改为创建原生 session 并投递 prompt。不推荐作为首选：原生路由是 agent 语义（工具、权限、流式、取消），与现有执行器、费用口径和回执不兼容；改造面远大于方案 A，且会把订阅对话额度用于组织任务而难以按调用记账。仅当方案 A 的端点验证失败时再评估。

## 需要用户决定

1. 是否允许宿主一次性读取 active 订阅凭据写入私有文件（只写不显示）。
2. 是否允许一次最小真实调用做端点验证（产生订阅用量，不是金钱账单）。
3. 验证用哪个模型（建议免费档 `iceman-contributor-free`）。
4. 是否把创建的连接自动设为组织默认（建议否，显式勾选）。
5. 现存 3 个重复 Go 连接是否在本轮清理（建议不动，另立任务）。

## 明确不做

- 不改 AU 权限模型，不自动绑定岗位，不做多账号去重。
- 不引入新的计费口径或硬性额度管理。
- 不读取或代理 ChatGPT 凭据。
- 不因本方案自动启用调度、自动派发或真实组织任务。

## 工作量

`model_api.py`（headers 校验与注入）、`model_protocols.py`（合并头）、`subscriptions.py`（组织标识与模型校验、创建连接）、前端（选模型→建连接）、宿主脚本 1 个、测试与独立复核。约 1 个工作日；真实调用验收需单独授权窗口。
