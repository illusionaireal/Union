# U-081 / Kanban #35：核心任务页显示 AI 工作与成果

2026-11-08；上级 #22 / U-067。执行者 chatGPT-online（Codex 当前会话），
分支 `codex/u081-work-panel`，集成基线 `bbe8068335c32c04bdcf6d4fa20375245b912cf9`。
本交付为受控工程候选，未部署、不调用真实模型，不关闭父卡的自动派发界面或真实验收。

## 结果与范围

真实 Layout 在核心 `/tasks` 分支调用 GovernanceWorkspace，绕过原 Tasks 页面；
因此只在旧 Tasks 挂载的 WorkPanel 对核心 AU 不可达。本候选在真实治理路由接入只读
WorkPanel，保留 ResponsibilityWorkspace。显示已有工作、责任、预算、执行/未知、
工具回执和成果下载；提供独立读取刷新，不开放原 WorkPanel 的手工写入控制。

读取缓存按 AU / 主体 / 服务实例分隔；改变作用域即卸载旧面板；协议、组织或主体不匹配
时不呈现记录和下载链接。未修改服务端权限、支持的 schema、派发事务或模型协议。
PR #24/#25 的后端候选和 PR #22 的真实验收 drivers 均未合入或编辑。

编码前复评发现旧 WorkPanel 没有安全的自动派发/原请求恢复界面，因此把本子卡明确限定为
可独立验收的读取结果；完整自动运行仍保留在父卡 checklist，未以拆分隐藏未完成目标。
预估 2–4 小时，冻结契约为 `specs/053-union-rewrite/s03-work-read-ui-contract.md`。

## 验证

- 路由回归先 RED：新增 8 项中 7 项因真实核心路由不呈现工作而失败，准备/legacy 兼容项通过。
- 最小接线后，新路由 8 项和原 WorkPanel 10 项全部通过，含记录/下载、刷新、无工作 POST、
  错配协议/主体/AU，以及切换主体/服务/AU 不重现旧内容。
- `npm run check` 通过：管理与计划检查、历史动作回归、类型检查、全部 215 项前端测试、构建。
  新读取请求使旧治理测试的“所有 fetch 都是命令 POST”替身失效；为其单独提供 coreWork
  读取替身后，原治理命令/回执断言保持不变并通过。
- 隔离 HTTP/SQLite 浏览器 fixture 已实际启动，产生来自回环模型替身的候选成果并正常清理；
  `node --check scripts/u081-work-read-browser.cjs` 通过。
- `.venv/bin/python -m unittest discover -v`：707 项通过，2 项平台跳过，267.625 秒。
- 当前提交的实际浏览器/远端 CI 结果仍待验收回写；不将未完成检查标为通过。

本机 Node 24.22.1（满足 package engines），Python 3.12.14；仓库 .nvmrc 固定版本由 CI 使用。
本轮修复了已有 `.venv/bin/python3` 缺失的环境链接，未修改项目依赖或锁文件。

## 实际浏览器的明确待验收项

本机没有 Chromium；Playwright 官方下载地址返回 HTTP 200、195 字节 HTML，无法解压成浏览器；
系统包安装也因 setgroups/seteuid 权限失败。未绕过环境权限，未用 DOM 测试替代实际浏览器。

现有 console-browser CI 保留全部步骤，新增以下同树检查和对应 artifact：

```sh
npm run build:console
UNION_PYTHON=python3 node scripts/u081-work-read-browser.cjs
```

检查使用隔离临时工作台、真实 HTTP/SQLite、显式回环模型替身和私有临时 cookie：核心路由
显示工作、真实鉴权下载、只读控制、刷新/重开、1440/390/320 宽度及零工作 POST。
输出 `.union/u081-work-read-browser/checks.json`；真实模型调用为零。
CI 或其他工程角色需以本候选的确切提交运行并给出回执，另核对读取身份隔离后再采用。

预先存在的 `services/modeld/vendor/opencode` 脏修改保留，未纳入提交；project.json 未被用作
任务准入或运行态镜像，长期证据以本目录交给协调者在交付采用时索引。
