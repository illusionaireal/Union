# 075：CI `A01` 浏览器失败诊断（团队动态 #4 求助的回复）

2026-11-08 06:04–06:30。`chatGPT-online` 在团队动态留言 **#4** 报告：PR #15 的 `console-browser` 在 `scripts/check_console.cjs:66` 断言 `A01: fresh service has a clear empty state` 失败，请求工作台/浏览器验收负责人定位。本轮在本地复现并给出根因与最小修复建议，已回复到留言板（**回复 #6**）。

## 结论

**不是 PR #15 的回归，也不是 CI 环境问题**：`scripts/check_console.cjs` 仍在断言**已退役的单 HTML 工作台 DOM**（`#org-select`、`#role-label`、`data-command`），而服务现在只提供 React 构建产物（`web/console/dist`，见 `ai_union/server.py` 的 `static_dir` 默认值）。因此该断言在当前代码上**必然失败**。

## 本地证据（HEAD `993fed7`，Windows + Chrome，全部使用临时目录与回环替身）

| 命令 | 结果 | 日志 |
| --- | --- | --- |
| `npm run test:browser`（旧单 HTML 脚本） | **FAIL**：`scripts/check_console.cjs:66` A01，与 CI 同一断言 | [`browser-legacy-fail.txt`](browser-legacy-fail.txt) |
| `npm run test:workspace`（当前 React 门槛） | **PASS 71 项** | [`workspace-pass.txt`](workspace-pass.txt) |
| `node scripts/check_core_creation.cjs`（S01 门槛） | **PASS 30 项** | [`core-creation-pass.txt`](core-creation-pass.txt) |
| `npm run test:model-service-browser` | **PASS 8 项** | [`model-service-pass.txt`](model-service-pass.txt) |
| `npm run test:novel` | **FAIL**：`scripts/check_novel_company.cjs:14` "Settings has configuration actions without repeated create/run buttons" | [`novel-fail.txt`](novel-fail.txt) |

`test:novel` 是**同一类问题**：脚本用 `data-nav` / `data-command` 旧选择器导航，页面没切换，于是把 Overview 上的 `create`/`start` 当成 Settings 页上的按钮。**只修 A01 不能让 CI 变绿**，因为 console-browser 步骤里 browser 与 novel 两段都是旧契约。

## 最小修复建议（未擅自实施）

1. `.github/workflows/ci.yml` 的 `console-browser` 步骤改为运行当前 React 门槛：`npm run test:workspace`、`node scripts/check_core_creation.cjs`，保留 `npm run test:model-service-browser`；
2. `scripts/check_console.cjs`、`scripts/check_novel_company.cjs` 标注 legacy 并从 CI 阻止性步骤移除（旧单 HTML 已按用户要求退役，见 `docs/site.md`）；006 小说场景的 Python 机制测试继续保留；
3. 若仍要求覆盖旧 UI，只能重写这两个脚本（成本≈复制 `check_workspace.cjs`），不建议。

**这属于"验证范围变更"，需要卡片负责人或用户确认**，所以本轮只给诊断与建议，没有改动 `ci.yml`、`package.json` 或任何脚本。

## 边界

- 本轮**没有**提交除本目录外的任何仓库文件；同工作树另有 agent 的未提交改动（`management/project.json`、`PROJECT.md`、`TASKS.md`），已回避。
- 真实模型调用 **0** 次；未部署；未修改 main/dev。

## 更正（2026-11-08 06:12，team-feed #8）

本文件初版有一处**结论错误**，已由 `codex-home`（团队动态 #7）指出并经源码核对确认：

- 错误说法："`#org-select` / `#role-label` / `data-command` 都是旧单 HTML 的 id/属性，React 页面不存在"。
- 事实：这些选择器**仍然存在** —— `web/console/src/app/Layout.tsx:129`（`id="org-select"`，全新服务时 option 为"尚未创建 AU"）、`Layout.tsx:173`（`id="role-label"`）、`web/console/src/features/commands/CommandProvider.tsx:218`（`data-command={kind}`）。
- 因此 A01 的真正失败点更窄：S01 之后全新服务的落地页改为 `CreateAUIntro`（`web/console/src/pages/Overview.tsx:12` 的 `if (!d) return <CreateAUIntro />`），而 `SetupGuide`（`aria-label="公司启动准备"`）只在有快照且无活动时渲染（`Overview.tsx:79`）。**旧空态区域已不是当前全新服务的空态**，断言因此必然失败。
- 修复方向（`codex-home` 在 U-080 推进）：把 A01 断言改为「创建AU」区域 + `create_v1` 禁用 + 保留 legacy 兼容按钮；`scripts/check_console.cjs` 与 `check_novel_company.cjs` 归 U-080，不由本任务改动。
- 本目录下的本地运行证据（`test:browser` FAIL、`test:workspace` 71 PASS、`check_core_creation` 30 PASS、`test:model-service-browser` 8 PASS、`test:novel` FAIL）**未受影响**，仍然有效；被纠正的只是对失败原因的文字解释。
