# 长期阻塞复查的实际宿主采用

2026-11-08，前台协调者按用户授权采用PR31，区别于受监督值守执行者。
[契约/17项回归](overdue-review.md)与[真实采用读回](overdue-host-adoption.json)分别保存。
14项当前CI通过后合并e7b139f，宿主安装文件与被合并源SHA256/字节一致。
原宿主额外三次HTTP只读重试补丁完整保存在私有备份；本次安装精确已验证源。
凭据、真实地址和私有执行日志不入库。

14:21:55Z三源完整轮询成功：board revision299、GitHub、NAS可读取；NAS running /
OOM=false / restart=0。attention真实标出#28（blocked、period=2），原owner不变。
前台占用写入锁时run_agent返回busy；五分钟只读巡检继续，未产生第二写入者。
前台最终交接后释放锁，由原计划任务继续执行。

#33 v5已读回采用。#28 v12、评论81、交流44记录明确工程缺口：V1 CoreModels未挂载
旧ModelRunStream，modeld已有原请求/AU events。可先用本地受控服务完成流式投影、
主体/撤权清除和重连去重，不整体等待真实额度；原owner/blocked/WIP和真实profile
资源条件保留。进一步的五卡粒度核查见[评审](../../docs/reviews/2026-11-08-task-granularity.md)。

每五分钟轮询，每四小时无更新的在制任务重新提醒；失败board不把缓存年龄变成新
事实。介入应推进修复、诊断、拆分或明确资源决定，不重复不变留言。本记录是部署
协调采用，不是产品真实业务/持续运营验收。
