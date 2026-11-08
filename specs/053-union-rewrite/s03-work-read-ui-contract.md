# U-081：核心任务页的 AI 工作读取（编码前冻结）

2026-11-08；上级 Kanban #22 / U-067，执行卡 #35 / U-081。
基线 `bbe8068335c32c04bdcf6d4fa20375245b912cf9`，预计 2–4 小时。

- 核心 `/tasks` 沿 Layout → GovernanceWorkspace 的真实路由显示既有 WorkPanel，保留 ResponsibilityWorkspace。不依赖只有 legacy 快照才能渲染的 Tasks 页面。
- 本次只读接入：展示当前 AU 的责任、预算、执行/未知、工具回执和成果下载；不开放 WorkPanel 旧的手工登记、预约、提交和采用按钮，不发起模型调用。自动派发与原请求恢复仍是父卡未完成的独立界面出口。
- 查询按 AU、当前主体和服务实例分隔；换主体/服务/AU 后不复用旧内容。只显示 `core.work.v1`、organization_id 和 principal_id 与当前受信投影相符的记录，错配时不给出记录或下载链接。
- 准备态、其他治理页面和 legacy 路由沿原行为；不改变支持的 schema、服务端权限或 API 写入契约。待复核的 schema 4 候选由原 PR 独立采用，本卡不先行合入。
- 严格 TDD：真实 Layout 路由缺失先 RED；接线后验证只读控件、错配投影、切换归属及准备/legacy 兼容。实际浏览器通过隔离临时服务验证显示、刷新和成果链接。所有替身证据均为受控工程，不关闭父卡真实验收。
