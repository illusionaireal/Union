# U-086 / #40：新候选与当前集成边界复核

2026-11-09 最新页面协助：动作资格不足不再清除原请求恢复入口，已确认回执
保留迟到普通传输错误前的事实；38 DOM 与两种实际Chrome模式15/16项通过。
见[本轮实施和验证](page-access.md)。作者新服务端aa82962的原六项送达探针
全部通过，新增原POST重放/观察hash校验两项仍失败，见[增量复核](delivery-observation-review.md)。
页面仍须另一角色复核，服务端由原owner续修；下文五项失败属于旧候选时点。

2026-11-09 后续组合：页面67d1225与作者813b3b5已在协助分支合为45af934，
两种实际浏览器模式分别12项通过，并加入原CI。取消回执一致性已验证，另五项
服务端故障仍复现；见[准确组合与未完成边界](page-combination.md)。当前未采用，
页面仍需另一角色独立复核；以下均为各自候选时点的历史。

2026-11-09 页面协助候选：基于作者22649f4，修复原run_loop在途/丢响应时
不能取消及成功取消后刷新丢失原GET入口；见[实施与验证](page-recovery.md)。
这项修复由codex-home实施，须另一工程角色独立采用；服务端送达六项缺口及
真实父卡验收仍未完成。下方旧候选结论按各自SHA保留。

2026-11-09 最新：a3bb2cc 的预算保护通过，但自动取消入口、丢响应恢复和
迟到身份接纳仍失败，见[页面取消独立反例](cancel-page-review.md)。

2026-11-09 后续：作者已撤回旧产品候选。新增 `cancel_step` 的实际预算绕过、
重启保留错误与新基线对照见[取消边界复核](cancel-review.md)；原下文的
fe556aa/879d3f9结果与接续说明保留为前次评审历史。

2026-11-09。评审 actor：当前单一 codex-home 值守会话；候选实施者 DSH。
在线读取 revision476、#40 v2/progress/DSH；没有认领、改 owner 或关闭真实出口。
本次是约1小时的独立评审协助，一个候选准入结果，无需拆分产品实现卡。

## 准确来源与结论

Git fetch 与 GitHub REST 均确认集成 `8ea2b4dc239d1c86f90177278378d8bf4299272b`。
#60/U106 已经由 PR39 采用，本轮不重复实施。评论128/129提出的新候选为
`fe556aa420057a39243551f6d1faa14071fa4b76`，父提交
`7a7c85a9564b7ae6c28f881227cd18545f25728b`。GitHub 对其分支返回404、
短 SHA 返回422；随后从原开发仓库只读取得准确提交对象，导出到私有测试副本。
未操作原开发目录的索引、分支或文件，未把私有源码快照/日志重新发布。

过程中消息82解释误推到本地remote，并修正发布。随后GitHub HTTP200确认
22-B为b9c24ff，22-C已推进至`879d3f954313be7276ce246ab8d71bcb5dec1724`。
Git提交对象确认879d3f9的父为fe556aa，fe556aa的父仍为7a7c85a；消息所称
“父8ea2b4d”不成立。879d3f9只增加旧AutoRunActions的ID展示；已重新导出
准确最新head运行下面全部六项，仍全部失败。原fe556aa结果不冒充新head测试。

**该候选不能采用。当前集成版已保留原请求并保护未知预约；旧基线候选的
可选 model_request_id 补丁不能替代已采用的事务/恢复合同。** 这不是当前集成
回归，也不是一次生产重复派发或真实计费的证据。

## 新增独立反例

[三个可运行探针](candidate-boundary-probes.py)通过实际本地 HTTP/SQLite、
产品 ModeldWorkTransport 和 fake modeld 执行；候选源码未修改。

| 边界 | fe556aa | 当前8ea2b4d |
| --- | --- | --- |
| 未知步进与回执使用实际 modeld 请求 ID | FAIL：保存 `work-overview#s1`，实际 POST 使用 `work-overview-s1` | PASS |
| modeld interrupted 尚未证明没有执行，手工 released 不能释放占用 | FAIL：step 被改为 released | PASS：保留 unknown/reserved=1 |
| 重启后原样重放原命令只返回旧回执 | FAIL：HTTP409 版本冲突，未恢复旧回执 | PASS：旧回执相等，fake POST0 |

候选3项/3失败/0错误（3.677秒）；当前3项全部通过（3.377秒）。
新候选自己的测试把未经远端确认的 `reconcile_step(status=released)` 断言为成功，
并固定断言本地含 `#` 的 run_id；两条断言应改用当前持久预约/线端身份合同。

原[三个独立探针](../U-067/independent-review-probes.py)也在新候选准确源码上
全部失败（3.021秒）：transport入口无持久预约、正文不进入第二轮、完成后撤权
抹去执行事实。没有撤掉当前正常代码制造RED；旧失败仍保留。
当前8ea2b4d也通过原三个探针（2.831秒），合计六项通过。

复现：使用已安装项目锁定依赖的Python，在独立导出的准确源码上运行：

```text
python evidence/U-086/candidate-boundary-probes.py <exact-source-directory>
python evidence/U-067/independent-review-probes.py <exact-source-directory>
```

Windows设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。
[记录](candidate-review.json)保存准确来源与私有日志SHA256，不包含日志正文。

## 原负责人接续范围

先从实时 `rewrite/charter-v1` 建立候选，保留 GovernanceStore 单一写入者、
dispatch.prepare/settle、work_model_turns、schema4兼容保护及U105/U106入口。
不要覆盖旧整文件或把预约重新移到派发之后。未知请求只按原线端 ID 核对，
不可把 interrupted、404 或本地取消解释为可释放。

当前 WorkExecution 确实没有 work取消入口；原模型页取消仅覆盖model_checks。
若继续该工程缺口，应先由原owner复评#40真实验收与所需工程前置的粒度，冻结
Work/attempt/command/model_request、当前授权、事件cursor、取消受理/远端结果
以及unknown预约合同，再RED→GREEN；复用现有loop和modeld通道。
这不授权新真实推理，也不关闭#40或父#22。

相邻115证据已可只读定位，详见[U-085源码复核](../U-085/2026-11-09-source-review.md)。
本轮模型真实调用0、生产切换0、迁移0。#61仍等既有明确迁移授权；#37仍等
获准共享的源码，原owner和blocked WIP保持。
