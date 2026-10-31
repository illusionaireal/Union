# Astra 规划：A03时间过期与迟到回执

2026-10-31 19:34起，基线dev@3e908fd；GPT-6 Astra只读核查后完整返回，未改文件或运行测试。Sol按计划执行。

最高优先级补A03实际机制证据，不先扩U-042。现有host_activity要求0<=age<=5且真实runner.lock held；_reserve保存package.host_owner，snapshot仅用于活性匹配。没有独立持久epoch/租约或回执owner-token fencing。finish_*靠run.status、工作run_id/version与任职保护，正常runner.run/watch先持锁进入activity，再recover旧running为unknown，step拒绝重派。

冻结四个最小用例：
1. 原owner/锁持续存在，真实首拍后仅冻结续拍调度及activity本模块时钟；age=0/5确认、5.001/负age不确认。心跳文件与owner不变、锁仍held；快照running→unconfirmed，runtime活性unknown、active_run_id为空，成员blocked/activity_unconfirmed；未暂停dispatch仍enabled，暂停为pause_requested。读取不恢复/写业务记录，实际第二runner锁拒绝、factory/execute零次。
2. 独立过期fixture保留原owner/锁，原run的合法成果仍可正式finish_work，用量和唯一成果保留；过期不等于取消或自动授权接管。
3. 旧owner退出留未结算running，新Engine真实runner.run持锁新owner后先观察旧run不冒领，再真实recover→unknown/blocked；旧finish_work/finish_progress拒绝，迟到fail_run无效，无成果/新预算。
4. 正式reconcile confirmed_not_executed，依据仅为fixture只预约且未调用外部执行器；新Runner的模拟executor执行时尝试旧回执，旧记录不能替新run交付，最终仅新成果、累计预算2、旧reconciled记录保留。

时钟只patch ai_union.activity.time模块绑定，不能改共享stdlib time.time。threading只patch该模块绑定为proxy：真实Thread，Event子类wait等待真实set，保留首拍JSON/replace/UID/真实文件锁并正常join。不是续拍可靠性测试，不用退出activity假装时间过期，不手填owner/run状态，不mock恢复/结算/派发。

默认只加tests/test_activity_receipts.py；有实际契约失败才最小生产修复。先定向、相关回归、全量Python与npm，再独立复核。平台不新增业务岗位、流程、权限、租约或托管控制。

可报告A03上述受控子集；真实续拍/进程崩溃、供应商迟到网络响应、跨进程/跨主机fencing、systemd/VPS、热配置、WAL/跨库、Chromium和U-041整体仍未验。工程模型解析型号/token/费用未返回，保持未知。
