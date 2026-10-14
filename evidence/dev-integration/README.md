# dev 三分支集成验证

2026-10-14。统一开发分支为 `dev`，保留三个源分支及提交历史，`main` 保持 `e11c389366814060ea4475a359c9b62036ccd176`。

| 源分支 | 合入的提交 | 内容 |
| --- | --- | --- |
| `feat/ai-union-runtime-console-handoff` | `cd6d06238b8bc79637b725f0041c9c32770f9352` | Python 运行时、本机组织工作台和模型设置 |
| `feat/real-model-api` | `6ce24b75e8cdcd3c60b4b5ee2091350d95845d3d` | 私有 API 配置、默认绑定、连接测试与真实执行器 |
| `feat/react-typescript-console` | `8179d6ee176360184ad159ffb6b3db4b53bb2bb4` | React / TypeScript / Vite 前端、SPA 服务及 CI |

## 合并与修正

解决 README、HANDOFF、STATUS 三处内容冲突，保留两侧成果、交接和历史证据。Python 服务同时提供 React 构建和 API 连接路由，未改变鉴权边界。

补齐前端接口兼容：API 执行器独立名称和默认绑定识别、有限调用费用确认、API 回执种类及 failed/blocked 状态、仅请求身份的恢复存储，以及连接测试核对文案。API 配置/绑定/测试暂通过 [API_MODELS.md](../../docs/API_MODELS.md) 的 CLI 或 HTTP 完成，已绑定的默认 API 可从 React 运行表单选择；专门的连接管理表单仍待后续前端接入。

## 实际验证

- `npm ci --ignore-scripts` 成功。
- `python3 -m unittest discover -v`：78 项通过（原前端 55 项与 API 23 项合并）。
- `npm run check`：82 项历史计划、181 条依赖、9 项旧平台动作测试、严格类型、12 项前端测试和 Vite 生产构建通过。
- `python3 scripts/check_console_start.py`：5 项通过，包括一条命令启动、深层 SPA 路由、同源 CSP、静态脚本、会话及未知资源边界。
- `git diff --check` 及源分支包含关系检查通过。
- [独立工程复核](../../docs/reviews/2026-10-14-dev-integration.md)通过，无阻断问题。

## 限制

当前环境没有 Chromium，Playwright 下载得到无效 ZIP，未完成本次 60 项浏览器流程复验。保留原前端分支的浏览器证据和 CI 浏览器任务，不把历史结果当作当前合并结果。真实供应商调用 0，未部署、未进行真实小说发布或市场反馈验收。

公开摘要保存于 `validation.json`，运行数据库、密钥和私有日志不提交。
