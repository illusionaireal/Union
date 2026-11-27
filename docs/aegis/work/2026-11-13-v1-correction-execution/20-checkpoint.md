# 续接检查点

## Current Checkpoint

2026-11-27 完成用户接续范围。#74、#75、#66、#46、#47 和 #76 已受控采用并在线读回完成。最后的 U-121 准确候选 `4aa5f96` 七项 CI 全绿，普通 Git 快进采用 `rewrite/charter-v1`，#76 v6/rev1294 完成且三项均勾选。973 Python（7 环境跳过）、496 前端、89 modeld、本机和 CI 各 168 项实际浏览器、独立权限/身份/计量复核通过。证据见 [U-121 采用记录](../../../../evidence/U-121/adoption-20261127.json)。以下条目保留各时点的历史。

2026-11-27 U121 组合候选复审：两个独立工程角色确认 scoped start ID、版本化资料、原执行恢复、迟到明确拒绝与未知及原回执的关联。前端全量 496、相关 Python 66、独立复核 Python 6 通过。原浏览器场景已观察实际受控注销、继续、重启读回、最终交付下载、保留决定；最新组合浏览器与固定本地 Python 全量仍在验证。在线 #76 v3 progress。证据见 [U-121 索引](../../../../evidence/U-121/README.md)。下一步通过后发布准确候选验证七项 CI，随后普通 Git 快进、看板验收及交付记录。

U121 开发现场：`6cd6954` 冻结合同和 ADR，编码前实际后端 HTTP RED 为 400 `invalid_request`（原 Work 命令不支持意图），前端 RED 为正常页只发送 `start_work`。正常页面端第一轮定向通过 37 项，后端原 Work/当前授权/原执行接续还在实施。受控浏览器驱动准备从无 Work 一次提交、丢响应、首次模型调用保持时注销、原作用域续做与重启查询、下载已交付结果和保留决定。隔离 provider 的测试保持/释放已实测，组合链尚待。在线 #76 仍 v3 progress。协调员完成前仍需要合成、两阶段复核、完整验收、准确 CI、远端和在线读回。

U121 TaskStartSnapshot 2026-11-27：真实 #76 v3 progress/rev1291，由相同实际在线用户持有，所有前置已完成。独立集成 checkout 以 clean `b0d0043` 创建 `codex/u121-intent-20261127`。冻结 [U-121 契约](../../../../specs/053-union-rewrite/u121-durable-work-intent-contract.md) 和 [ADR-0011](../../../decisions/0011-durable-work-intent.md) 后才写行为代码。后端与前端按不相交的代码路径实施，协调者独占 Git、看板、账本、浏览器与流程证据；受控整体验收仍待验证。

2026-11-27 U093 完整受控采用：`0e03e92` 的准确七项 CI 全绿，普通 Git 快进采用 `rewrite/charter-v1`，远端读回 `protected=false`。本地 957 Python（7 跳过）、475 前端、89 modeld、155 Chrome（13 次受控推理，真实 0）及两工程角色独立复核通过。在线 #47 v8 done/rev1289，三项检查完成；#76 用实际账号认领 v3 progress/rev1291，所有真实前置满足。见 [U-093 采用记录](../../../../evidence/U-093/adoption-20261127.json)。剩余整体验收为 U121 一次合法有界意图、原执行接续和按有效规则交付，先冻结事务、运行身份及文件责任。

2026-11-27 U093 接续：远端实读 `d04767f`；在线 revision 1286，#47 v5 progress、原 owner 与依赖一致，#76 尚待 #47。在 5be7 集成 checkout 组合 94bd 后端与原前端，本地 D 盘工作区保持原现场。独立内核和前端复核反例已经落入定向行为测试；目前本地 npm 全量（475 前端）通过，Python 最终全量、实际 Chrome 组合及准确提交七项 CI 待完成。当前证据见 [U-093 证据索引](../../../../evidence/U-093/README.md)。按 #47 全验收 → 任务分支及 CI → 普通 Git 采用与在线读回 → #76 准入的顺序继续。

