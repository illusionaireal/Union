# U-086：本地取消不能释放未知模型调用

2026-11-09。接续 #40 评论132/134/135。原候选实施者 DSH；独立评审 actor
为当前单一 codex-home 值守会话，在线 user.id
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`。未接管产品实现或原 owner。
fresh revision487/#40 v5 后，复评范围和反例已在评论136 GET200读回
（revision488；owner/status保持）。约1小时，一个候选准入结果，无需拆卡。

## 结论与准确来源

工作期间作者发布 `310c7e1cc4588f9d876453a1f1e978785ed3dc71`（评论137）。
该候选已拦住错误释放，四项安全探针全部通过；但实际自动调用的取消功能
仍缺失，新增在途请求探针明确失败：HTTP200/rejected，原modeld取消POST为0。
不能把“取消命令只释放手工预约”当作#40的自动工作中断能力。

撤回候选 `0f4abf5bad3e4fdb428cee6b2f350c201ce26b24` 的 `cancel_step`
会把远端结果未知的调用释放，并实际重新开放 `max_calls=1` 的调用预算。
这是独立 HTTP/SQLite 反例，从此前静态发现推进为行为证据；不是生产重复
派发，也不是当前集成回归。该候选已经由作者撤回，不建议恢复旧分支。

作者重建分支 `dsh/u086-page-cancel` 的首个重建 head
`07b6f089e0a6267e2e4806a69b4af22ad491552c`，父为 `8ea2b4d`，该提交只新增
重建说明。当前集成 `2ff90f1fe631e46fc71f9ba5487417415e0e4f63` 与该新基线
的 ai_union/web/services/scripts/tests 字节相同，都尚未提供取消命令。
GitHub HTTP200和本地准确Git对象分别核对；新对象通过现有REST工具逐对象
哈希验证取得。测试在导出的源码副本进行，未改作者源码或原开发目录。

## 有意义的反例与对照

先冻结[复核合同](cancel-boundary-contract.md)，随后编写
[四项可运行探针](cancel-boundary-probes.py)。每例通过实际 Core HTTP、
SQLite、ModeldWorkTransport 和明确 fake modeld 建立一项工作；每项工作
最多一次调用。没有加载真实模型配置。

| 检查 | 撤回0f4abf5 | 当前2ff90f1 | 作者重建07b6f08 |
| --- | --- | --- | --- |
| 本地取消后unknown仍占一个预约 | FAIL：released | PASS：拒绝不支持的命令 | 同左 |
| 不同run_step命令不得绕过max_calls=1 | FAIL：实际fake POST为2 | PASS：仍为1 | 同左 |
| 重启仍保留原unknown与预约 | FAIL：released持久保存 | PASS | PASS |
| 已完成的used/11输入/4输出/成果不被抹去 | PASS | PASS | PASS |

准确运行：旧候选4项/3失败/0错误，4.686s；当前4项通过，4.854s；作者新
基线4项通过，4.782s。旧候选取消unknown返回HTTP200/succeeded；当前和作者
新基线均为HTTP400“不支持的核心工作命令”。**后两组只是拒绝操作的安全
对照，不是取消功能GREEN或完整#40验收。**

首轮探针在当前集成误读错误体的`message`，实际字段为`error`，导致4项辅助
断言失败。修正探针后完成上表复验；此为测试编写错误，不冒充产品RED。
首轮旧候选已真实复现同样3个失败，所有日志摘要与哈希保留在
[验证记录](cancel-review.json)，不上传私有日志。

复现命令（Windows设置PYTHONUTF8=1、PYTHONIOENCODING=utf-8，使用项目固定依赖）：

```text
python evidence/U-086/cancel-boundary-probes.py <exact-source-directory>
```

## 最新310c7e1的功能反例

GitHub与fresh fetch确认该head包含当前2ff90f1，其直接父为组合提交f445446。
新的规则要求 `status=reserved` 且 `command_id` 为空；正确拒绝释放原自动
预约。四项安全探针4/4通过（5.004s），每项取消均HTTP200/rejected。

随后按同一#40验收补[在途取消功能探针](cancel-route-probe.py)：真实Core
HTTP自动派发，产品ModeldWorkTransport已POST且原SQLite自动预约为reserved；
fake modeld的原GET回调触发第二个真实HTTP取消。核对原command/attempt/step/
model_request后，要求取消送达同一 `(model_request_id, au_id)`，预约不释放。
没有借助手工reserve_step构造页面实际不会创建的未派发预约。

310c7e1为1 FAIL/0 errors（1.214s），原因是自动调用一律被新命令拒绝，
modeld取消POST为0。当前2ff90f1同样功能RED（1.251s，HTTP400/取消POST0），
属于已有能力缺口，不是当前代码回归。两者安全保留预约也不能替代真正取消。
此探针独立运行、预期在这些准确源码上失败，不冒充完整测试套件通过。

```text
python evidence/U-086/cancel-route-probe.py <exact-source-directory>
```

不建议把该手工预约命令接成Core自动工作取消按钮：Core的实际自动步进都带
command_id，reserved时仍会被拒绝。请原作者复用线端原请求取消协议和既有
loop，保存取消意图，分开取消受理与执行事实，先通过此真实入口功能RED再
做必要UI。保留原未知预约保护；如果冻结不同的公开命令输入，应调整探针
入口而保留行为断言。旧文件内“复用dispatch.find/settle/event”的文字也应
与实际通用work分支调用rules.cancel_step的实现分别陈述。

## 交接与未完成范围

本次只新增独立探针、合同和结果索引，产品字节不变。原作者继续基于当前
集成实施真正取消入口；“只结算reserved”也不能释放transport中的自动预约。
应复用原Work/attempt/command/model_request与GovernanceStore，分别处理取消
意图、远端取消受理、实际结果及当前授权；unknown、404和本地停止均不能
证明未执行。完整并发、丢响应、重开和Core页面验收仍待新产品候选。

受影响新探针已完成；npm check（315前端、37管理、9动作测试）通过，Python
全量782项/9跳过/0失败（492.101s），Node24.19.0、Python3.12.10。这些全量
检查验证当前集成代码，独立功能探针的预期RED仍单列；准确PR head CI及后续
候选评审单独跟进。没有新增真实推理、业务切换、数据迁移或调度变更，
未关闭#40或父#22。#28真实profile授权、#37获准共享源码、#61限定迁移授权
仍是各自阻塞，不用这些阻塞替代本次离线评审推进。
