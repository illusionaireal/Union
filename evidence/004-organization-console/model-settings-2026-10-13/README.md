# 管理后台模型设置增量

基线 `4e7b4e8`。用户要求在管理后台配置模型，本轮补齐“组织设置 → 模型设置”及启动时的本次覆盖。配置按组织保存，留空使用 CLI 默认；保存本身不连接模型服务、不增加调用、不启用真实执行器。

## 验证与 review

| 范围 | 最终结果 | 证据 |
| --- | --- | --- |
| Python 全套 | 53 项通过；包含配置持久化、越权和运行中拒绝、默认／覆盖／清除、参数传递、原请求固定模型，以及 CLI run/watch 的模型与资源交错检查 | [日志](final/runtime-reviewed/tests.log)、[命令与源码快照](final/runtime-reviewed/validation.json) |
| 浏览器与实际 HTTP | 53 项通过，其中新增 8 项 C10 检查 | [检查清单](final/browser-validation.json)、[设置页手机截图](final/settings-390.png) |
| 完整 fixture | 两成员、三工作、三成果、六次模拟调用；重启等待；evaluate 预期退出 3 | [运行](final/runtime-reviewed/fixture-run.log)、[评估](final/runtime-reviewed/fixture-evaluation.json) |
| 历史平台 | Node 24.19.0 的 `npm run check` 通过；82 项任务、181 条依赖、5 份基线、9 项动作安全测试 | [日志](final/npm-check.log)、[退出码](final/npm-check.json) |
| 独立工程审阅 | 检查模型参数、授权、事务与并发边界；修复 CLI 在锁前选择模型及检查金额硬上限的两项竞态 | [review](../../../docs/reviews/2026-10-13-model-settings.md) |
| 单页 HTML 报告 | 离线文件打开、复制命令、打印入口与键盘展开通过；1440／390／320px 无横向溢出、无网络请求或 JS 异常 | [验证记录](final/report-validation.json)、[桌面](final/completion-report-1440.png)、[手机](final/completion-report-390.png) |

运行环境：Windows、Python 3.13.14、Node 24.19.0、Chrome 154.0.8037.99。**真实模型调用为 0**。浏览器测试通过私有 stdin 启用 Codex 接口替身，并始终拒绝真实 Codex 调用；验证配置传递，不宣称模型可用或真实运行成功。

`final/runtime/` 保留第二项审阅修正前的 52 项结果；最终采用 `final/runtime-reviewed/` 的 53 项结果。首次浏览器在切回后台标签页点击时等待超时，记录保留在本目录；测试显式激活主标签页后，完整重跑通过。旧工作台验收目录没有覆盖。

复盘：模型名称属于可变运行配置，必须与资源条件一起在派发锁内解析；设置成功、请求指定模型和真实模型可用是三个不同事实。默认配置后续变化不改变已受理作业或旧回执。真实调用仍受宿主启用、会话权限、有限额度和费用确认约束。

使用方法见 [CONSOLE.md](../../../docs/CONSOLE.md)，简版见 [单页完成报告](../../../ai-union-completion-report.html)。