U093 TaskStartSnapshot/readback：在线47v5 progress owner363、依赖全done；13:28前捕获两个checkout为clean、共同代码d04767f（前46所有业务源码与七CI5513相同）。root5be7创建codex/u093-input-integration-20261126，kernel94bd创建codex/u093-input-kernel-20261126；原46分支/历史保留。行为代码前冻结完整spec u093-work-input-contract和ADR0010，文档提交b638dbc已在两分支相同HEAD。新的两个工程实现任务按spec固定文件责任并并行；协调者独占Git/board/ledger/共享文档与最后顺序整合，独立规格→质量复审后完整#47验收，下一#76目标不能省略。

2026-11-26 13:18当前：准确5513cf6七CI全部success，普通Git快进采用rewrite并读回protected=false；online46 v12/revision1284、三checklist和owner363 done已确认。online47所有真实依赖done，从backlog准备ready后以实际user363认领v5/progress/revision1286（receipt host-private u092-complete-u093-claim.json）。47尚未写行为代码，下一步冻结完整输入合同/责任后strict TDD，随后76；74/75/66done保持。47设计报告host-private u093-precode-readback-20261126.md有重要接收/附入/观察/消费分离及内循环version/schema/私有正文审查。先提交本轮46采用文档并普通Git采用（仅过程，25份业务源码与已验5513一致），复用两个既有checkout；不重开原D盘dirty、恢复保护、丢原历史。

最终本地门槛2026-11-26：Python916/7skip/812.105秒exit0（u092-python-final.log、session10576已完成），npm445、实际Chrome135/11受控回环/真实0、构建兼容11与独立内核/UI/测试接缝均通过。25份准确源码与旧失败日志hash已归档verification-20261126.json/browser-20261126.json。当前只差本任务提交→准确七CI→普通Git快进采用与online46done；47/76目标保留。宿主SDK已录六行生成补丁经差分核对后仅逆向该patch，vendor恢复clean，不重置他人现场。后续测试若需SDK须再次prepare；构建产物仍为原验证字节。

#47只读预编码复核（尚未开工/采用，不是新产品事实）：沿原Work保存input ID/seq/hash/actor/责任版本，正文用同AU事务private store；必须复用U120 normalized command，避免不可变commands/audit复制正文。prepared附入原sealed请求与预约可靠关联；observed仅表示原模型收到，正式consumed须与当前owner成功adopt_turn/context同AU事务，采用/保存失败或false授权不消费。未知不再派、旧owner不能采用；长等待与重启仍能接受input。新schema6若有必要则只显式成功采用升级，现行work.py/work_dispatch/work_recovery三处写5要保持高版本，installer按input特征拒绝<=5，read不升级。#41反馈同源身份但正式反馈另由原owner；原profile原生long_job_new_input未验仍unsupported。待46实际done、最新board准入与源核对后再冻结完整合同和代码责任。

最新 2026-11-26 12:41：npm最终445前端/37管理/359行动安全、类型/build通过（u092-npm-final3.log，VITEST_MAX/MIN_THREADS=2/1与FORKS=2/1，仅宿主env未改仓库）；准确browser6最终135检查/11回环模型POST/真实0通过，包含U122与U092完整两次重启/原ID查询/同attempt与原工具正文。初次Python916/7skip失败2：读事件零写断言在prepared→dispatching合法worker写期间抽样竞争、真实驱动仍拦截旧chat不是新chat_body。只修tests观察/同步接缝，23受影响组合+独立4（含3次race）通过，所有production hash仍quality冻结值。第二次Python全量现运行session10576，日志u092-python-final.log；只有它通过才能最终完成，首轮失败保留u092-python-full.log和seams-before.log。此前paragraph的旧session与“运行中”说明均为上一时点。

剩余：finalPython读回→归集证据/过程与本地长期U070交付历史（不改变父卡状态）→严格仅本任务路径commit/push→准确SHA七CI→普通Git快进采用rewrite并读回（保护不得恢复）→online46全验done→47准入/合同/实现/同等级验收→76持久身份与自动交付。当前不可停止为74/75部分完成。vendor生成补丁仅opencode.ts已录six-line patch，CI需要prepare；采用前核对仅逆向此次生成差异。

2026-11-26 续接：目标仍是完成74/75/76及用户已明确授权的46/47/66；74/75/66已七CI采用并在线看板done，76不能省略。当前root是5be7 `codex/u092-integration-20261126@68ad090`；94bd kernel `4d339e1`已由协调者提交并cherry-pick。两份合同add/add仅保留获授权的复审补充，没有backend源码冲突。kernel全部冻结，stage1及独立质量/身份/计量复审通过；hash原CRLF变LF仅行尾，quality核对文本相同。

