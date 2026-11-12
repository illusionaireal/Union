2026-11-10：新补证02dc3f3的逐原始记录复核见[补证核对](supplement-record-audit/README.md)；三个运行分别绑定，modeld中断、真实调用数和完整回执仍按实际证据陈述。

# U-086 / #40：新候选与当前集成边界复核

2026-11-12 有界真实运行计划（**待授权、未执行**）：[bounded-real-run-plan.md](bounded-real-run-plan.md)。目的=第 4/5 项一次取证；上限 3 次真实调用/≤10 分钟；禁止新建 AU、补造快照、部署与迁移；remote_fact 恒 unknown。
2026-11-12 PR 描述（供协调者代开 PR）：[pr-ready-description.md](pr-ready-description.md)。标题/摘要/范围/验证表/复验指针/未闭合项一页备好；交付 head e7b1b0c。
2026-11-12 取消证据读取的后续校验失败诊断（复审包）：[合同·四反例·两控制](cancel-validation-diagnostics.md)。四路 GET 200 后的 principal/receipt 校验拒绝仍带四路 route/status；修复 c4b95b7，交付 head a858999。
2026-11-11 失败归档保留已观测路由结果（回应 PR83 P2）：[合同·RED·GREEN](cancel-failure-route-outcomes.md)。`readCancelEvidence` 失败时把 `http/route/status/code` 挂在 error 上，写入器写入 `<name>-failure.json`（仅路由与状态，无正文/凭据）；`exit22` 338/338。

2026-11-10 产品修复（待评审）：[一个不一致的 catalog 行不再让整个 `/api/session` 失败](session-409-skip-fix.md)。
`console.py` 的 legacy 分支仅跳过 `unsupported_capability`/`incompatible_state`，其余 CoreError 照旧上抛；
5 项新测试、全量 Python 822/11 跳过/0 失败、Node 320/320、管理 37/37。仅供协调者评审后采用。

2026-11-10 `/api/session` 在 core_v1 AU 创建期间可能 409（前快照缺失根因假设）：
[只读归因与建议](session-409-during-core-creation.md)。catalog 行仍记 legacy_v0 而目录已是
core_v1 时，`session_info` 的 legacy 分支会被 `_catalog_engine` 拒绝、整个 `/api/session` 409；
重启后一致才成功——解释「前侧 117B、后侧 6643B」。未改产品代码，建议修法见文内。

2026-11-10 把「重启后无新增派发」接进中断驱动（严格 TDD）：[合同·RED·GREEN](replay-observation-wiring.md)。
新增 `scripts/exit22-replay-observation.cjs` 记录器（observed / unavailable / failed 三态，只在
两侧可用时断言零派发），驱动在 `restartComparison` 之后落盘 `replay-observation.json`；
`exit22` 320/320 通过，既有源码切片用例未受影响。

2026-11-10 重启前后读取的归因缺口（严格 TDD）：[合同·RED·GREEN](restart-read-diagnostics.md)。
`readSnapshot` 原先失败只抛通用状态断言，现按路由归因（键名+路由+状态+Core 错误码）并保持
AssertionError 类型；3 项新测试，`exit22` 317/317 通过（过程中修正了一处真实回归）。

2026-11-10 重启后「无新增派发」观测（严格 TDD）：[合同·RED·GREEN](replay-no-dispatch-observation.md)。
新增只读 `observeNoNewDispatch`（比较 attempts、model_request 去重数、budget.used），
前侧缺失时返回 `unavailable` 而非猜测；5 项测试、`exit22` 314/314 通过。尚未接入驱动主流程。

2026-11-10 取消证据读取的归因缺口（严格 TDD）：[合同·RED·GREEN](cancel-evidence-attribution.md)。
`scripts/exit22-cancel-evidence.cjs` 原先失败只抛通用状态断言，无法归因到路由；现先记录四条
路由的 HTTP 结果、失败信息含键名/路由/状态/Core 错误码。新增 3 项测试、`exit22` 309/309 通过；
只提升可归因性，不产生新的真实运行事实。

