# 仓库交接验证

日期：2026-10-12（北京时间）。本次在完整本地成果与远端 `main`（`e11c389`）整合后的工作区执行。真实模型调用 0，无发布、支付或业务系统调用。

| 检查 | 实际结果 | 记录 |
| --- | --- | --- |
| `python3 scripts/validate.py --root .union/handoff-2026-10-12 --output evidence/handoff-2026-10-12/runtime` | 退出 0；25 项机制／接口测试通过；两成员、三工作、三成果、六次 fixture；新进程恢复无额外调用 | `runtime/`，内部 evaluate 按预期退出 3（模拟）。 |
| `npm ci --ignore-scripts`、`npm run check` | 退出 0；82 项历史任务、181 条依赖、5 份基线校验及 9 项旧平台实验测试通过 | `summary.json`；旧平台源码和基线与远端保持一致。 |
| 独立目录安装 `playwright-core@1.64.0` | 退出 0；显式采用可写工具目录作为 npm cache，不依赖用户 HOME | [新环境说明](../../docs/DEVELOPMENT.md)。 |
| `node scripts/check_dashboard_design.cjs` | 48 项通过 | [观察交互](../design/browser-validation.json)。 |
| `node scripts/check_console_design.cjs` | 32 项通过 | [操作交互](../design/console-validation.json)。 |
| `UNION_SITE_SINGLE_FILE=ai-union-progress.html node scripts/check_site.cjs` | 43 项通过 | [单 HTML 展示](../site/single-file-validation.json)。 |
| 生成器、文档本地链接、差异空白与历史保留检查 | 通过；旧平台基线、任务与离线实验没有被本次实现覆盖 | `summary.json` 与 Git 差异。 |

浏览器脚本用新安装工具，断网文档加载，网络请求与脚本错误为 0。直接 file 导航、远端 CI、真实网页 API、真实 Agent、Cloudflare 发布不属于本次已通过项。

原验证证据保留在 `evidence/001-org-bootstrap/`；新运行目录含数据库和董事会密钥，位于被忽略的 `.union/`。本目录只包含可公开的 fixture、命令结果与摘要。新环境按 [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md)重建状态，无需取得这些私有运行目录。