原Work恢复UI已接入；5→6→7正式行为测试，陌生实例回执与direct POST401/403重登录死端分别真实RED/GREEN。新成功owner只匹配原请求service/originServiceInstance；仅直接恢复POST已知认证拒绝保存refusedBeforeAcceptance，已返回response后权限失效或unknown+GET404不释放。49项恢复/治理schema5/资料/成果组合通过，schema5入口漏识别由实际browser和17项1RED查出后窄修，backend未变。最终build已过；最终npm/Python/browser仍运行，不能据旧npm称准确最终候选通过。

宿主日志：`C:/Users/曾驳/.codex/tmp/union-v1-resume-20261116/`。Python全量session76378从12:22开始，日志u092-python-full.log；当前browser5 session59945，npmfinal2 session61021，准确built兼容11项无skip已过session16861。browser前几轮失败分别missing UNION_BUN、错误Bun/未prepare的oauth导出、schema5前端入口；原失败全部保留。当前Node24.19.0在该tmp/node-v24.19.0-win-x64，Python D:/Project/Union/.venv/Scripts/python.exe 3.13.14，Bun D:/nvm4w/nodejs/node_modules/bun/bin/bun.exe 1.4.2。已用npm build:model-service准备固定SDK，vendor仅本轮opencode.ts六行已录补丁生成差异，任务采用前核对仅逆向此生成补丁；不能reset/clean/stash。

下一步：读回正在跑的检查与quality对UI最终复审；browser5带U122和恢复模块，验证两次重启、丢响应原ID、同attempt/工具文本连续与两轮真实本地modeld/SDK（真实模型0）。如失败先查真实证据、strict修复；全量/browser/独立复核/准确七CI及普通Git采用后，在线46完整done。然后在线准备/认领47冻结合同并实施，再76持久身份/自动交付。不因内核完成结束整体任务，保护按用户关闭不得恢复。

下方条目为上一时点记录，保留历史。

- Current todo: 74/75和66已完整done；继续46恢复、47输入、76持久业务意图自动交付
- Active slice: U-092
- Completed todos:
- #74/U120done；#75/U122与#66/U112以382fce1七CI成功普通Git采用，online done和全部checklist读回，437前端/873Python含7skip/124业务浏览器/116入口保持
- 46独立kernel已23恢复+3HTTP+11兼容及原相关63通过；stage1独立复核发现POST全局锁、旧异常释放新预约、最终host/epoch fence三问题，正RED/GREEN修复，未采用未整卡done
- Evidence refs:
- evidence/U-122/adoption.json
- evidence/U-112/README.md
- specs/053-union-rewrite/u092-work-recovery-contract.md
- Blocked on: none
- Next step: 记录75/66采用收口后固定root当前状态；kernel全部稳定后独立规格复审再工程质量/权限复核，顺序整合和原Work恢复UI/组合全量。46done才能47，最终76一次意图后台持续推进交付，原目标不省略

## Recent Checkpoint History

## Checkpoint Update

- Current todo: 完整完成74/75/76及46/47/66前置；75准确382fce1等待最后WindowsPythonCI，46kernel继续
- Active slice: U-122
- Completed todos:
- #74/U120done；用户关闭保护真实生效，e29fb49记录；root75代码0228b3b和消费者修复382fce1已推送，root无业务未提交变更
- #75完整437前端/873Python含7跳过/124资源资料成果浏览器/116入口复验/14定向和独立复核通过；准确382fce1已6CI成功，WindowsPython未结束；75在线review v5，66review v7，未冒称done
- 用户明确授权46交接及47/66必要前置；46v6 progress owner363，kernel在94bd codex/u092-recovery-20261126严格TDD实施，新增17+2HTTP+11兼容及原63相关通过；宽回归与审查仍待完成，不算整卡done
- Evidence refs:
- evidence/U-122/README.md
- evidence/U-122/verification.json
- evidence/U-112/README.md
- specs/053-union-rewrite/u092-work-recovery-contract.md
- Blocked on: none
- Next step: 382fce1七CI全过后普通Git采用并在线75/66完整done；kernel DONE后独立规格再工程审查，协调者提交/顺序整合并补原Work恢复UI与组合全量，46done后47持久输入，最终76完整后台意图交付
## Checkpoint Update