2026-11-10 按协调者 B 口径的逐项补证映射：[原 ID 记录对照](original-id-supplement-2026-11-10.md)。
把取消输出 events、cancel command/身份一致、受理-interrupted-远端未知三分、同运行前后预约与用量、
重启重放零派发、源码/服务/运行身份绑定六项逐条标为「已记录／未记录／仅受控断言」，并指出可只读
补证与不可补造的分界；不新增模型调用、缺失用量不补 0、历史失败保留。

2026-11-10 收尾就绪度陈述：[已覆盖与未覆盖的真实出口](closure-readiness-2026-11-10.md)。
汇总集成 head `faa5a4c` 上的本地自动化面（306 Node / 812 Python 全绿）与仍开放的真实
出口（真实输出后取消、真实取消受理/远端事实、真实用量费用、真实条件下重开不派发、
准确 head CI 与最近增量的非实施复核）。该陈述不关闭任何出口，真实授权仍在用户侧。

2026-11-10 集成 head `faa5a4c` 全量回归：本机 `.venv` 运行 `python -m unittest discover -v`
得 812 项全过（skipped 11，exit 0），同期 Node `exit22` 306/306；历史记录的环境性失败
`test_binding_rejects_board_failure…`（WinError 1314）本次正常通过，未为它改动产品代码。
见[全量回归记录](daily-full-python-faa5a4c.md)。该记录只覆盖本地自动化面，真实集成、
用户验收、发布就绪与持续运行仍按 `docs/FORMAL_DEVELOPMENT.md` 分别另验；真实出口未关闭。

2026-11-09 重开现在同时保留原成果来源、完整记录和交付引用，不能仅凭相同摘要
掩盖成果事实变更。18个Node/9个实际HTTP浏览器反例RED→GREEN，见
[原成果持久性](result-provenance/README.md)。仍须当前head CI和非实施复核，
原owner/WIP与真实父出口保持，真实调用0。

2026-11-09 两份一致但错误的预算快照不再通过重开验收；按全部used/unknown步进
逐项计数，保留released和未知用量语义。严格RED与246相关Node、7实际Chrome
场景见[预算守恒](budget-conservation/README.md)。仍需准确head CI与非实施复核，
原DSH owner和真实父出口保持，真实模型0。

2026-11-09 登记响应断体恢复：原助手在 start_work 已落盘、HTTP200头后正文
中断时一直等待，并可忽略完整错误POST回执。两个完整登记片段实际Chrome/
Core HTTP/SQLite先2正常通过/8反例失败，再10项通过，原16浏览器回归通过。
保留页面原ID查询、已知403与完整错回执拒绝，零模型登记；见
[合同与验证](registration-response-body/README.md)。候选继承PR64，须各自
独立工程角色复核与准确head CI；原owner/WIP及真实父出口保持。

2026-11-09 PR63接续：取消HTTP200响应头后正文断线会卡住验收driver；实际
Chrome/Core HTTP/SQLite截断反例RED后，改为等待原请求成功或失败结束事件，
再经原页面控件/原GET恢复。四项新故障场景及原八项浏览器通过，已知403与完整
错回执仍拒绝，原owner/真实出口保留。见[合同与验证](cancel-response-body/README.md)。
本增量仍需准确head CI及另一工程角色复核，不能沿用PR63旧head批准。

2026-11-09 原请求页面取消验收补漏：中断driver改为原Work实际取消按钮，
刷新后从原取消请求控件GET恢复，POST丢失不补发。三个实际Chrome/HTTP/SQLite
原源RED→GREEN，八项浏览器和216相关Node边界通过；见
[合同与验证](page-cancel-action/README.md)。基于PR62，不自批候选，不关闭
DSH负责的真实出口；无新增真实推理。

2026-11-09 原成果采用/交付页面验收补漏：移除driver直接API采用/交付和手工
finish_attempt补救，实际操作同一Work/result的Core控件，严格核对原成果交付。
7项原源RED→GREEN、实际Chrome/CoreHTTP/SQLite缺失控件反例成对验证；见
[本轮合同与验证](page-delivery-gate/README.md)。仍待非实施角色复核/准确head CI，
DSH owner及真实出口保持，无新增真实推理。

