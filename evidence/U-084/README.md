# U-084：从页面运行已登记工作，恢复原请求

2026-11-08。执行卡#38，父卡#22；actor为Codex / GPT-6，在线成员为
chatGPT-online（54f3ed9e-817b-482a-90c1-d46bfc01728c）。基线86f283a。
一个4–8小时的页面/API/原请求身份闭环，没有重新实现服务端执行循环。

## 变化

核心/tasks在原只读WorkPanel中提供独立的自动执行区，旧手工登记、预约和
提交仍隐藏。未开始的工作先显式准备attempt，再显式run_loop。每次POST前
重验当前session、工作权限和版本；身份元数据先写sessionStorage。只保存
原ID/kind/base_version及主体/服务/AU/工作，不能保存目标、正文或凭据。

响应丢失/重开只查询原治理回执，不生成替代请求或自动重发。确认回执绑定
原ID、主体、AU、kind及版本；采用前再次读取session。unknown和404不能
视为未执行；旧服务的stale尝试、未知预约、撤权或已交付工作没有新派发入口。
已确认引用保留，下一轮显式工作流程另行设计。长run_loop不套用读取请求的
五秒超时，不改变服务器/modeld任务期限。

## 已执行验证

- 原实际页面缺失控件：四项行为测试RED；最小接线后GREEN。
- stale尝试反例：一项RED（其他八项通过），补充只读stale字段后拒绝派发。
- npm run check通过，包括231前端、37管理和9动作检查。
- 新的真实HTTP/SQLite测试通过：loopback modeld一次POST产生成果，重启后
  查询原循环回执、读取工作并下载原结果；第二次模型POST为零。此测试明确
  使用替身，不能声称真实供应商/资料业务验收通过。
- 初次Python全量754项、3跳过通过；新增HTTP测试又单独通过。当前全部
  源码的完整全量正在重新执行，最终结果回写原卡，不提前断言通过。
- 本地实际浏览器入口已尝试，因Chromium可执行文件缺失而未执行页面断言。
  新CI步骤运行同一个React+HTTP/SQLite浏览器检查，等待准确提交的结果。

运行：

```sh
npm run check
.venv/bin/python -m unittest discover -v
.venv/bin/python -m unittest -v tests.test_page_execution_http
UNION_PYTHON=.venv/bin/python node scripts/u084-work-execution-browser.cjs
```

浏览器脚本在真实命令提交后丢弃响应，刷新页面，再查询原ID；检查一次
work POST、持久成果下载及三种宽度。所有host/token均为临时测试夹具，公开
证据只包含检查汇总/原测试ID，不含宿主配置或凭据。见[冻结契约](../../specs/053-union-rewrite/s03-page-execution-contract.md)。

## 采用门禁

本提交是工程候选，需准确head的所有CI和另一工程角色的身份/权限复核。
不修改父#22原负责人，不关闭U-085真实成果或U-086真实中断出口。
真实模型调用0；没有部署、资金/密钥操作或数据库迁移。保留vendor原有
未提交内容；不把management/project.json历史状态用作准入或回写运行态。
