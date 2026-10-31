# 独立 Astra 复核

2026-10-31，实际GPT-6 Astra只读审查并独立复跑；不参与测试实现。结论：**PASS，仅服务端观察与实际HTTP交集的受控子集。没有发现需要修改生产代码的缺陷；A01–A06全项和U-041整体均未验收。**

独立运行115项，31.831秒，全部通过，见[independent-review-tests.log](independent-review-tests.log)。组成：runtime_http6、http5、console40、runtime_location4、runtime_workspace7、runtime_checkpoints8、dispatch_observation4、harness25、workspace_harness4、workspace12。

确认实际loopback Server与cookie；宿主全局会话和限域会话区别正确，后者不可越AU。两AU同名成员/session、仅一方真实SDK根检查点不串读；完整响应含非空receipts，私有key/路径/镜像/失败/feedback/checkpoint正文与metadata哨兵不泄露。伪造参数不扩权，无/伪造/过期cookie401、越域403、observer写入403、未实现控制路由404。稳定fixture读前读后业务表及非SHM检查点字节/文件集合一致，执行/恢复/SDK正文读取失败哨兵均未触发。

仍未通过：
- A03：已覆盖owner退出后的未确认、既有新owner不认领旧run；缺直接heartbeat时间过期及旧实例迟到回执的完整证据。
- A06：已有实际SDK章程变更后旧消息排除；缺连接revision、工作区revision和任职变更分别产生新会话、保留历史的专项真实SDK证据。task_key源码包含字段不是运行证据。
- 检查点存在不代表当前权限或安全恢复；Chromium、WAL TOCTOU、跨库原子观察、真实恢复、VPS/供应商和公司运营继续未验。

初次fixture缺token_limit_field导致合法输入校验拒绝，是fixture修正，不是生产红绿缺陷。复核者仅写独立日志；实施者随后强化根路径哨兵和会话字典不变断言，并另跑最终6项及245项全量通过。
