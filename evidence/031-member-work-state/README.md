# 031：成员工作状态与交接会话引用修复

2026-10-31 02:35起（UTC+8）；基线 `dev@ed0d411`。这是外部工程协作和受控回归，不是公司成员自主交付、真实供应商运行或VPS常驻链验证。

## 核查结论

- 开始时dev领先远端7提交，tracked工作区干净；未跟踪的用户docs/research/保持原状。远端dev只读查询仍为b39c06c，main为e11c389，未推送或合并main。
- [16项完成声明逐项核对](completion-audit.md)：10项文档交付、6项受控验证，引用产物均存在；结合源码、历史独立复核和当前工程回归核对其验收范围，不换算产品完成百分比。
- [原公司本地只读诊断](company-status.json)于02:44取自既有身份org-eb1c6fc7e1784a52823f3d389f9cac34：bootstrap、paused、0成员/工作/成果/模型调用；没有已绑定真实模型或工作区，没有Docker CLI。固定Harness依赖在本轮验证解释器可用；仍缺实际模型与工作区/主机条件。本次没有核查远端生产服务。
- GitHub combined-status返回statuses=[]；commit-workflow-runs仅查PR触发首批记录且返回[]，不表示全部Actions不存在或通过。本地新修复未上传，没有该变更的远端CI证据。

## 规划、实现、复核

[GPT-6 Astra规划](astra-plan.md)选择U-041的一个投影切片：本人unknown/needs_review优先；running必须有对应当前宿主活性；多待办选择依赖已满足项；显式blocked/failed/paused不再落为idle。AU级unknown/running、预算和暂停只约束原本可ready的候选，不把全部成员都显示为受阻。状态原因优先级冻结到028规格，不更改组织排程/岗位/授权。

GPT-6.1 Sol主代理实施ai_union/runtime_view.py及Engine/snapshot级测试。recent_run持久顺序、公开runs顺序保持；代表工作只属于当前成员，不保证正在执行。独立Astra初次复核发现handoff后新成员会话误引用旧成员run；补先红后绿回归后，在调用_session前验证run归属，保持_session内部和检查点判断原实现。见[完整局部复核](astra-review.md)。

两个Astra角色均通过代理接口显式指定gpt-6-astra，主执行环境为gpt-6.1-sol；不只是提示词角色命名。服务端解析型号、工程token/费用回执未提供，保持未知。这些工程代理请求不算AU runtime供应商调用或公司自主组织证据。

## 验证与证据

| 检查 | 实际结果 |
| --- | --- |
| 修复前有效回归 | Console 39项，8个新增方法失败、共12个失败断言/子测试；[日志](regression-before.log) |
| 初次测试草稿 | 一项资源设置错误被已有Console拒绝，且ready/waiting名称顺序未真实触发选择缺陷；修正测试后重新取上述有效红灯，未修改产品权限；[原草稿记录](initial-test-draft.log)不作为缺陷证据 |
| 初次修复全量 | 214项Python通过，66.185秒；[日志](python-tests.log)，此时独立审查尚有交接会话阻塞，不能据全绿视为验收完成 |
| 审查发现的handoff回归 | 新成员错误拿到旧成员会话摘要，先失败；[日志](handoff-before.log) |
| 最终Console | 40项通过；[日志](console-tests.log) |
| 最终Python完整回归 | 215项通过，61.694秒；[日志](python-tests-final.log) |
| 独立Astra | 初轮39项和15个额外确定性边界探测通过但发现会话阻塞；修复后40项和running/unknown两类交接额外探测通过；[原记录](independent-console-tests.log)、[最终PASS](independent-final-tests.log) |
| npm完整检查 | 退出0；管理8项、历史82任务/181依赖、动作安全9项、前端22项、类型检查和构建通过；[完整日志](npm-check.log) |
| 管理与差异收口 | 主账生成及一致性检查通过；git diff --check通过。主账仍为在制3/3、就绪0、阻塞7、done16、realAccepted0 |
| 实际浏览器 | Playwright缓存的Chromium可执行文件仍不存在；未重试已知失败的下载、未执行实际A01–A06/A11，不以组件/HTTP检查替代 |

新增10个测试方法使用新临时组织、正式Engine决定/工作/交接/核对接口和明确fixture；会话案例使用合成元数据，不声称真实检查点存在或安全恢复。覆盖成员结果与宿主失败、unknown决策、依赖选择、撤权needs_review、宿主活性、预算/暂停、显式恢复/取消和交接归属。重复读取及重开Engine检查state/events/runs/调用占用不变；unknown派发仍blocked，没有自动重放。

上一轮`.union/validation-20261031-0131`临时解释器已不在当前环境，未假设持续存在。本轮用uv新建忽略目录`.union/validation-20261031-0237`，按requirements-harness.lock安装60个固定包及editable项目，未清空已有.venv。运行命令：

```sh
.union/validation-20261031-0237/bin/python -m unittest tests.test_console -v
.union/validation-20261031-0237/bin/python -m unittest discover -v
npm run management:render
npm run check
git diff --check
```

## 阻塞与下一步

U-041保持blocked，无completion，不以局部独立复核替代完整观察边界验收。剩余兼任工作区、检查点/恢复与运行位置描述、实际浏览器矩阵及完整独立复核。主账、生成视图、028任务、STATUS和HANDOFF同步；实际在制3的原纠偏及恢复上限2的条件不变。

下一小时首项：复现_workspace只取首个有效任职的缺口，明确成员兼任时按代表工作/实际任职判断工作区可用性的最小契约；先由Astra界定、Sol按现有宿主/章程/岗位授权做只读修复及回归，不自动给成员增加工具权限。

模型凭据及明确调用预算、实际Docker镜像/主机、SSH/VPS连接和真实New API条件未补齐；U-002/U-005/U-007/U-008/U-037/U-039原阻塞保留。未发布、付费、合并main或修改生产环境。
