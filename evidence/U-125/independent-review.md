# U-125 独立身份与恢复复核

2026-11-18，执行者 Codex/gpt-6.1-sol，独立工程 reviewer `review_u125`。
审查 working tree，基线 `2b3d281`；依据入口契约 E01–E05/E08、U-110 产品与前端契约。
审查不代替完整产品验收或合并授权。

独立审查先执行并复现三个 P2：

1. 列表页获知协议失配后，纯断网返回旧路由仍可复活 AU 缓存。
2. AU 读取返回 403 后，已打开的修章表单仍含旧正文。
3. 缺少部分作用域字段的历史创建引用既不自动读取，也没有显式查询入口。

协调者将反例纳入正式测试并观察 RED。另一个正常断网邻例的初始断言
误把本地预览等同于新写资格，随后按契约更正为“保留草稿、不产生 POST”。
修复分别位于 workspace 的身份/协议比较、GovernanceProvider 的草稿生命周期、
receipts 的引用归属分类；没有新增事实缓存或创建 writer。

重新独立执行三个反例和两个有效断网邻例：5 项全部通过。
正式入口、创建身份/回执、治理四文件 104 项通过，真实 HTTP 定向 18 项通过。
partial 引用仅显式读取，已知 principal/origin 不匹配仍拒绝；完整归属才后台查询。
拒绝/失配清受保护投影及草稿，原回执和引用继续保留。

最终 advisory readiness：无剩余阻断发现，可交付 PR。
最终 npm/Python 与修复后实际浏览器由协调者另行汇总；U-126 完整表单仍属下一项。

## 2026-11-18：共享重启验收的独立复核

独立工程 reviewer `review_u125_restart` 只读复核 `348c828 → WORKTREE`
的 `scripts/exit22b_page.cjs` 与 `browser-migration.md`，未发现阻断或其他问题。
重启片段读取同源 Core session 的协议/实例/原 principal，VM 的 `createRequire`
支持 `node:url`；原 snapshot、结算、预约、execution/result 和原回执断言保留。
只有 observed-settlement 消费此次改动区，其余四项保留原共享 helper 或 exit22c。
该验收代码重绑无需新增 ADR 或改变产品权限基线。

独立执行 observed-settlement 3 项、shutdown helper 2 项，以及临时 VM 中的
principal/协议/401/实例反例和路径检查 5 项，全部通过、退出 0；diff check 通过。
独立读回五份探针 JSON 共 41 项通过、Python 原日志与最终收据 863 项/12跳过/退出0。
完整 npm 与启动由协调者执行，reviewer 未重跑；最终远端 SHA/CI、PR/合入和
完整用户旅程仍须单独确认。首次 reviewer 请求因服务限流未执行，续跑后得到上述证据。
