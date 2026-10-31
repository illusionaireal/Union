# 034：未登记部署不冒报embedded

2026-10-31 08:36起（UTC+8）；基线dev@70e2c29。GPT-6 Astra规划、GPT-6.1 Sol实施、另一独立Astra局部复核。工程代理分工不是AU成员自主交付或VPS运行；模型解析型号、token/费用未由工具回执提供，保持未知。

## 实际进度

开始时dev领先远端10提交，tracked干净；用户docs/research/未跟踪资料保持原状。只读ls-remote仍为dev b39c06c76e3b83a6d5413b45f58a9c736e2f15bc、main e11c389366814060ea4475a359c9b62036ccd176。GitHub combined-status的statuses=[]，workflow_runs=[]但后者只查PR触发首批结果；不能推论全部Actions不存在或通过。本地变更未上传，无该提交远端CI证据。

16项done仍为10项documentation、6项controlled，无real/sustained完成或accepted结果阶段。内容/代码映射重读[031逐项核查](../031-member-work-state/completion-audit.md)，本轮重新核对[完成范围和产物完整性](completion-audit.json)并运行工程回归；文件和哈希不证明历史真实业务。真实目标公司、本地SDK/替身和工程代码分别验收，不换算总完成百分比。

[08:39本地原公司只读诊断](company-status.json)：原身份仍bootstrap/paused，0成员/工作/成果/模型调用，未配置真实模型或工作区，无Docker CLI；不是远端生产检查。模型/Docker/持久主机和真实New API资源阻塞未解除。

## 规划和改动

[Astra规划](plan.md)确认当前无runtime登记读写机制，现有锁/临时心跳只有宿主活性证据，不能区分Console、CLI、service部署。Sol仅把mode改为已有枚举unregistered、name改为部署位置未登记、capabilities改为空实例声明；runtime_id/instance_id/observed_at仍null。没有注册、迁移、回填、服务控制或新增权限。

宿主liveness与匹配owner的active_run保留，未登记不抹去真实执行事实；新owner不能认领旧run，活性丢失不recover或重派。Resources局部映射明确区分部署模式、宿主活性和已确认活跃执行，不再将活性unknown译成执行待核对；embedded/managed_local/external的显示兼容有明确fixture检查，不代表当前后端已实现登记。

[独立Astra局部复核](review.md)PASS。不修改组织业务岗位/流程、Engine/runner/权限，不扩大观察字段。当前顶层和runtime派发算法仍保持原样，二者在unknown且未暂停、暂停且仅有宿主活性时的差异留下一切片。

## 验证

| 检查 | 结果 |
| --- | --- |
| 修复前新增回归 | 4项均失败，直接复现固定embedded/名称/能力声明；[日志](regression-before.log) |
| 修复后定向 | 44项通过，1.368秒；[日志](focused-tests.log) |
| Python全量 | 234项通过，64.262秒；[日志](python-tests.log) |
| 前端 | 类型、29项测试及构建通过；[日志](frontend-tests.log) |
| 独立Astra | 59项Python、前端9项及类型检查通过；[日志](independent-review-tests.log) |
| npm完整检查 | 退出0：主账/视图、管理8项、历史82任务/181依赖、动作安全9项、前端29项、类型及构建通过；[日志](npm-check.log) |
| 收口 | 主账生成/一致性及git差异检查通过；未关闭U-041或提升真实验收 |
| 实际浏览器 | Playwright缓存文件缺失，常用chromium/chromium-browser/google-chrome命令均未找到；未重复已知失败下载，未执行A01–A06/A11 |

新增4个方法使用临时fixture组织、正式Engine及exclusive/activity：无登记/旧库、宿主活跃无run、匹配run执行与pause_requested、退出活性后running保留、owner不匹配、unknown/paused。重复snapshot和重开Engine不新增表或改变组织/事件/runs/预算，路径/PID不进入runtime登记字段。稳定fixture范围的只读验证不能外推为检查点任意并发绝对零写入保证。

旧验证解释器本轮已缺失，未沿用历史通过结论；uv在忽略目录新建.union/validation-20261031-0837，按requirements-harness.lock安装固定60包及editable项目，未清空原.venv。实际命令为该解释器执行unittest定向和discover -v，以及npm run management:render、npm run check、git差异检查。

## 阻塞与下一小时

U-041保持blocked、无completion，在制3/3、就绪0、阻塞7、done16；不关闭U-042或真实主机任务。WAL TOCTOU、跨库非原子、完整恢复/观察边界、实际Chromium与托管仍未验。未推送、发布、付费、合并main或改动生产环境。

下一小时先由Astra冻结顶层snapshot.dispatch_state与runtime.dispatch_state的统一观察口径，复现unknown未暂停、暂停且仅宿主活跃的差异，再由Sol最小只读修复与回归；不顺带改实际派发/暂停授权或抹掉未知执行。其余资源不足如实保留。