2026-11-09 输出到取消恢复的主体传递补漏：当前作者abef544正常链路因
outputObservation缺principal_id而拒绝原GET，独立片段测试未覆盖衔接。
本次两行修复经原源4项RED→GREEN及实际Chrome/Core/SQLite成对验证；
[合同、证据与保留边界](reader-binding/README.md)。DSH原owner/真实出口保持，
本实施会话待另一工程角色复核/当前head CI，不自批、不新增真实推理。

2026-11-09 最终下载会话核验组合：DSH修复1bd324a与PR58原取消恢复合并，
新增常规CI三项竞态反例，旧源1PASS/3FAIL→组合4PASS。原相关134项、两组
实际Chrome/HTTP/SQLite通过；双方实施与独立复核分开记录，见
[组合及保留边界](final-read-combination/README.md)。真实调用0，原owner/真实出口保持。

2026-11-09 原取消GET重开协助候选：原源34项1通过33失败，修复后34全通过，
相关134 Node和实际Chrome/HTTP/SQLite原回执恢复通过；仅GET取证，fake1/cancel1/
真实0。见[原取消回执恢复](cancel-receipt-recovery/README.md)。当前head CI与另一
工程角色复核仍是采用条件，不据本断言修复关闭DSH负责的#40或真实父出口。

2026-11-09 原Core快照恢复协助：两个验收driver改用固定原AU/Work的Core前后
快照，核对完整原请求/用量/预约集合；40项原源反例3通过37失败，扩展相关100项
与实际Chrome/HTTP/SQLite通过，真实调用0。见[合同、失败与验证](restart-snapshot/README.md)。
这是待独立工程复核/当前CI的断言候选；DSH owner与139旧失败、真实出口保留。

2026-11-09 download restart assistance: the original AU/Work/result, digest,
delivery binding and HTTP status are now checked together. Latest author RED,
17-probe GREEN and full validation are indexed in
[the scoped repair](download-reopen-binding/README.md). This implementation
awaits independent review/current CI; real acceptance and DSH ownership remain.

2026-11-09 验收宿主协助：作者096815e的transport会替换产品保存的连接/grant，
真实回环HTTP与Console重启反例已先RED，再复用产品factory修复。
见[范围、验证与剩余出口](host-connection-integrity.md)。本会话是该修复实施者，
须另一工程角色复核及准确head CI；不据此采用原127完整真实验收声明。

2026-11-09 宿主最小集成候选：PR45准确`cfe0631`已获另一工程角色
chatGPT-online的限定复核5821070358；本轮从实际`d209a0e`引入完全相同的
宿主、测试与原证据，未导入作者driver或127–130真实记录。9项HTTP/重启
回归通过；完整验证与当前CI分别记录，见[集成范围](host-integration.md)。
原owner/真实出口保持，新增真实调用0。

2026-11-09 作者严格下载候选 `bdbbb9b` / `1d9ed8e` 已独立复核：旧错误正文、
空成果、错成果三个反例已修复；新11项离线检查7通过、4失败、0运行错误，
仍缺下载HTTP/AU/Work与重启原成果核对。129实际保存2条请求、用量1032/898，
before仍是legacy错误；见[准确范围与可运行探针](strict-download-review.md)。
作者保留driver修复，原证据/owner/真实出口不变，本执行者真实调用0。

2026-11-09 最终真实中断记录 `1e490d0` 已独立核对：最终保存两条请求，
已完成438/43与第二条unknown分开；三个新增离线反例显示取消前输出、
取消回执身份和重启后预约断言仍缺失。见[准确证据与可运行探针](final-interrupt-review.md)。
未改作者driver/原证据，未新增真实调用；#40与父#22完整真实出口保持。

2026-11-09 原attempt关闭后恢复：PR44 `c6c13f2`在成果采用/交付后会隐藏原
run_loop或显示旧准备ID；4项DOM及实际Chrome RED后修复，46相关DOM、
U106 Chrome19与U086 Chrome18/19通过。见[补漏与完整验证](closed-attempt-recovery.md)。
仍是受控候选，需新head CI及另一角色独立复核，原owner和真实出口保持。

