# HYB 接口访问与项目级 goals

2026-10-18（北京时间）。基于 `dev` / `f0839d7`。本次使用用户指定的 `https://ai.hybgzs.com/v1`、`hyb_key`、`hyb_model`，没有再调用 OpenRouter，也没有重放历史未知请求。

最初新变量未注入，CONNECT 被宿主代理拒绝。用户更新权限/环境后重新检查：环境工具为 `observations_current=true`，网络 `enforced`，`hyb_key` 与 `hyb_model` 均 `ready`，实际进程也已包含两个变量。后续 HTTP 403 发生在这次配置生效之后，不能继续解释成变量缺失或要求再次填写密钥。

## 实际接口结果

- 使用绑定凭据访问 `GET /v1/models`，收到 HTTP 403、HTML 标题“访问已被拦截”，带 `CF-Ray: a4c235c6d93da4aa-GRU`。这是站点防护页面，不是有效模型列表。
- `hyb_model` 实际包含两行候选标识。整串直接配置时被模型名称校验拒绝，尚未发出请求；随后按配置顺序取第一个非空行，两个候选均符合现有标识规则，没有修改校验或猜测型号。
- 通过项目 `APIExecutor` / `test_tool_connection` 向正式 `/v1/chat/completions` 发出 **1 次**真实请求，HTTP 403，运行 `failed`，没有完成第一步工具调用。未自动重试，也没有继续尝试其他模型。
- 项目按通用 403 分类记录 `api_authentication`。该分类不能区分防护拦截、模型权限与密钥认证，当前证据不能证明用户提供的 key 无效，也不能证明实际生成成功。
- 没有供应商生成 ID 或 token 回执，费用保持 `unknown`，未填为零；没有启动新小说公司，三章、经营周期与质量均未因此验收。

实际回执见 [访问摘要](access-summary.json)。私有原始工作包、连接配置、数据库保存在本机 `.union/hyb-first-release-20261017-205726/preflight/`，被 Git 忽略，不随仓库提交。公开记录省略密钥和模型变量值。

继续条件是接口方核对该环境对 `/v1/chat/completions` 的 POST 403、API 访问权限及正常客户端访问策略；模型列表端点另有上述防护页面和 Ray ID 可供排查。没有绕过宿主代理、修改 TLS 校验或伪装浏览器访问。HTTP 403 与本机文件挂载权限是不同问题。

## goals 与沙箱

用户要求执行 `codex features enable goals`，并在设置完全访问权限后再次尝试。两次仍无法写入只读挂载上的 `/run/codex-environment/codex-home/config.toml`。

已新增项目 `.codex/config.toml`：

```toml
sandbox_mode = "workspace-write"

[features]
goals = true
```

在 `/workspace/Union` 运行 `codex features list`，退出 0，实际显示 `goals stable true`。这证明新 CLI 调用读取了项目配置，不代表当前托管会话热更新了功能或权限，也没有让全局只读挂载变成可写。临时 `--enable goals` 覆盖也曾验证成功，但最终项目验证没有使用该覆盖参数。

没有重定向 `CODEX_HOME`、复制全局认证文件或修改系统挂载。项目配置不包含凭据。业务代码、权限机制、账本和历史证据未改动。本轮 `npm run check` 通过（历史 Node 9 项、前端 16 项、类型检查及构建），后端 136 项通过；见本目录日志，实际 API 结果单独报告。
