# U086：一次验收只准备一个 AU 和一个 grant

2026-11-09，实施前冻结。基线 `9195e25142014cb33ceb1c2ed4304839e8cf5725`；
在线 #40 保留 DSH owner/progress/WIP。实施 actor 为当前单一 codex-home 值守会话，
在线 user `c18f0d21-1d63-4e37-af3e-2dbb78d75995`，不是产品 AU 成员。

范围：`exit22b_page.cjs`（中断）与 `exit22c_download.cjs`（下载）的初始化。
预计 1–2 小时有效工程/验证，一个可独立验收的副作用边界，不再拆卡。
依据 Charter D-01、D-05、R-02、R-05 及 S01 原创建身份契约。

1. 一次新的 driver 运行仅发送一次 `create_v1`，保留该回执的原 AU ID。
   页面重新导航不代表新的创建意图，不能创建一个未追踪的第二 AU。
2. 只为该原 AU 发送一次 host `prepare`；`prepare` 会创建 modeld grant，
   不能把它当作可重复的只读刷新。后续采用连接继续用首次返回的 grant。
3. 初次创建/prepare 拒绝或结果未知时停止；不能换 AU/grant 隐式补救。
   本次不新增重试、不改 PageHost 或产品事务、不撤销/删除历史重复资源。
4. 原工作、执行、取消、下载、最终 GET 和重开断言保持；移除重复准备
   不改变实际调用预算，不声称完整页面/真实/持续出口通过。

验证先执行未改源码的真实片段：两个 driver 均应复现两次创建/两次 grant；
使用真实 Chrome→Core HTTP→SQLite 验证 AU 数与回执身份；grant 计数使用显式
替身（不接真实 modeld）。保留正常与首次失败对照，最小删除后全量回归。
准确 head CI 与另一工程角色复核后才进入集成；实施者不自行声称独立批准。
