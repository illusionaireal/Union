# U-117 / #71：原预约就绪后继续浏览器验收

当前 U108 驱动在 PR87 CI 和本机 Chrome 均出现同一按钮超时。原请求组已显示，
但当次页面 GET 尚无步骤；稍后 Core 中原预约已经存在。驱动只刷新一次后等待
按钮，不再获取工作快照，因此就绪取决于线程调度。

按[冻结合同](contract.md)，[驱动](../../scripts/u108-work-events-browser.cjs)
从那次真实 run_loop POST 取得原命令身份，最多 10 秒只读查询同一 AU/Work。
只接受该原命令派生首步骤处于 reserved 且预算仍占用的快照，然后刷新页面。
协议/AU 不符或 HTTP 失败立即报错；等待超时不重发命令。原产品代码没有改动。

冻结后，未改驱动再次出现真实 **RED**：10 秒内找不到“查看工作输出”。
最小修复后，实际 Chrome **21/21** 通过，包括正文、隐私、撤权清除、一次取消、
unknown 预约保留及重开不派发；新增断言绑定原步骤四个身份字段。
[7 项就绪回归](../../tests/u108-reservation-readiness.test.ts)覆盖延迟、错 Work/
命令/状态/预算、立即就绪、有界超时、错协议/AU 与 HTTP 失败；原 2 项 fixture
退出回归保留。仅回环夹具，一个 fake 模型请求、一个 cancel POST，真实模型为 0。

```text
node --test tests/u108-reservation-readiness.test.ts scripts/u108-work-events-browser.test.cjs
node scripts/u108-work-events-browser.cjs
npm run check
python -m unittest discover -v
```

完整检查及源码/原失败日志摘要见[validation.json](validation.json)。原日志和
诊断正文留宿主私有目录，只提交哈希与限定事实。Windows Chrome 使用已安装
浏览器并显式设置 `UNION_CHROMIUM_PATH`；固定 Python 使用项目既有虚拟环境。

本结果只说明当前驱动修复，不能倒推 U086 历史 117B 的原因，不能补造缺失 before，
也不能关闭其真实中断或父卡验收。U116 是独立构建修复，其后续采用见[读回记录](../U-116/adoption.json)；
本浏览器候选的采用仍取决于自己的准确 head CI。
实施 actor 为 `01a1c746-eb38-7711-ad90-290392a05d89`，在线成员为
`89f4c1c1-329a-4b54-ad37-235cf061e9a8`；自检不称独立评审，非产品 AU 成员。
