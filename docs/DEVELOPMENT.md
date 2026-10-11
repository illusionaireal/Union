# 从新环境接手开发

更新：2026-10-12（北京时间）。面向只有 GitHub 仓库、没有上一轮聊天或云环境快照的开发者。

## 1. 读取顺序与当前任务

先读 [当前状态](ai-union/STATUS.md)、[工程交接](../HANDOFF.md)、[PRD v0.2](PRD.md)和[产品设计](product-design.md)。下一工程任务是 [004 组织操作工作台](../specs/004-organization-console/tasks.md)的 W2–W7；[003](../specs/003-runtime-dashboard/spec.md)是观察模块，不能把整个产品继续做成只读 Dashboard。

已实现 Python 本地运行时和 CLI、静态展示页、操作设计原型。实际网页会话、读写服务、暂停协议尚未实现。真实模型调用为 0；不用获取模型凭据就能继续本地 fixture 开发。

原治理设计在 `docs/ai-union/DESIGN.md`，最初开发任务在同目录的 `DEVELOPMENT.md`，上传原件在 `docs/inputs/`；它们保留来源，不代表当前完成状态。旧 UNION 平台在 `docs/baseline/`、`docs/kickoff/` 和 `spikes/`，继续保留独立任务线及历史编号。

## 2. 工具和首次验证

运行时使用 Linux、Python 3.11+（本轮验证 3.12.14）、SQLite 标准库；互斥使用 `fcntl`，未声明 Python 运行时兼容 Windows。无需 pip 包、数据库服务或 API Key。

旧平台检查和浏览器工具使用 `.nvmrc` 指定的 Node.js 24.19.0。安装对应版本后，从仓库根目录执行：

```bash
python3 -m unittest discover -v
npm ci --ignore-scripts
npm run check
```

Python 测试验证组织机制和执行器接口替身；Node 检查历史计划完整性与旧动作安全实验。两者都不调用模型，不证明真实组织能力。两个 CI 工作流分别执行这些范围；本地浏览器验证不自动等于远端 CI 通过。

## 3. 重建完整模拟场景

以下目录必须不存在；再次运行选择新的目录，不重置原组织或覆盖历史证据：

```bash
python3 scripts/validate.py \
  --root .union/first-fixture \
  --output .union/first-fixture-evidence
python3 -m ai_union --root .union/first-fixture status
python3 -m ai_union --root .union/first-fixture context --work-id work-followup
```

脚本预期退出 0，包含 25 项机制／接口测试与 CLI 场景，得到 2 名成员、3 项工作、3 份模拟文本成果和 6 次 fixture 调用。内部 `evaluate` 返回 3 表示模拟结果，脚本按此预期检查；不要将其修改为真实通过。

不依赖 `.union/validated-final`、`/tmp` 目录、旧登录、进程或端口。新环境自己生成 fixture；数据库、`board.key` 和私有执行记录留在被忽略的 `.union/`，只有公开证据进入 Git。

## 4. 原型与浏览器验证

入口为 `ai-union-progress.html`（进展展示）和 `ai-union-dashboard-prototype.html`（组织操作设计）。后者沿用文件名，现含七视图和操作流程。两者均可单独分发，不连接真实组织服务。源文件在 `site/` 和 `design/dashboard/`。

```bash
python3 scripts/build_site_data.py
python3 scripts/build_single_html.py
python3 scripts/build_dashboard_prototype.py
```

`build_site_data.py` 只使用 `evidence/001-org-bootstrap/` 的历史公开快照；重跑开发测试不要求改写它。更换展示依据时同时复核来源、摘要和模拟标记。

浏览器测试需要 Chromium 和独立工具依赖，网站本身不需要 npm 包。Linux 上先安装系统 Chromium（如 Debian/Ubuntu 的 `chromium` 包），然后：

```bash
UNION_BROWSER_TOOLS="$(mktemp -d /tmp/union-browser-tools.XXXXXX)"
npm install --prefix "$UNION_BROWSER_TOOLS" --cache "$UNION_BROWSER_TOOLS/npm-cache" --no-save --package-lock=false playwright-core@1.64.0
export UNION_PLAYWRIGHT_MODULE="$UNION_BROWSER_TOOLS/node_modules/playwright-core"
export UNION_CHROMIUM_PATH="$(command -v chromium)"
node scripts/check_dashboard_design.cjs
node scripts/check_console_design.cjs
UNION_SITE_SINGLE_FILE=ai-union-progress.html node scripts/check_site.cjs
```

预期分别为 48、32、43 项通过；脚本会更新 `evidence/design/` 或 `evidence/site/` 的报告和截图，提交前检查变化。断网测试用 `setContent` 加载完整 HTML；直接 `file://` 导航未在受管理浏览器验证。

多文件展示页检查先在另一终端启动服务：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

然后在设置好浏览器变量的终端执行 `node scripts/check_site.cjs`，预期 37 项通过；结束后关闭自己启动的服务。

## 5. 后续实施与完成定义

| 顺序 | 任务 | 完成证据 |
| --- | --- | --- |
| 1 | 004 W2 受信会话与组织范围，服务端校验角色、来源、版本和权限 | 观察者直接调用写接口被拒绝，密钥不进入浏览器。 |
| 2 | 003 观察服务及 [review](../specs/003-runtime-dashboard/review.md) 两项修复 | 活跃执行不误报；同版本事件／用量更新、乱序及恢复通过 A01–A10。 |
| 3 | 004 W4–W5 幂等命令、作业与持久暂停意图 | 暂停停止新派发并等待在途回执；未知结果核对，不退款或盲目重派。 |
| 4 | 004 W6–W7 前端接入实际服务 | 浏览器 fixture 闭环及 C01–C09，通过真实接口验收，不以模拟成功回退。 |
| 5 | 有限真实 Agent 与业务接入 | 明确调用范围和费用未知条件后记录 E1/E2；真实交付／反馈另需渠道。 |

现有 `runner.exclusive` 保护运行与管理变更；新增 API 不得绕过它。当前没有跨进程暂停协议或远程取消确认，不能将原型状态变量当实现。ERP／CRM 等按 [软件复用方案](software-reuse.md)接入。

资金和权限实现采用前需要另一工程角色复核；此次交接不表示生产采用获准。新缺口同步 STATUS、HANDOFF、Spec 与 Tasks，保留失败证据。

## 6. 可直接交给下一开发者的任务

> 阅读 AGENTS.md、docs/ai-union/STATUS.md、HANDOFF.md、docs/DEVELOPMENT.md、docs/PRD.md 和 docs/product-design.md。基于已有 Python 运行时和操作原型，继续 specs/004-organization-console/tasks.md 的 W2–W7，同时实现 specs/003-runtime-dashboard 的观察要求。先在新目录复现 fixture 和两套既有测试；不要重做已完成原型，也不要继承旧平台任务优先级。修复执行活性与同版本更新问题，以实际服务及浏览器证据验收 A01–A10、C01–C09。真实模型、渠道或部署条件缺失不阻止 fixture 开发；不得以模拟宣称真实能力或上线。完成后同步交接和验证记录。
