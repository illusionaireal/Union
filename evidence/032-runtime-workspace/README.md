# 032：代表工作的工作区许可摘要

2026-10-31；开始核查03:33（UTC+8），后续因Astra额度中断，07:30继续并重新核查现场。基线dev@85647a7。外部工程协作与受控fixture，不是AU成员真实交付或VPS常驻链验证。

## 实际进度核查

- 当前dev开始时领先远端8提交，tracked工作区干净；用户docs/research/未跟踪资料保留。07:33再次只读ls-remote：dev仍b39c06c76e3b83a6d5413b45f58a9c736e2f15bc，main仍e11c389366814060ea4475a359c9b62036ccd176。未推送、发布或合并main。
- 主账43任务中的16项done逐项复核完成范围、验收说明和引用产物：10项documentation、6项controlled，没有real/sustained完成项或accepted真实里程碑。逐项内容/代码映射沿用已审阅的[031核查表](../031-member-work-state/completion-audit.md)，本轮重新采集[16项范围及证据完整性](completion-audit.json)，结合222项工程回归核对当前实现；文件存在/哈希不自动证明业务真实性。
- [原公司本地只读检查](company-status.json)07:33：原身份仍bootstrap/paused，0成员、工作、成果及模型调用；未绑定真实模型/工作区，无Docker CLI。工具往返与自主运营未验证。本地数据不是远端生产现场。
- GitHub combined-status返回statuses=[]；commit-workflow-runs返回[]，但此接口仅覆盖PR触发首批结果，不能据此认定全部Actions不存在或通过。本地修复未上传，无本提交远端CI证据。

## 规划与实际变更

[Astra核心取舍及中断记录](planning.md)：实际gpt-6-astra规划代理核对源码并要求工作区摘要跟随代表工作，不选首个任职；无代表工作不猜岗位；静态许可不能当作命令实时可执行。其后因usage limit终止，完整规划/测试矩阵未完成，没有升级或买额度。

GPT-6.1 Sol主代理依据已收到的核心方案细化028契约、实现和测试。runtime_view._workspace现在以代表工作的assignment_id定位有效任职，核对当前成员及岗位，再取当前章程/岗位许可；无代表工作返回no_current_work，无有效任职返回no_active_assignment，保留未配置/禁用优先原因和实际revision。不新增字段、前端或真实执行权限；组织仍自主决定岗位、任务和工具。

workspace.available是此投影的配置/任职许可交集，不是对真实容器、镜像、运行工作包、暂停或恢复安全的承诺。真实workspace.available(package)/authorized/execute保持原独立门槛。交接和暂停场景中，即使许可摘要为true，旧包或被暂停的执行仍被拒绝。[独立工程复核由另一GPT-6.1 Sol承担](review.md)，不冒称Astra复核。工程模型解析型号、token/费用未由回执提供，保持未知。

## 测试与证据

| 检查 | 结果 |
| --- | --- |
| 新增回归修复前 | 7方法、4个失败断言/子例：兼任双向误报、交接、无代表工作；[日志](regression-before.log) |
| 定向修复后 | 59项（新7+Console40+workspace12）通过，2.060秒；[日志](focused-tests.log) |
| Python全量 | 222项通过，62.858秒；[日志](python-tests.log) |
| 独立Sol | 29方法通过，4.529秒，含额外6项边界探测；[日志](independent-review-tests.log) |
| npm完整检查 | 退出0：主账/视图、管理8项、历史82任务/181依赖、动作安全9项、前端22项、类型及构建通过；[日志](npm-check.log) |
| 收口检查 | 主账生成与一致性通过；git差异检查通过，U-041未关闭 |
| 浏览器 | 07:33检查Playwright缓存可执行文件仍不存在；没有实际A01–A06/A11验收，不用组件测试替代 |

新测试均使用临时fixture组织、正式Engine组织/章程/交接接口和workspace.configure/disable配置，不执行Docker命令。重复snapshot及重开Engine核对state/events/runs、配置/回执和数据库表不变，读取不建表、不调用容器，私有目录/镜像不进入公开快照。完整回归含既有真实SDK与本地HTTP替身，不代表真实供应商成功。

上一段验证解释器在继续工作时已缺失，本轮07:31用uv新建忽略目录.union/validation-20261031-0731，按requirements-harness.lock安装固定60包及editable项目；未清空已有.venv。命令：

```sh
.union/validation-20261031-0731/bin/python -m unittest tests.test_runtime_workspace tests.test_console tests.test_workspace -v
.union/validation-20261031-0731/bin/python -m unittest discover -v
npm run management:render
npm run check
git diff --check
```

## 阻塞与下一小时

U-041仍blocked，无completion；本轮仅局部受控修复和工程独立复核。检查点存在性/恢复判断、部署描述、实际浏览器矩阵及完整观察边界复核未完成，U-042未实现。主账仍在制3/3、就绪0、阻塞7、done16，不按任务统计换算产品完成率。

下一小时先复现_session按agent_sessions.status推断has_checkpoint的缺口，由可用Astra明确只读元数据核查契约，再由Sol修复和测试；检查点存在不自动等于可恢复，不能重放unknown或把私有正文带入观察接口。若Astra额度仍受限，如实记录规划阻塞，不替换后冒称已完成指定模型规划。

实际模型/授权预算、Docker主机及镜像、SSH/VPS和真实New API条件未到位，原资源阻塞保持。未付费、采购、公开发布、合并main或改动生产环境；工程代理工作不计作公司自主组织、真实模型调用或运营。
