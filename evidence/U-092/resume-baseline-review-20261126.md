# U-092/U-093 接续前独立基线复核

2026-11-26；基线e29fb49，review_recovery_baseline只读复核。用户明确授权保留原历史后，将在线#46从codex-home交接至zbook-codex，并完成#47/#66这些#76必需前置。交接已在#46 version6/progress读回；原负责人、分支与失败记录保留。这份报告不证明恢复或新输入已完成。

实际相关40项测试通过：review_inputs5、work_context13、work_dispatch22。现有机制正确保留网络前预约、原请求ID、工具上下文和unknown用量；reconcile_automatic只GET原请求并结算为not_adoptable，不能恢复正文。重开上下文用例仍手工finish/start新attempt，原host_instance继续拒绝旧实例，不是同一attempt恢复证据。

需冻结并修复的边界：WorkService准入/预约/采用仍借用浏览器token；active_steps/active_loops仅进程内，Console关闭没有Work停止边界；缺少持久owner/epoch与旧worker fencing。dispatch.prepare存命令摘要而非完整实际模型请求快照，没有prepared→dispatching可证明边界。必须持久保存原请求快照/摘要，在同AU事务取得恢复所有权，并逐次验证有效治理、责任、模型、资料授权；未知结果只查原请求，不POST重放，旧worker不得执行工具或覆盖新状态，但真实调用/用量保留。

U-093尚缺稳定输入ID/正文摘要/actor/AU/Work、去重及消费cursor。输入选择、cursor、完整下一模型请求快照及预约需在同AU事务可靠关联；收存/正式采用/交给模型消费区分，原上下文连续，不另造队列或loop。条件唤醒及profile原生能力仍由原任务负责。

原20文件恢复候选未在当前可达基线找到，旧评审包装正确以输入缺失退出2、零行为测试；不把缺文件当产品RED或用替身抹去历史。ARCHITECTURE§9.2/9.3的generation/请求快照是拟接口，不是已实现事实。

编码前须观察：原attempt工具快照重启连续；prepared未派发可恢复而dispatching/未知不重放；两恢复者只一有效epoch；关闭前未提交和关闭后未派发拒绝新POST；旧worker迟到/被替代请求重放不得夺回所有权；正常注销/到期与真正撤权区别；等待中输入到达、采用失败和采用后崩溃均不丢/不重复；unknown A不默认阻塞独立B。GovernanceStore仍为唯一AU写者，WorkService驱动原loop/step，按#46→#47→#76共享事务顺序集成。