- Current todo: 完整完成用户74/75/76及已授权46/47/66前置；75最终浏览器，46独立kernel并行
- Active slice: U-122
- Completed todos:
- #74/U120已采用dc9431e并done，e29fb49关闭保护决定保留
- #75已认领；14定向/437前端npm全量/873Python含7跳过及独立复核通过；无未解决Important，浏览器准备consumer错误修复后重验中
- 用户已明确授权46责任交接和47/66前置；46v6及66v5 progress原历史保留，kernel在94bd任务checkout按冻结合同严格TDD实施；根5be7保留75未提交变更
- Evidence refs:
- specs/053-union-rewrite/u122-result-reader-contract.md
- specs/053-union-rewrite/u092-work-recovery-contract.md
- evidence/U-122/independent-review.md
- Blocked on: none
- Next step: 完成75实际浏览器五宽/下载/原Work隔离，提交/CI/普通Git采用与在线done；46kernel完成后独立规格再工程审查并顺序集成，协调者补恢复UI；再47及66完整验收，最终76不省略
## Checkpoint Update

- Current todo: 用户要求完成在线74/75/76；先实现U122成果阅读下载
- Active slice: U-122
- Completed todos:
- #74/U120已采用dc9431e，收口e29fb49；在线done，保护按用户关闭
- #75前置均done，当前user363a9919已认领progress；codex/u122-result-reader从e29fb49干净基线建立
- Evidence refs:
- specs/053-union-rewrite/u122-result-reader-contract.md
- Blocked on: #76仍需#46/#47/#66等；#46由codex-home持有，已异步请求明确交接授权，不能自行接管
- Next step: 按U122冻结合同观察新组织成果路由真实RED，最小接通正文与下载，再完整验收；等待#76前置交接答复期间独立推进#75
## Checkpoint Update

- Current todo: U120受控交付已完成；记录用户关闭分支保护决定并提交收口证据
- Active slice: U-120
- Completed todos:
- 候选dc9431e七项CI成功，18份源码与5份最终日志摘要一致，原873Python/425前端/104浏览器及独立复核保留
- 用户明确关闭rewrite保护；Git实际凭据执行DELETE204，随后GET404/分支200/protected=false；普通Git快进采用dc9431e并读回，无需网页登录
- 在线看板revision1265 #74 v10 done，原owner、完整三检查项及受控证据已读回；U112/U121/U124保持
- Evidence refs:
- evidence/U-120/README.md
- evidence/U-120/adoption.json
- evidence/U-120/verification.json
- Blocked on: none
- Next step: 仅提交本轮交接/采用证据并读回远端；本卡完成，不自行扩展其他卡。原保护不得自动恢复。
## Checkpoint Update

- Current todo: U120远端PR合入与完整在线验收
- Active slice: U-120
- Completed todos:
- 候选dc9431e已推送，18份源码摘要和5份最终日志核对一致，准确SHA七项CI全部success；原受控全量、104浏览器和独立权限复核证据保留
- 在线看板恢复；revision1262，U120 #74 v7 blocked，原owner保留，两个检查项、受控证据和GH006阻塞已读回；团队协助留言153已读回
- Evidence refs:
- evidence/U-120/README.md
- evidence/U-120/verification.json
- evidence/U-120/independent-review.md
- Blocked on: GitHub令牌创建PR/读取保护403；桌面比较页Sign in；非强推快进被GH006拒绝，要求PR。目标rewrite仍b4371d8，保护未修改。
- Next step: 等待仓库管理员完成已打开GitHub比较页登录；核对实际ref及最终候选CI，按已有合入授权完成PR交付/合入并读回。只在本卡完整出口通过后done。

## DriftCheckDraft

- Scope status: 用户74/75/76及46/47/66授权保持；74done，75工程/浏览器完整通过，66贯通通过，采用与在线done待准确候选；46独立kernel仍实施
- Compatibility status: 75只消费原Work/result_content/SQLite；437前端、873Python含7跳过、124真实本地浏览器及独立复核，旧有效兼容通过；SDK仅本轮已记录生成补丁逆向恢复原状态
- Retirement status: 旧ResultList JSON读取消费改绑同一正文实现，未新增正文数据库/循环/fallback；46仅冻结设计未称运行采用；用户关闭分支保护决定保持
- New risk signals:
- 只按本卡完整出口关闭75/66，不将准备/阅读工程升级76自动或真实/持续业务
- Advisory decision: continue
