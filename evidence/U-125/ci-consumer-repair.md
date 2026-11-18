# U-125：共享重启验收的处置

2026-11-18，候选 `348c82894000361510681bd95c1e2ba0040584f8` 的
`frontend and historical checks` run `44231413637`：Windows/Linux offline checks
通过，console-browser 在 U-086 observed-settlement 正常 unknown 例超时。
两种伪造 released 反例已按预期拒绝。失败日志保留在宿主私有验证目录。

该探针从 `scripts/exit22b_page.cjs` 提取重启片段，仍等待已退出当前 UI 的
“已连接本机服务”文字。新组织壳无需恢复该文字；这段证据的责任是实际
认证及持久化事实。只重绑共享片段为当前同源 `GET /api/session`，校验
HTTP 200、`core.au.v1`、非空实例及与重启前相同的 principal。
用 `require('node:url').URL` 解析 API 地址，保留 fixture origin 中历史路径的兼容。
初次直接使用全局 URL 时 VM 未提供该全局而失败；改用模块后重验通过。

原 snapshot、结算、预约、步骤/原执行身份和已采用成果断言保留。
没有新增恢复 POST、产品缓存、身份写入者或旧 UI 回退。其余四个探针保持原代码。
保留 shared driver 是因为这些有效合同测试仍消费其片段，不宣称其完整旧页面
runner 可用于新工作旅程；最终旧前端处置仍由 U-115 负责。

本机修复后读回五个完整 JSON：observed-settlement 3、budget-conservation 7、
result-provenance 10、reopened-download 11、material-read 10，均通过。
Node shutdown 辅助测试 2 项、实际 `npm start` 检查 5 项退出 0。
对应完整 Python 收据为 863 项、12 跳过、退出 0。
这些是受控本机 HTTP/SQLite/Chrome 证据，真实模型调用为 0。

变化必要性：`code-change`，共享验收消费者应读取实际 Core 身份契约。
修复形状：重绑失效的表示层断言到 session owner，不改变产品权限协议。
本机直接证据支持上述 scoped failure 的解释；远端最终 SHA 检查另行读回。
首次首页恢复与构建并发的失败原因仍未查明，此修复不声称解决该历史失败。

独立工程 reviewer 对本次两文件修复无剩余发现；实际探针 3、辅助测试 2、
临时 VM 身份/协议/401/实例反例与路径检查 5 项全部退出 0，详见
[独立报告](independent-review.md)。
