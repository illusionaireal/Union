# 035：派发观察单次计算与诊断修正

2026-10-31；09:38开始核查，12:36继续并重新核查现场，基线dev@d428e87。GPT-6 Astra已确认规划决策→GPT-6.1 Sol实现→独立GPT-6 Astra局部复核；均为外部工程角色，不是AU成员或VPS常驻开发链。工程模型解析型号/token/费用未返回，保持未知。

## 实际核查

开始时dev领先远端11提交，tracked干净；用户docs/research/未跟踪资料保留。12:39再次只读ls-remote：dev仍b39c06c76e3b83a6d5413b45f58a9c736e2f15bc，main仍e11c389366814060ea4475a359c9b62036ccd176。combined-status返回statuses=[]，workflow_runs=[]但接口只查PR触发首批结果，不证明全部Actions不存在或通过。本地变更未上传，无该SHA远端CI。

16项done仍为10项documentation、6项controlled，没有real/sustained完成或accepted结果阶段。逐项内容/代码映射重读[031审计](../031-member-work-state/completion-audit.md)，本轮重新核对[完成范围与产物完整性](completion-audit.json)并执行当前回归；文件/哈希不证明业务真实性，不按16/43算产品完成率。

[12:40原公司本地只读诊断](company-status.json)仍为原身份、bootstrap/paused，0成员/工作/成果/模型调用，未绑定真实模型或工作区，无Docker CLI；未核查远端生产。模型/调用预算授权、Docker镜像/主机、SSH/VPS和真实New API资源阻塞保持。

## 规划与修改

[Astra实到决策](plan.md)冻结unknown优先、暂停与持久running/宿主活性的共同口径；Sol在snapshot计算一次并传runtime_view，去掉第二份公式。owner失配/活性丢失不抹掉持久running；enabled不是预算、依赖、权限或可执行保证。runner/Engine/next_step/成员状态、真实暂停和恢复行为不改。

Astra还批准纯诊断消费者修正：corp.inspect_company从真实engine.paused()生成paused blocker，不再将非enabled等同用户暂停；未知执行仍有unresolved_execution，启动未被放开。该诊断多源读取，不承诺原子一致。前端仅调整pause_requested标签，两资源卡片继续读各自字段而获得同一值。

[独立Astra复核](review.md)PASS。没有新增字段/枚举、组织岗位流程、控制动作、权限或预算，也没有注册runtime。完整观察边界与真实运营仍另验。

## 测试与证据

| 检查 | 结果 |
| --- | --- |
| 修复前回归 | 新5方法中3失败，2控制场景通过；[日志](regression-before.log) |
| 修复后定向 | 59项通过，2.103秒；[日志](focused-tests.log) |
| Python全量 | 239项通过，64.219秒；[日志](python-tests.log) |
| 前端 | 类型、31项测试及构建通过；[日志](frontend-tests.log) |
| 独立Astra | Python34项、前端31项、类型及差异检查通过；[日志](independent-review-tests.log) |
| npm完整检查 | 退出0：主账/视图、管理8项、历史82任务/181依赖、动作安全9项、前端31项、类型及构建通过；[日志](npm-check.log) |
| 收口 | 主账生成/一致性与git差异检查通过，U-041保持blocked，真实/持续验收不提升 |
| 实际浏览器 | 12:39再次检查Playwright文件和常用Chromium命令均不可用；未重复安装或用组件检查冒充A01–A06/A11 |

新增4个派发观察方法和1个临时公司诊断方法，通过正式Engine和exclusive/activity覆盖unknown无论暂停与否均待核对、host-only暂停不宣称结束、持久running在owner丢失后仍待确认、enabled与额度/可执行性分开、corp暂停意图不误报。重复snapshot/重开Engine核对组织/事件/runs/暂停标志/表结构/额度不变；patch禁止读取调用recover；runner.step仍拒绝unknown或暂停且未调用执行器。前端新增2个两卡片一致文案用例。

旧解释器已缺失，09:40用uv在忽略目录新建.union/validation-20261031-0940并按requirements-harness.lock安装固定60包，12:36实际仍可执行；未覆盖.venv或用户数据。该解释器执行unittest定向及discover -v，另执行npm run management:render、npm run check和git差异检查。fixture与SDK/回环替身验证均不算真实供应商或公司运行。

## 阻塞与下一小时

U-041仍blocked、无completion，在制3/3、就绪0、阻塞7、done16不提升；WAL预检TOCTOU、跨库非原子、完整恢复/观察边界、实际浏览器与托管未验。未推送、发布、付费、合并main或修改生产。

下一小时先对完整U-041观察面做独立服务端/实际HTTP权限、AU隔离及只读矩阵，按028 A01–A06的服务端部分收集证据并把失败收敛为最小修复；这不替代实际浏览器A01–A06/A11或整体验收。明确WAL剩余边界，不为填进度先扩托管能力。
