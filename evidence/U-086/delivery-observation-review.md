# U-086：aa82962 服务端增量复核

2026-11-09，原实施者 DSH，复核者为当前 codex-home 值守会话。准确输入
`aa82962107225903643d3949f51d4b77258b33ca` 经 fresh Git fetch 取得；
没有修改被评产品源码。#40 评论153为作者输入，评论154已 GET200 读回，
原 owner/progress/WIP 保持。本会话同时实施的 PR43 页面不在此独立批准范围。

原 PR42 六项送达探针 **6/6 PASS（6.830s）**：取消意图在发送前提交、外部
I/O 不占 AU 写事务、错误请求/AU 响应不被受理、提交失败不发生取消副作用、
POST/GET/重开送达事实一致。此前五项失败不适用于此新 head。

按[增量合同](delivery-observation-contract.md)新增两项
[可运行反例](delivery-observation-probes.py)，结果 **2 FAIL / 0 ERROR（2.808s）**：

| 边界 | 实际结果 | 必要修复 |
| --- | --- | --- |
| 重开后同 ID/同输入 POST 重放 | 第一次 POST/GET 为 `cancel_accepted=true`，重放却为 `null` 且缺少 delivery | `WorkService.command` 的 existing 提前返回路径须取得相同已持久送达视图；不能重新送达 |
| 送达观察完整性 | 改 observed 内容、保持 hash 原值后，原 GET 仍 HTTP200 接纳篡改正文与 false | 读取独立观察时验证已存 hash、绑定和结构，错误不得作为可信事实返回 |

`tests/test_core_work.py` 在新候选把原 POST 重放断言改为只查 GET，减少了
已有幂等覆盖。应恢复原断言并使三条路径保持一致。允许稳定受理回执加独立
送达观察，不要求回到发送前持锁方案，也不要求修改原审计回执。

首次新增探针还遇到测试自身 SQLite 连接未关闭导致 Windows 临时目录清理
失败；改用显式 closing 后，同样两处产品反例仍失败且无清理错误。两次日志
摘要均保留于[结构化记录](page-access-verification.json)，没有把夹具错误算
成第三个产品问题。源文件从准确候选导出，原 PR42 fixture 字节保持。

新服务端候选暂不采用，原两项由 DSH 接续修复。原模型预约仍保留，页面
自测和此服务端复核均不关闭 #40 或父 #22 真实出口。真实模型调用、部署
切换和业务迁移均为 0。