2026-11-09 页面递进恢复：原GET先确认取消意图后，页面现在能接纳后续送达
观察并在刷新后展示原回执；5 DOM与实际Chrome RED后修复，42相关DOM及
Chrome18/19通过。作者53ed829准确复核7用例失败；组合d93b3cf保留其历史，
服务端维持19afff3已验证字节。见[实施与组合处置](page-delivery-progress.md)。
本页面与此前服务端增量仍待另一工程角色复核/准确head CI，真实出口不变。
接续完整Python792项/9跳过通过、npm339前端通过；最终组合dfa5bfe补齐真实
集成祖先并保留作者fcbc932的126证据，受测源码不变。原未完成全量记录保留。
随后仅合并作者c0c1787交接。PR43旧head已自动并入作者分支，新页面及完整
组合改由接续草稿评审到rewrite；旧PR状态不代表本次候选已经采用。

2026-11-09 最新组合修复：作者a8c7280与页面915cc15合为66c97a8；原取消
POST重放和GET共用完整性校验、只读快照，原观察不被覆盖。9项针对性用例、
原6+2探针及实际Chrome15/16项通过，见[实施与验证](delivery-recovery-fix.md)。
本增量与页面仍待另一工程角色复核/准确head CI；不提前关闭真实出口。
下列“仍失败/由原owner续修”均为各自候选时点的历史。

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

2026-11-09 前次：a3bb2cc 的预算保护通过，但自动取消入口、丢响应恢复和
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

PR48/PR49 are combined in a separate, not-yet-adopted candidate; both histories
and the independent fixture review gate are preserved. See
[the exact integration inputs](host-fixture-integration.md).

## Original output before interruption (2026-11-09)

The scoped [original-output gate repair](original-output-gate/README.md)
retains DSH ownership and the real parent exits. It fixes optional/mismatched
event acceptance with31 executable offline tests; it does not run the real
driver or approve itself. Exact source, failures and validation are indexed.

PR53 current-integration refresh: [conflict resolution and combined validation](host-fixture-current-integration.md).
This candidate preserves both histories and current U108; host and fixture
are independently reviewed, with final-head CI pending before rewrite adoption.

Single preparation: [one original AU and grant per acceptance run](single-setup/README.md).
Strict RED/GREEN and real Core/SQLite creation checks; no real inference or grant.
Independent review and exact-head CI are still required before integration.

Core registration acceptance: [page entry and original command recovery](page-registration/README.md).
Full driver prefixes run on disposable Core/SQLite; no model request or real grant.
Independent review and current-head CI remain adoption gates.

Observed call settlement: [reject released after original output](observed-settlement/README.md).
Two acceptance assertions tightened after actual fragment and HTTP/browser RED.
Unknown reservation and original facts remain; no product accounting changes or real inference.

Reopened download: [read and verify the original body after restart](reopened-download/README.md).
The actual acceptance tail now checks a scoped result GET, current identity,
UTF-8 bytes and digest; metadata alone cannot claim the body survived.
Controlled evidence only; the implementation does not independently approve itself.

Material/source gate: [require the original document-read receipt before delivery](material-read/README.md).
The original candidate must cite a persisted read of the actual synthetic bytes;
nonce/digest checks alone no longer pass. Controlled checks do not close real exits.

2026-11-10: [Independent recheck of revised session and replay candidates](recheck-1730a11-da316ed-20261110/README.md) verifies partial repairs and records the remaining contract and same-count diagnostic gaps. This is controlled review evidence, not candidate adoption.

## 2026-11-10 session resolution repair recheck

[Independent 5545d4f review](recheck-5545d4f-20261110/README.md): all four original HTTP probes pass; 36 session/integrity regressions ran with one platform skip. Damaged creation audit still rejects. Replay/cancellation findings and full real acceptance remain open; product candidate is not adopted.

## 2026-11-10 replay and cancellation driver recheck

[Independent 7dd23fc review](recheck-7dd23fc-20261110/README.md): all five original replay probes pass. Four cancellation call-site controls pass; two new durable-diagnostic probes still lose completed HTTP outcomes. Sixteen affected author checks pass. This is bounded evidence, not combined-product adoption or real acceptance.
