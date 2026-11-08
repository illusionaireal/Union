# U-084：原回执等待期间的403不能单独证明撤权

2026-11-08。原PR34候选`3cabe0d4205fd8d59597cc7f1f1e792cab4d1f49`，
实际集成基线`cbdbb552106089629984dda0473753a37a264506`；本地组合提交
`4ca8cb232e2607aa05f004c366365dc161f40eaf`，保留PR33的夹具及用量元数据修复。
执行卡#38原owner为chatGPT-online；codex-home本会话先独立评审，再实施
这个缺陷的协助修复。实施actor为当前Codex会话，在线成员ID为
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`，不是产品AU成员。

## 原因与冻结边界

GovernanceStore只允许原签发主体取得已经提交的回执。尚无该记录与无权取得
该记录统一返回403/not_authorized；没有回执不能证明AU读取权消失。原页面
把这次403直接交给通用撤权处理，从而清空工作和原请求查询入口。

真实本地HTTP验证：不存在的原回执GET为403/not_authorized，同一身份的
work GET仍为200且can_start=true。真实Chrome复现更严格的在途场景：
只在回环模型替身中等待，页面发送一次run_loop，最终回执尚未提交时查询
得到403，原页面显示“权限或身份已变化”。没有撤掉正常实现制造失败。

先补[冻结合同](../../specs/053-union-rewrite/s03-page-execution-contract.md)，
再增加反例，才修改WorkExecution.lookup。收到回执403后独立校验session、
当前工作投影的协议/主体/AU，再重验session；读取权有效时保留原引用并允许
稍后查询。实际读取拒绝或身份错配仍清除旧内容。未知不会成为成功、不释放
预约、不生成替代ID、不重放POST；已确认回执不会被稍后的查询失败降级。
服务端授权、事务、计量、模型派发及持久状态均未修改。

## 验证与失败历史

- DOM RED：新增“尚无回执403但工作仍有权读取”的行为测试失败；14项通过。
  原代码错误清空工作。最小修复后15项通过，包括读取拒绝、主体/AU/协议
  错配和在重新读取期间更换登录主体。
- 浏览器最初的长等待探针先遇到夹具的10秒transport timeout，不能单独用它
  证明产品故障；原日志保留。改为立即断言页面反馈后，在尚未重新构建的原
  PR34组合产物上再次RED，实际值为错误撤权页面，期望为保留原回执查询。
- 修复后真实Chrome、HTTP、SQLite与明确回环模型替身：等待期间403恢复、
  一次原work POST、完成后丢响应、刷新、原ID GET、持久成果下载及三宽度，
  7项通过。原默认浏览器场景另外6项通过。两次都是受控模型替身。
- npm check、Python全量与各日志SHA见[验证汇总](pending-receipt-verification.json)。
  CI新增等待场景并上传结果，不删减原检查。宿主私有日志不进入仓库。

运行入口：`npm run check`；`python -m unittest discover -v`；
`npm run test --workspace @union/console -- src/features/work/page-execution.test.tsx`；
`UNION_U084_PENDING_RECEIPT=1 node scripts/u084-work-execution-browser.cjs`。
Python与Chrome路径按宿主私有环境配置，Windows使用PowerShell设置环境变量。

## 采用边界

本修复是待审候选。原PR34的14项CI成功不等于这次修改已经通过CI；新增候选
须其当前head CI和另一工程角色的身份/权限复核。codex-home不能把自己的
这次修复称作已独立复核。#38/#22的owner、状态及未完验收保留。

真实模型调用0，没有切换NAS业务服务、迁移数据或更改监督配置。
#39/#40及父#22真实结果/中断出口、本卡后续业务轮次均未由本证据升级。
