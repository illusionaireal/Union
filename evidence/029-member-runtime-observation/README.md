# 029 成员运行观察：受控实现记录

2026-10-30；实现基线 `dev@594cdbf`（本轮工作树）。本记录只覆盖 U-041 的受控实现切片，不关闭 U-041，也不证明真实托管、成员自主运行或浏览器验收。

## 已实现

- 新增 `runtime_view.py`：从现有组织状态、工作、运行回执、会话表和工作区绑定生成只读 `runtime` 与 `member_execution` 摘要。
- `snapshot` 返回该投影；读取不登记运行时、不写心跳、不恢复会话、不派发任务，也不调用模型、容器或 systemd。
- 成员状态明确区分 `executing`、`ready`、`waiting`、`blocked`、`idle`；未知/失败运行、等待依赖、暂停和预算限制保留原因码，不能以 idle 覆盖。
- React 的成员页显示每位成员的工作、会话摘要和状态；资源页显示嵌入式运行位置、活性和派发状态。
- 投影不返回业务工作区路径、容器名、凭据、检查点正文、消息、PID 或宿主 activity owner。

## 本轮受控检查

- `python3 -m unittest tests.test_console -v`：27 项通过，包含新增只读、无私有宿主细节测试。
- `npm run typecheck --workspace @union/console`、`npm run test --workspace @union/console`（22 项）与 `npm run build:console`：通过。
- `npm run check:management`：通过（15 模块、8 里程碑、43 任务）。
- `npm run check` 的 Node/管理/React 部分通过；系统 Python 的完整 unittest 在既有 Harness 依赖缺失处失败，失败项需要 `deepagents` / `langgraph`，不是本投影测试失败。
- `npm run test:browser` 未能启动：当前环境缺少 Playwright Chromium 可执行文件 `/root/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`。未伪造 A11 或截图结果。
- 2026-10-30 重试仓库 CI 同用的 `npx playwright-core install chromium`：连续下载 `Chrome for Testing 156.0.8078.4` 均显示 0 MiB，解压报 `End of central directory record signature not found`，最终以下载失败退出。未安装系统依赖、未改动项目配置；这是环境下载内容截断，不是浏览器用例失败。

## 未通过范围与后续

U-041 仍需在带 Chromium 的环境完成 A01–A06/A11 浏览器验证，并由独立工程角色审查新增观察面权限。U-042 的托管控制、真实主机/模型、Docker、恢复和持续运行仍未实现或验收；本轮没有变更任何宿主、运行时注册、组织身份、权限或生产环境。

## 追加：组件行为覆盖

本轮新增 `RuntimeObservation.test.tsx`，以两名成员的只读快照验证成员身份与工作状态分列、等待原因可读、嵌入式本地位置与未知活性不会伪装为受管服务，并检查页面不渲染工作区路径或容器详情。前端总计 22 项通过；定向 Python 现为 27 项通过。该覆盖仍是 JSDOM 组件测试，不替代真实 Chromium 的响应式和浏览器交互验收。
