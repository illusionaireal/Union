# 真实模型 API：运行与前端接口

2026-10-16 更新：开发主分支 `dev`；小说公司首版已接入网页创建、模型 API 配置并绑定/连接测试、经营周期/章节/账本及缺失用量核对。操作入口按页面职责展示。最新范围和使用步骤见 [NOVEL_COMPANY.md](NOVEL_COMPANY.md)，下文旧迭代记录以此更新为准。

更新：2026-10-13。后端支持 OpenAI-compatible Chat Completions，通过配置的 API 根地址调用 `/chat/completions`。无需 Codex CLI。前端页面由独立开发者接入；本次未修改 `web/console/` 或生成的 HTML。

2026-10-14：在 `dev` 中与 React 前端整合。已绑定默认 API 可从运行表单选择，API 与 Codex 的名称和模型配置分别表达；API 回执类型、失败状态与查询身份已兼容。连接管理表单仍待接入，配置和绑定按下文 CLI／HTTP 完成。合并验证见 [dev](../evidence/dev-integration/README.md)。

## 1. CLI 配置与运行

先创建独立组织，不复制 fixture 数据库作为真实能力评测起点：

```sh
python3 -m ai_union --root .union/api-real init --name "真实模型测试" --board-name "发起人（本地测试）" --charter examples/charter.local.json --resources examples/resources.local.json
```

复制 `examples/model-api.json` 到私有目录，例如 `.union/api-real/model-api.json`，填写供应商 API 根地址和实际模型 ID。文件不含密钥。配置项必须齐全：

| 字段 | 含义 |
| --- | --- |
| `name` | 连接显示名称，1–100 字符 |
| `base_url` | API 根地址，例如 `https://api.openai.com/v1`；不含 `/chat/completions`、账号密码、查询参数或片段 |
| `model` | 实际模型 ID；首版采用既有 1–128 位模型标识格式 |
| `response_format` | `json_schema`：严格结构化输出；`json_object`：JSON 模式，仍由宿主验证完整协议 |
| `token_limit_field` | `max_completion_tokens` 或 `max_tokens`，按供应商接口选择 |
| `max_output_tokens` | 1–32768；会传给供应商，实际约束由供应商执行，不等于金额硬上限 |
| `timeout_seconds` | 1–600；实际单次截止时间取该值与组织资源超时的较小值 |
| `enabled` | 布尔值；停用后禁止新调用 |

将 API Key 放入自己配置的环境变量 `UNION_MODEL_API_KEY`，或置于私有文件，使用以下命令。命令中没有明文密钥参数：

```sh
python3 -m ai_union --root .union/api-real api-configure --connection-id primary --config .union/api-real/model-api.json --api-key-env UNION_MODEL_API_KEY --board-key-file .union/api-real/board.key --reason "配置有限测试使用的模型 API"
python3 -m ai_union --root .union/api-real api-bind --connection-id primary --board-key-file .union/api-real/board.key --reason "采用组织默认连接"
python3 -m ai_union --root .union/api-real api-list
python3 -m ai_union --root .union/api-real api-test --board-key-file .union/api-real/board.key --allow-unknown-cost
python3 -m ai_union --root .union/api-real run --executor api --max-steps 7 --allow-unknown-cost
python3 -m ai_union --root .union/api-real evaluate --output .union/api-real/evaluation.json
```

Windows 使用 `python`。示例资源累计最多 8 次调用：连接测试使用 1 次，随后最多 7 次；实际能否完成 E1/E2 取决于模型。失败也保留占用，不自动退款或重置。仅配置和绑定不调用模型。

`--api-key-file` 与 `--api-key-env` 二选一。更新配置时省略这两项沿用已保存密钥；API 地址改变时必须明确重填或使用 `--clear-api-key`。`api-bind` 省略连接 ID 清除默认绑定。`run/watch --connection-id OTHER` 覆盖本次连接；API 模型由选中连接决定，不接受 `--model`。`watch` 同样支持 API，并要求有限 `--max-steps` 与 `--max-seconds`。

连接测试验证实际模型、输出模式和输出上限字段，最多请求 512 个生成 token；它不消费业务事件、不建立岗位、不启动派发，组织原有暂停状态保持。连接测试也可能因推理 token 用尽或模型不支持结构化输出失败；明确调整配置后用新的请求再次测试，不静默降级。

## 2. 前端可直接使用的契约

沿用本机同源服务、HttpOnly 会话、Host/Origin 校验、服务端组织范围及董事会角色。启动服务后 API 默认开放配置入口，**不会自动调用**；`--disable-api` 可禁用入口。`GET /api/session` 的 `executors` 可能包含 `api`，不代表已经保存有效连接。

配置列表：

```http
GET /api/model-connections?organization_id=ORG_ID
```

响应含 `api_enabled`、默认 `api_connection_id`、`connections[]`。每项为 `{id, revision, config, has_api_key, updated_at}`；永不返回 API Key 或密钥后缀。仅董事会会话可读取；观察者仍可读取快照中的默认连接 ID 和公开执行依据。

