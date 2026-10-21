# 015 实际筹建准备与验证

2026-10-20，接续 dev / 4f5cbf4。新增公司准备、只读诊断、不启用 fixture 的真实工作台、有限 API 常驻监听包装与 systemd 模板。未变更资金或岗位授权机制，未合并 main。

## 工程验证

- `python-tests.log`：152项后端全量回归通过。之后收紧工具往返验证，要求同一真实连接版本及归档供应商回执；`corp-tests-final.log`：10项相关测试再次通过。
- `npm-check.log`：仓库计划完整性、9项旧动作安全检查及 npm check 命令记录；`console-check.log`：完整前端类型检查、16项测试与正式构建通过。
- `http-validation.json`：实际运行的公司工作台通过23项HTTP检查，包含React/JS/CSS、八页路由、本机一次性会话、无fixture执行器、观察者写入拒绝及真实待筹建状态；0模型调用。
- `systemd-validation.json`：用当前checkout替换模板 `/opt/union` 路径后，`systemd-analyze verify`退出0。未在真实主机安装、开机或掉电恢复验收。
- `scripts/check_corp_startup.cjs` 浏览器检查尝试未能启动，因为本环境没有Chromium（`/usr/bin/chromium`和Playwright缓存均无可执行文件）。没有浏览器截图或通过结论；HTTP检查不能替代视觉验收。

## 实际公司状态

公司 `org-eb1c6fc7e1784a52823f3d389f9cac34` 保存于被Git忽略的 `.union/ai-union-corp/`。目标、章程和累计最多32次/每次180秒资源已采用；当前bootstrap、暂停，0成员、0工作、0成果、0调用，source=not_run。正式工作台已启动并完成上述HTTP验证；这不是公司自主运营。该私有目录不随Git保存，新的环境须安全迁移或明确新建，不能伪装接续旧组织。

首次跨exec请求本机端口返回连接拒绝，原服务进程仍存活；当前工具命令各自处于网络隔离环境。改为在同一命令内启动服务并执行HTTP检查后通过，未改变网络策略。私有一次性链接和会话未进入本证据或Git。

## 外部条件核查及未完成

- 本环境未收到OpenRouter/HYB或其他模型key，也没有先前私有组织状态、可调用的Codex CLI。未提取或复制其他应用凭据。
- Cloudflare账户可读取Workers列表，现有 `union-guide` 为先前展示资源；本轮不修改。Containers列表实际HTTP401，明确说明需要Workers Paid套餐。没有升级、付费或部署，也没有把静态页面当运行时。
- 用户选择**已有服务器**；尚无SSH地址、用户名、端口/已配置认证引用，无法连接和部署。
- 成员运行时仍缺少真实代码仓库、测试与运维工具。宿主代理本次编写代码不等于成员自行开发；仍须工程实现及权限评审。
- 没有真实筹建、成员交付、持续自治、收入或法律实体设立证据。

继续步骤见 [CORP_STARTUP](../../docs/CORP_STARTUP.md)和[015未完成任务](../../specs/015-corp-startup/tasks.md)。
