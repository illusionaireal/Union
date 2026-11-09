# 单次初始化：保留一个原 AU 和一个原 grant

基线作者 `9195e25142014cb33ceb1c2ed4304839e8cf5725`，#40 评论265冻结范围；
实施 actor 为单一 codex-home 值守，DSH 仍负责原卡。合同见 [contract.md](contract.md)。

两个验收 driver 原本各调用两次 `create_v1`，第二个 AU 回执被丢弃；各调用两次
`prepare` 又创建第二个 grant，连接仍采用第一次的 grant。现在删除这四个重复调用块，
保留首次身份、连接及所有工作/取消/成果/重开代码。未删除任何已有 AU 或 grant。

- 未改基线执行完整准备片段：8 项 Node 中4通过、4失败，分别证实每个driver
  留下两个AU及两个grant。首次创建unknown和prepare失败的既有停止行为保持。
- 最小删除后8项全部通过；首次返回的grant与采用连接精确相等。
- [browser.cjs](browser.cjs) 在两个真实Chrome→Core HTTP→SQLite实例执行原创建片段，
  基线两项均因2≠1失败；候选两项通过，刷新仍仅有原AU、原创建命令ID。
  [host.py](host.py) 明确移除真实modeld配置；浏览器四次一次性实例共0模型调用、
  0真实grant。Node的grant为显式内存替身，不是modeld授权或实际业务验收。

全量检查、源码和原始日志摘要见 [validation.json](validation.json)。私有日志留宿主，
失败历史不改写。未改产品ai_union/web/services、PageHost、调用预算和真实旧证据。
准确head CI与另一工程角色复核仍为采用条件；本实施者不自行批准。

仍需接续：实际Core目标登记、完整原页面链路/历史139、远端派发计数及明确的真实
资源授权；#22/#39/#40的真实出口保持未完成。没有新增真实推理、NAS切换或迁移。

最终本地：npm166 Node/363前端/37管理、类型及构建通过；Python全量808项/11跳过/0失败（524.979秒）。首个全量进程未设置UNION_BUN，随后显式使用锁定Bun单独补验该1项Core/modeld/SDK回环成功，仍为替身；原全量跳过数不改写。其余平台/未构建发布/真实资源跳过保留原日志，未算通过。