写操作都使用现有接口：

```http
POST /api/commands
Content-Type: application/json
```

请求顶层固定：

```json
{
  "id": "unique-request-id",
  "organization_id": "ORG_ID",
  "base_version": 0,
  "kind": "api_connection",
  "data": {
    "connection_id": "primary",
    "config": {
      "name": "My model API",
      "base_url": "https://api.openai.com/v1",
      "model": "your-model-id",
      "response_format": "json_schema",
      "token_limit_field": "max_completion_tokens",
      "max_output_tokens": 4096,
      "timeout_seconds": 180,
      "enabled": true
    },
    "api_key": "<用户在密钥输入框填写的值>",
    "reason": "配置测试连接"
  }
}
```

`base_version` 来自最新快照；配置和绑定成功会增加组织版本，下一条命令需要新版本。连接配置命令只持久化完整参数的指纹，实际密钥仅保存到私有连接表；即使误把密钥粘进配置依据后被拒绝，也不把它存入命令日志。页面不得把密钥写入 URL、localStorage、日志或回执；提交后清空密钥输入，查询原请求回执即可。

| `kind` | `data` | 行为 |
| --- | --- | --- |
| `api_connection` | `connection_id, config, reason`；可选 `api_key` | 新建/更新版本。省略或 `null` 沿用密钥，空字符串清除。成功回执含脱敏 `connection` |
| `api_binding` | `connection_id, reason` | ID 为字符串绑定，为 `null` 清除默认；允许先绑定尚未填密钥的连接，但不能运行 |
| `api_test` | `allow_unknown_cost: true`；可选 `connection_id` | 受理 202 后在后台测试一次，省略连接 ID 使用默认；保持原暂停意图 |
| `start` | `executor: "api", max_steps, allow_unknown_cost: true`；可选 `connection_id, max_seconds` | 运行组织；不传 `model`，或传 `null`。模型固定为连接配置 |

`pause`、`reconcile`、事件及资源命令沿用原协议。新增操作与 CLI 共用派发锁；在途作业期间不能更新连接或绑定。连接停用、缺密钥、未接受费用条件、额度不足、金额硬上限、未知执行和版本冲突均在发起请求前拒绝。

重复请求 ID 返回原回执；相同 ID 携带不同密钥或参数会被拒绝，不再次发请求。网络断开后通过 `GET /api/receipts?organization_id=ORG_ID&id=REQUEST_ID` 核对。连接测试最终回执含 `status`、`run_id`、成功时的 `usage`，失败时有脱敏 `message`。受理不等于测试成功。

## 3. 执行、费用与恢复

每个作业开始时固定连接 ID、版本、请求模型和密钥快照；随后每次执行记录携带 `execution`，包含 `connection_id`、`connection_revision`、`protocol`、`requested_model`、`transport_source`。密钥不进入模型消息、工作包、事件、回执或执行文件。

用量记录包含供应商实际返回的 input/output/cached token、实际模型、响应 ID、`x-request-id`、耗时。供应商未提供的 token 不补 0。金额始终为 `cost=null, cost_status=unknown`，不接受未知计费下的金额硬上限。费用计账由后续适配负责，当前只约束调用数、请求输出限制和等待时间。

只发一次非流式请求，不自动重试、不跟随 HTTP 重定向，也不自动探测其它模型或输出模式。TLS 使用系统信任和证书校验；首版不自动使用环境 HTTP 代理，可配置供应商的 HTTPS 网关地址。回环服务可使用 HTTP，但总是标为 `local_test`，不能据此声称真实供应商 E1/E2 通过。

401/403、429、其它明确 4xx、重定向、截断/拒绝/工具输出和不符合 JSON 协议的结果失败；5xx、发出后断开、整体超时或宿主中断进入 unknown。所有调用保留额度。unknown 阻止新调用，按原核对入口处理，不因为本地线程结束推断供应商取消。

私有执行目录仍为 `executions/RUN_ID/`，API 路径保存工作包、schema、配置依据、已验证结果和脱敏回执；不保存供应商原始错误正文。API Key 存在组织 `state.sqlite3` 的私有 `model_connections` 表，正式状态只保存绑定 ID。数据库及运行目录不得上传 Git；本地管理员/操作系统是信任边界，Windows 使用用户目录访问控制，未声称提供加密 vault。

## 4. 验证与当前限制

本轮测试使用回环 HTTP 替身，验证传输、额度、持久化、组织协作机制与错误处理；真实付费供应商调用为 0。`evaluate` 已接受 `api` 执行器，但排除连接测试、fixture 和 `local_test`。真实 E1/E2 需要配置用户的凭据和有限资源后另行留存证据；小说发布、订阅和税费 mock 不等于真实市场反馈。

API 兼容性以每个供应商的连接测试及试跑为准。不支持原生 Anthropic、Responses、流式输出、工具调用、远程取消或自动重连。本轮未修改前端页面。
