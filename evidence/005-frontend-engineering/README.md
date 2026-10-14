# 005 · 工程化前端验收

日期：2026-10-14（北京时间）。接续远端实现基线 `cd6d062`，正式前端使用 React + TypeScript + Vite、React Router、TanStack Query。代码为七页、API、组件、命令与详情模块，构建由现有 Python 同源提供。旧单 HTML 演示、报告和 004 证据保留。

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| Python 机制、API、静态路由和路径边界 | 55 项通过 | `python-unittest.log` |
| TypeScript、前端交互/数据、Vite 构建 | 严格类型通过，10 项测试通过，生产构建通过 | `engineering-check.log` |
| 历史计划和旧动作安全 | 82 项任务、181 条依赖核对，9 项测试通过 | `engineering-check.log`；不是组织能力验证 |
| 实际 HTTP + Chromium | 60 项通过 | [browser-validation.json](browser-validation.json)，包含构建资产 SHA-256 |
| 一条命令启动 | 5 项通过 | [startup-validation.json](startup-validation.json) |
| 桌面／移动设计 | 1440、1024、390、320 像素流程检查；无文档横向溢出 | [桌面](overview-1440.png)、[移动](settings-390.png) |

环境：Linux、Python 3.12.14、Node 24.19.0、系统 Chromium（精确版本见 JSON）。安装使用锁文件 `npm ci --ignore-scripts`，缓存位于 `/tmp/union-npm-cache`。真实模型调用 **0**；fixture 及 Codex 执行器替身均明确模拟。没有外部发布、Sites 站点或 Figma/Canva 文件。

## 覆盖关系

保留原 004 的 C01–C10 与 003 的 A01–A10 检查：创建、运行/暂停、模型配置、资源/章程、事件、unknown 核对、只读会话、实际成果校验、同版本新快照、乱序响应、断开/重连、组织隔离和服务重启。源码为 `scripts/check_console.cjs`。

新增 F02–F05 对应：路径路由直接访问、前进后退、深链接刷新保留组合筛选、一次性凭据从地址栏移除、自动轮询保留表单与焦点、关闭不提交，以及生产 SPA 的同源 CSP。启动检查验证真实 `npm start` 构建、深路由、脚本、会话及缺失资产 404。Python 新增的两个 HTTP 测试验证全部页面、资产类型、来源限制、缺失资源、编码路径穿越和私有文件边界。

前端单元/交互测试覆盖：请求超时/取消/不重试、单调回执、请求身份恢复、轮询保留输入与焦点、必填空格/模型格式/清除默认值、真实执行费用确认，以及快速连续 URL 编辑不恢复旧筛选。没有以测试数量证明真实 AI 能力。

## 迁移中发现及修复

1. 快速清空筛选后选择成员，React Router 的异步导航会沿用旧搜索参数。参数更新现依据当前浏览器 URL 合并，并有专门行为测试与实际浏览器检查。
2. TanStack Query 默认离线暂停会保留上次成功连接状态。读取改为明确处理离线状态，立即过期并禁用写操作；POST 不进入联网后自动执行的队列。断网/恢复与迟到响应检查通过。
3. 新建目标不再预填行业实例，验收脚本显式提供测试目标。成员/岗位/工作仍由运行时决定。
4. 新增轮询测试最初试图点击模态框后的刷新按钮，原生 dialog 正确阻止点击。脚本改为等待实际自动快照更新，再检查编辑内容和焦点。

## 重跑及范围

从根目录执行 `npm ci --ignore-scripts`、`npm run check`、`python3 -m unittest discover -v`、`python3 scripts/check_console_start.py`；设置系统 Chromium 路径后执行 `npm run test:browser`。默认浏览器结果写入 `.union/`，新公开证据使用新的 `UNION_CONSOLE_EVIDENCE` 目录，不覆盖本记录。

本记录证明 Linux 仓库工程、同源本地运行和模拟操作闭环。Windows React 迁移实机和远端 CI 结果尚未取得；已配置对应 CI。真实执行器烟雾、E1/E2、真实交付与经营反馈仍独立验收。
