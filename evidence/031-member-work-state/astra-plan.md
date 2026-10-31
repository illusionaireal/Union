# GPT-6 Astra 局部规划

2026-10-31；独立上下文代理 `/root/astra_work_state_plan`，创建接口显式指定 `gpt-6-astra`，只读核查实际源码后给出本计划。主执行代理为 GPT-6.1 Sol。服务端解析型号、token与费用未在回执中提供，保持未知。

选择U-041成员工作状态与代表工作引用：原投影只取running/pending，遗漏blocked/failed/paused/needs_review；unknown分支又在pending之后；第一项pending还可能掩盖依赖满足的待办。runner对全AU的unknown/running已有停止新派发规则，投影应如实解释，而非改写调度。

实施顺序：本人unknown/needs_review→running（按实际宿主活性判断）→依赖满足pending（应用AU门槛）→blocked/failed→依赖未满足pending→paused→idle。同级保持既有状态顺序，代表工作不得冒指他人；unknown决策没有工作时保持null。全AU门槛只影响本可ready的候选，不将依赖等待或真正idle统一blocked。细节冻结到028规格。

新增Engine/snapshot行为回归，使用正式状态变更和明确fixture：受阻、成员结果失败、宿主失败、暂停、unknown、撤权后needs_review；多待办选择；本人/他人unknown与无work_id决策；确认/失去宿主活性；暂停/额度到限；显式恢复、核对、取消后的重算。先红后绿，重复读取/重开Engine不改状态、事件、runs或调用占用，unknown不自动重试。保留最近执行与隐私测试，运行完整Python和npm检查，再做独立局部复核。

不改Engine/runner/授权/恢复/会话/工作区；不扩前端功能或托管。U-041仍blocked：兼任工作区、检查点/恢复与部署描述、实际浏览器A01–A06/A11及完整观察边界复核待完成。模型/真实Docker/持久主机阻塞保持。本工程协作不是AU自主组织或真实公司运行证据。

规划代理未运行测试：其检查发现上一轮临时解释器不存在；主执行代理随后在新忽略目录重建固定依赖环境。规划建议不是测试已通过的声明。
