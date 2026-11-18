# 续接检查点

## Current Checkpoint

- Current todo: U125共享验收修复的独立复核、最终远端SHA与PR，随后U126和U111贯通
- Active slice: U-125
- Completed todos:
- U110/U118已合并；U125独立身份复核、396前端、116浏览器、863 Python/12跳过通过
- 5个保留HTTP/SQLite探针41项结果、Node辅助2项、实际启动5项通过
- Evidence refs:
- evidence/U-125/README.md
- Blocked on: GitHub创建PR的凭据权限不足（已明确403，已询问用户配置；尚无答复）
- Next step: 提交推送已验证修复，读回最终SHA的远端检查；权限恢复后创建PR并交付U125，再认领U126

## 2026-11-18 全量收据与共享验收收尾

核对任务checkout `codex/u111-v1-organization-entry@348c828`，此前候选已推送且
与远端一致；集成基线仍 `2b3d281`。只续做原owner的U-111/U-125；revision1219
再次读回#65 v5/#79 v4 progress，#80 v1 backlog依#79，未认领或实施U-126。

Python一次性有界验证跨续接结束：863项、12跳过、741.052秒、退出0。
已禁用的一次性验证Scheduled Task精确注销；原业务定时任务未改。
中断日志与首次失败保留，此完整退出收据不重写旧历史。

候选CI `44231413637` 的offline checks通过，但console-browser在U086共享重启
片段等待已退役的界面文字。仅将该片段重绑到当前同源Core session/principal；
全局URL在VM缺失的首次失败保留，改用node:url后五探针41项结果通过。
原snapshot/结算/预约/原步骤/成果断言保留，未恢复旧UI或更改产品authority。
完整npm再次退出0（396前端及构建）。详见evidence/U-125/ci-consumer-repair.md。

PatchShape：共享验收消费者重绑；CanonicalOwner：Core session提供身份事实，
共享driver只负责验收读取；UpwardDrillSignal：旧页面断言已失去当前产品责任。
Decision：保留有效合同验证、不扩旧壳。原首页恢复并发失败原因仍未知。
Drift decision：continue，收尾已授权U125；PR写权限是外部交付阻塞，不把候选当done。

## 2026-11-16 历史续接（恢复保留）

已现场核对：原 PR #90 于11月13日合入 `f87d610`，head `1400d4f` 的14项CI通过，
在线U-110/U-118均done；下方旧“候选/PR待交付”描述仅保留为原时点历史。
当前集成 `2b3d281`，在原干净工作区切到 `codex/u111-v1-organization-entry`。
TaskStartSnapshot：原任务worktree的`756dc81`无dirty/index/untracked；fetch后旧分支
落后自身remote一个测试修正；新分支从当前rewrite建立，初始clean、无Git冲突。
用户 D盘原目录的已有修改及旧分支完全保留。

在线revision1218读回U-125/#79 progress v3，原user.id/owner保持；U-111父卡在制，
U-126/#80 backlog依U-125。HTTP200已写续接范围和实际分支；本机默认凭据属于另一成员，
本轮使用原用户给出的已授权凭据，仅在进程内使用、不保存值。连接使用本机现有代理。

当前todo：冻结U-111精确路由/异步/创建恢复合同；U-125真实RED/GREEN及HTTP/浏览器；
独立复核、全量、PR和子卡交付；随后U-126创建恢复及父卡贯通。过程记录复用本目录。
scope/owner以线上为准；合同 `s01-workspace-contract.md`，TDD strict。不得把U-111
入口完成当完整V1产品。当前无新增模型/部署/真实数据操作。Drift decision: continue。

### U-125 实施中（2026-11-16）

新App/Layout及组织列表/概况/八个范围明确入口已替换旧profile分流；workspace仍是
唯一身份/服务/AU选择owner。先观察入口14项失败；新增历史恢复隔离/协议拒绝5项失败，
路由2项、独立评审4项及跨入口拒绝后缓存复活1项均先RED再修复。
当前入口/工作区定向47项通过；治理53项、模型身份11项通过。旧手工Work/责任的正确
测试改为feature边界，未恢复旧壳。完整npm/浏览器仍待收口。

HTTP明确模板及原请求路径检查两轮独立评审通过，18项相关HTTP回归通过。
真实浏览器已发现支持的200字名称溢出，修复换行及移动菜单选择器后重建复测。
独立SPEC评审发现跨路由AU403缓存可在断网后复活；统一清除同AU各入口投影，
原回执不受此清除影响。未完成评审重验前不声称U-125完成。

必要共享接缝：新壳中的原CommandProvider补账户/同源服务恢复引用、停止legacy和
无归属后台查询、后台结果不改当前导航；完整目的/成功依据/约束与创建恢复由U-126
继续。在线#79已注明此边界，父/子原owner和在制状态保留。无业务/模型/部署扩权。

下一步：当前源码实际浏览器、npm全量、进行中的Python全量、SPEC重验和质量复核；
U-125证据/提交/在线交付后认领U-126。Drift decision: continue。

## 2026-11-13 历史检查点

2026-11-13，基线 `d27d543`，分支 `codex/v1-correction-execution-20261113`。

- U-110/#64：完整体验、VJ/PRD映射与40条追踪，独立复核和结构检查通过；线上review，实际owner为zbook-codex。
- U-118/#72：Controller/Broker新派发、自动采用和新安装退役；42项定向含1跳过，规格和质量独立复核通过；线上review。
- 完整检查：npm重跑通过（363前端及构建）；Python847项含9跳过通过。首次ModelsIdentity等待失败、单文件11项通过和重跑原记录全部保留，未宣称根因修复。
- 已先写入Kanban：U-119/#73、U-120/#74、U-121/#76、U-122/#75、U-123/#77、U-124/#78。U-112/113/114完整父验收保留，依赖无环；原4张在制owner/WIP保留。
- 当时：候选提交/PR与交付记录收口；完成U-110前置后实际认领并派发U-111。U-111只读准备已完成，未开始代码。
- 保留：原用户工作区dirty及落后状态、历史数据/请求/预约；无真实支出、部署或已安装配方改变。
- 宿主副本、实际Unix socket/Docker、全部新前端及真实/持续产品出口未验。

2026-11-18 helper 更新当前检查点时覆盖了未标记的历史段；上述原阶段内容已恢复保留。
历史状态仍只对应当时，不据此认领或确认完成。当前证据入口为90-evidence.md。
