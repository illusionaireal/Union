# 部署与集成值守契约（U-079）

2026-11-08：用户授权 codex-home 负责 NAS 部署、每五分钟读取团队留言、维护 Kanban、检查 GitHub、审阅合并与冲突处理。本次交付一个可查询、可停止的值守入口；S08/U-074 的真实业务、恢复和持续运行仍按原卡验收。

## 执行与责任

Windows 计划任务每五分钟运行一次宿主上的 `ops_watch.py`。读取实时 Kanban 活动卡/留言、GitHub 开放 PR/检查及指定 NAS 服务健康；宿主私有目录保存成功时间、内容指纹和待处理信号。这些是巡检运行记录，不是第二份任务台账。不根据仓库历史状态自动修改在线卡，不自动认领或合并。

同一私有目录的进程共享操作系统文件锁，进程退出后锁自动释放。读取失败保留上次成功结果，不确认待处理信号。没有变化且没有未完成跟进时不启动模型。关闭 `agent_enabled` 可以保留确定性巡检、停止新 Agent 调度。

已启用且存在待处理信号时，调用既有 CLI、沿宿主模型配置执行一轮部署/集成工作；执行输出与诊断只存宿主。不以 `codex login status` 作为所有模型通道的统一门槛：已配置的自定义 provider 可以不要求 OpenAI 登录，实际执行失败才保留未处理信号。它须重新读实时看板，保留其他开发者改动，按用户授权和仓库规则审阅、验证后才提交/合并。模型失败或没有明确完成回执时保留待处理信号；结果未知不盲目重放部署或合并。下一轮先查询原操作结果。长工作不设统一短超时；另一个巡检进程仍可读取新的留言，单独的 Agent 文件锁阻止重复执行。

`handled` 表示本轮信号已检查并记录处置，不表示卡片完成；`follow_up` 保留下一轮接续。凭据失效时只记录阻塞，不弹出无人值守登录。用户本轮未授权真实模型业务支出、资金、生产数据迁移或运行中 AU 治理变更。

## 配置和操作

实际配置仅放宿主，字段：`state_dir`、`env_file`（Kanban 凭据与代理）、`repository`、`github_repository`、`ssh_target`、`ssh_port`、`health_command`（固定只读命令）、`codex`、`agent_enabled`、`prompt_file`。仓库不保存真实地址或私有目录。

```powershell
# 私有配置路径由本机运维设置。
python ops/automation/ops_watch.py --config $env:UNION_OPS_CONFIG
Get-ScheduledTask -TaskName Union-Deployment-Watch
Get-ScheduledTaskInfo -TaskName Union-Deployment-Watch
Disable-ScheduledTask -TaskName Union-Deployment-Watch
Enable-ScheduledTask -TaskName Union-Deployment-Watch
```

计划任务仅在本机开机且注册用户会话可运行时触发；它不保证断电或 Windows 注销后的运行。`status.json` 记录最新巡检结果，`agent.json` 记录登录/执行状态；日志在私有目录。修改配置停用 Agent 不会撤销已发生的远端操作或取消正在运行的工作。

验收：真实轮询、五分钟任务注册；无变化、读取失败、并发锁和失败后的信号保留行为测试。登录缺失与真实部署未完成分别报告，不将定时读取或开发代理当作产品 AU 自治证据。
## 单个来源故障的隔离补充（2026-11-08）

看板/留言、GitHub 和 NAS 是三个独立只读来源。一个来源超时或失败后，仍须尝试其余来源，并在宿主状态中分别记录本轮观察时间、成功数据或脱敏错误类型。部分读取不能替代完整 snapshot，不能推进 last_success、完整指纹或消费 pending。部分读取至少有一个当前成功来源时，自动 Agent 可处理已授权且有当前事实支撑的独立工作；在线看板变更仍要求重新读取成功及最新 version。部分信号使用独立指纹和处理回执，不消费完整信号；旧部分回执不能吞掉更新的事实，只有时间变化不重复触发。全部来源失败或泛化异常遗留的旧观察不启动 Agent。恢复完整读取后清除本轮部分读取诊断。此修复属于 U-079/#33 既有部署值守责任，不改变产品 AU 的授权。

未配置 HTTP_PROXY/HTTPS_PROXY 时使用直接连接，不向 urllib 传空代理地址。已配置的代理仍显式使用。完整快照的指纹不包含观察时间，因此同样内容不会反复产生新信号。
