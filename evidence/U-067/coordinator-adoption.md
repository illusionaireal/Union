# S03 阻塞修复采用与验收驱动交付

2026-11-08，前台接续 `01a1b7fe-81cb-7ec0-8459-d85fd97a9ba7`，用户明确要求介入长期阻塞。
actor 为本前台协调会话；在线成员 codex-home (`c18f0d21-1d63-4e37-af3e-2dbb78d75995`)。
DSH 保留在线 #22 的完整责任。这些开发代理不是产品 AU 成员。

| PR | 确认采用 |
| --- | --- |
| [24](https://github.com/illusionaireal/Union/pull/24) | 父循环停止保留实际调用与用量；`9bea36c382b7934037e7fd39e0ae9921e5ec18a4` |
| [25](https://github.com/illusionaireal/Union/pull/25) | schema 4 / 旧候选拒绝 / schema 3 历史预约兼容，经PR28采用，原SHA保留 |
| [30](https://github.com/illusionaireal/Union/pull/30) | 迟到准备拒绝不能抢占已派发原回执；合入PR28为`7ac4be01a62d47c0b1ea12ea2fe4ebd6c19b0165` |
| [28](https://github.com/illusionaireal/Union/pull/28) | 组合产品及已独立核验的HTTP夹具修复；`bd3445a3e6ec56f7bc5019cc33371d9e26331c4b` |
| [29](https://github.com/illusionaireal/Union/pull/29) | U-082独立夹具证据；`822847d3a57d132a868ba5a6ab662cf640c12311` |
| [32](https://github.com/illusionaireal/Union/pull/32) | 验收driver及099/100/107声明修正；`86f283a6955a22e8b721c18e8aac4683c1d72fd8` |

产品由先前值守会话实施，前台接续会话核对实际源码和契约。PR24/25/30 reviews
为5818137155/5818137398/5818137616；组合复核为
[5818201697](https://github.com/illusionaireal/Union/pull/28#pullrequestreview-5818201697)。
46项派发/回执/兼容/竞态、原三个反例探针、10项真实Chrome/HTTP/SQLite检查和npm
均通过。PR28最终443381a与被复核cba6260同树，14项当前CI成功后采用。
U-082的独立结论仅覆盖夹具。PR29首次Windows job128749099397的旧5秒等待失败
保留；引入已审查PR28祖先后，2996510全部当前检查成功才合并，断言未削弱。

在线#22评论76/78、交流42/43记录前台接管逾期driver范围，作者停止重复编辑、
保留父卡owner。PR32保留作者0821cff与重排a6a88f0历史；六个add/add文件先确认
作者新旧字节一致再采用修正。生产源码未因该PR改变。

[严格RED/GREEN及最终记录](acceptance-intervention/README.md)：8用例14断言失败，
再通过18项守卫，含真实本地HTTP/SQLite/资料读取/下载路径与明确模型替身。
首次727项全量因新测试清理次序错误失败（2 failures、12 errors）；原记录保留，
修正后25项隔离回归通过。固定1c5780f最终**751 Python通过、9跳过、零失败/错误**，
npm check通过；仅证据补记后的72c8284最终**14项CI全成功**。

驱动核对显式Go账户、不同原请求ID、各次上限/用量、正文/tool ID、下载内容散列/字节/
来源及不可预知资料token。中断要求同一AU/Work/attempt/command的实际输出、取消
回执与modeld interrupted；查询失败/无输出/完成竞态不得冒充通过。未知留预约，
实际completed才转used；重启重复原命令不再派发。取消受理或modeld interrupted
不证明远端取消。

本次新增真实模型调用**零**；历史真实记录不被工程替身重新认证。#22仍缺页面调用
自动循环及完整有界成果/中断出口，见[五卡粒度复核](../../docs/reviews/2026-11-08-task-granularity.md)。
原owner/未完验收保留；没有业务服务切换或数据迁移，原checkout/vendor脏改动保留。

组合含PR31/32的9f352e0在本机再次通过754项Python（9跳过）与npm；同提交Windows CI的一次5秒模型恢复夹具等待失败及单项诊断通过分别保存在[验证历史](coordinator-validation.json)。不改断言/生产源码，不把该失败重写为通过；最终交付仍以当前head全部CI成功为门禁。

该CI等待缺陷随后按[冻结夹具契约](model-check-fixture/README.md)稳定复现：真实本地HTTP原请求延迟5.5秒，原默认5秒失败；最小改为默认30秒且保留显式短等待。10项夹具/模型观察回归通过，原请求/两次调用、产品权限/计量及终态断言不变。
