# OpenRouter 免费模型测试与旧演示清理

日期：2026-10-18（北京时间）。基于实际远端 `dev` / `d297c21`；该分支已包含 React 前端、模型 API 及 010 Harness。独立单 HTML 演示已按用户要求删除，正式 React 工作台继续维护。历史验收目录未改写。

## 真实供应商测试

复用当前云环境的 `openrouter_key`，只使用实时目录中带 `:free` 且 prompt/completion/request 价格均为 0 的模型。密钥及本机访问凭据未写入公开证据或 Git。直接请求还限制 prompt/completion 价格为 0，未切换收费模型。

| 尝试 | 实际结果 | 证据 |
| --- | --- | --- |
| Gemma 免费模型 | HTTP 429，供应商限流，未取得生成结果 | `attempt-1-gemma-rate-limit.json` |
| Liquid，输出上限 64 | HTTP 200，64 token 全用于推理，正文为空，finish_reason=length | `attempt-2-output-limit.json` |
| Liquid，尝试关闭推理 | HTTP 400，该端点强制推理，不能关闭 | `attempt-3-reasoning-required.json` |
| Liquid，输出上限 512 | HTTP 200，正文严格为 `OPENROUTER_FREE_OK`，stop；106 输出 token（95 推理），约 2 秒 | `attempt-4-success.json` |
| 原项目 CLI | 连接建立前失败：旧 `http.client` 传输未读取 HTTPS 代理 | `project-before-proxy.json` |
| 修复后项目 CLI，输出上限 1024 | `api-test` 成功，59 输入/90 输出 token，约 1 秒；原失败运行及占用保留 | `project-cli-success.json` |

实际可用模型为 **`liquid/lfm-2.5-2.6b:free`**，供应商 Liquid。共 6 次探测尝试，其中 1 次在项目建立连接前失败、2 次请求被 HTTP 拒绝、3 次取得生成结果。没有对超时或未知结果进行重放。

通过 OpenRouter 的生成查询 API 核对了 3 个生成 ID，均返回 `total_cost: 0`，见 [费用记录](provider-billing.json)。项目自身仍保留 `cost: null / cost_status: unknown`，未以目录价格篡改账本或自动核销。这些测试仅验证普通文本对话和项目连接链路，不证明工具兼容、组织筹建、小说三章质量或经营闭环。

## 修复与回归

API 客户端现在遵守宿主 HTTPS_PROXY/https_proxy 与 NO_PROXY，使用 HTTP CONNECT 及默认目标 TLS 校验。代理认证仅发送给 CONNECT；本地 HTTP 测试继续直连。无支持的代理格式时失败，不绕过已配置路由；维持原请求截止时间、取消和未知执行语义，不引入重试。

新增 5 项代理行为测试覆盖隧道路由、TLS 验证、NO_PROXY、回环测试、代理认证范围及不支持配置的拒绝。完整后端、前端及启动结果见本目录 `python-tests.log`、`npm-check.log`、`startup.json`。后端 136 项、前端 16 项、启动 5 项全部通过，历史 Node 9 项和生产构建也通过。未重跑未更改的旧演示验收，也未覆盖历史证据。

## 当前工程入口

旧根目录四份演示/报告 HTML，以及 `site/`、`design/dashboard/`、`design/console-legacy/` 和专用生成/发布/验收工具已删除。`web/console/index.html`、React/Vite 工程、Python 服务和小说业务模拟场景保留。首次安装后使用 `npm start -- --open`；当前产品与开发分支为 `dev`。
