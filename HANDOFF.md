# 当前工程交接

## 2026-11-02：用户确认从MVP进入正式开发

阶段与交付门槛已固化到[正式开发标准](docs/FORMAL_DEVELOPMENT.md)。工程、真实集成、用户闭环、发布与持续运行分别验收；原模型/订阅/工作区/主机与经营阻塞不升级。U-053记录阶段决定，下一就绪工程项U-054准备候选版安装升级回滚验收包；具体负责人待认领，不代表公司自主改进。

## 2026-11-02：043登录与模型接入0–5工程交付

持久管理员身份、AU配置迁移、离线目录、多协议、岗位回退、上下文/多模态及四类成本已接入正式React与运行时。393项Python（5平台跳过）、15项Chromium、37前端检查及独立52/56项权限费用复核通过；真实供应商0，私有订阅最终登录/权限/组织使用、NAS部署和整体031对标仍未验。旧D盘工作与备份保留，新worktree承接本轮改动。使用见[docs/MODEL_ACCESS.md](docs/MODEL_ACCESS.md)，证据043。

## 2026-11-01：订阅认证故障修复（042）

U-046修复Go仅Key与ChatGPT旧设备授权失败；官方v2双供应商start probe有真实URL并取消测试attempt，实际账号仍待用户登录。回调同owner/原attempt/固定目标、单次预约，原未知精准人工诊断保留原字节和审计。298 Python、37前端/类型/构建和独立8项及11项HTTPS浏览器检查通过，浏览器账号动作明确替身。真实模型0、调度关闭；详见042。


## 2026-11-01：U-045 AI-UNION内订阅配置与实际HTTPS工作台

用户明确没有已有网址，要求正式AI-UNION前端配置Go和ChatGPT，不SSH/独立OpenCode页。/models订阅区、固定认证后端、私有凭据、未知核对/会话隔离及NAS HTTPS入口已实现；npm检查34前端、Python290通过，实际TLS浏览器8项及桌面/320px已验。独立权限复核见本轮041；真实账号未输入、模型调用0，不启用调度、不关闭U-044沙箱阻塞，也不迁移旧公司状态。U-045受控完成后在制上限恢复3。新服务为LAN私有原型，自签证书首次需核对指纹，公共账户/多租户生产登录尚未实现。见evidence/041-subscription-connections。

## 2026-11-01：NAS开发调度器默认关闭部署与U-037浏览器收口

用户提供root SSH并要求按Astra/Sol交接搭建。专用dev已接入用户推送53dd96b快照，固定工具链/Chromium、npm检查和Python279项、工作台61项/网关12项真实浏览器通过；桌面/320px已审，U-037以受控范围完成，U-039真实实例不变。新增U-044承接外部调度器，释放U-037后在制仍3/3，无需扩大上限。

控制器/broker/CLI/systemd已安装但enabled=false、max_calls=0、timer disabled；DSM4.4实际bwrap user namespace失败、官方设备登录403，未注入真实认证、真实模型调用0。U-044保持blocked，下一步选择Linux VM/执行节点、假凭据拒读、官方认证/有限额度与独立复核。U-041热配置/恢复/整体验收仍blocked，原公司状态不迁移、不据宿主Docker推定成员工具可用。详见[evidence/030-dev-orchestrator/README.md](evidence/030-dev-orchestrator/README.md)。未推送、公开发布、合并main或改生产；本地原用户工作区保留。

## 2026-11-01：检查点只做lstat与本地提交未同步（040）

Astra完整规划、Sol撤掉所有原检查点SQLite连接/文件头读取，保留调用签名，仅harness/固定路径lstat；存在/异常unknown、明确缺失false，无匹配session仍false。true是兼容协议但当前无生产来源；不靠伪造true维持测试。定向50、Python260、独立Astra94项和npm完整检查（前端31项/类型/构建）通过；独立明确报告无阻断缺陷，但书面长结论因额度中断，不称整体独立验收完成。两项有效red均来自旧实现，首个尝试的hash fixture自身被guard拦截另存，不把它归生产bug。详见[040](evidence/040-checkpoint-metadata/README.md)。

移除观察连接使DELETE→WAL/路径替换的旧connect入口不触达，不宣称外部转换已执行或全HTTP/并发绝不写文件。路径类型/权限错误未知，缺失仅探测时事实；组织库/文件系统非原子。Harness真实SDK恢复/锁/授权未改。下一小时先冻结已有HarnessExecutor在连接禁用/revision变化后的撤销生效点，再SDK/回环HTTP复现；不要自动重建true元数据。U-041仍blocked，热配置/真实恢复/浏览器/整体复核保留，U-042不扩大。

GitHub插件/ls-remote核对远端dev仍b39c06c；此前提交仅本地commit，未push，因此GitHub看不到。基线本地e0d04c7领先16提交；用户docs/research/资料未动，当前批完成后仍仅本地保存，不隐含声称远端CI或发布。原公司本地仍bootstrap/paused、0成员/工作/成果/调用，无模型/工作区、Docker/Chromium。未推送/发布/付费/合并main/改生产。

## 2026-10-31：WAL观察竞态局部修复与可见度退让（039）

Astra完整规划、Sol实际SDK/SQLite复现：sidecar预检通过后关闭最后writer，观察SELECT重建wal/shm；以writer关闭后的基线归因。runtime_view._checkpoint仅对已观察WAL早退None，不再connect；通常SDK检查点现为unknown。两项red后green，定向48、Python258、独立Astra92及npm完整检查（前端31项/类型/构建）通过；非WAL正例仅fixture写完SDK后显式转DELETE，保留正文禁止读取/会话与AU隔离，HTTP同时有WAL未知与非WAL正例。见[039](evidence/039-wal-observation/README.md)。没有改Harness/恢复/授权或使用immutable/复制库。

重要：race-after.json已证明DELETE头预检后外部切WAL仍可创建sidecars并返回true；路径替换/跨库也未协调，不可称任意并发零文件副作用。现行spec028已更新，历史033证据勿改写。下一小时先冻结这些残余场景的保证，再选择独立观察元数据或最小读写协调方案；不靠重复is_file预检宣称闭合，不先扩U-042。U-041仍blocked，热配置、真实恢复、Chromium/整体验收未过。

20:40公司本地仍bootstrap/paused、0成员/工作/成果/调用，无模型/工作区，Docker/Chromium不可用，真实供应商/主机资源阻塞保持。验证解释器.union/validation-20261031-0940/bin/python可用，接手先检查；用户docs/research/保留。未推送/发布/付费/合并main/改生产。

## 2026-10-31：A03心跳TTL与迟到回执子集（038）

Astra完整规划、Sol新增tests/test_activity_receipts.py四项测试，独立Astra83项通过，Python全量256项及npm完整检查（前端31项/类型/构建）通过。真实首拍/UID/锁/Thread与正常清理保留，只patch activity自身time和续拍等待：age0/5确认、5.001/负age不确认，原owner/文件/锁仍在，读取不恢复/写业务状态，第二Runner拒绝。过期不撤销合法回执；实际Runner启动recover→unknown和正式reconcile后新run期间，旧work/progress被拒、旧fail_run无效，仅新成果落库。无生产改动，首轮失败仅测试未预计usage的cost未知标准化。见[038证据](evidence/038-activity-boundaries/README.md)。

不能把run.status/工作版本及本地互斥改称独立epoch/owner-token fencing；也未验证真实续拍可靠性、进程崩溃、供应商迟到网络响应、跨进程/主机或VPS恢复。U-041仍blocked。下一小时先按Astra建议确定性复现checkpoint sidecar预检至connect TOCTOU，记录实际文件变化，再冻结保守只读契约并最小修复；不先扩U-042。WAL/跨库、已有Executor热配置、真实恢复、Chromium A11及整体复核保留。

19:37公司本地仍筹建/暂停、0成员/工作/成果/调用，无模型/工作区、Docker/Chromium；模型授权、真实容器/镜像、持久主机/SSH、New API阻塞未解除。验证解释器.union/validation-20261031-0940/bin/python可用，接手先检查；docs/research/用户资料保留。本轮未推送/发布/付费/合并main/改生产。

## 2026-10-31：A06 SDK版本与交接隔离（037）

基线dev@6ed3470，Astra完整规划、Sol新增tests/test_session_revisions.py七项行为测试，独立Astra曾因额度中断，18时恢复并最终54项通过；Python全量252项及npm完整检查（前端31项/类型/构建）通过。无生产改动；同版本paused/continued续接为对照，连接/workspace revision各仅改变目标绑定字段，正式handoff整体变化；新session/key无旧草稿，旧row/run/用量、非空workspace回执和旧thread checkpoint/writes保留。新factory禁用连接零消耗；禁用工作区及HTTP在途正式岗位撤权不调用容器、无新命令回执，模型用量保留。见[037](evidence/037-session-revisions/README.md)。

初期失败是测试读取最新delta checkpoint为完整内容、期待单步correction而非blocked及feedback必有值；均纠正测试，未证明生产bug。SDK历史用get_tuple确认根存在、list读取历史；同版本用例证明同thread历史续接，不额外宣称已直接断言read_file的ToolMessage正文。旧Executor连接快照热撤销和在途配置竞态未验。

下一小时首项A03：先核对activity/owner/receipt已有机制，冻结直接心跳时间过期、旧实例迟到的最小行为用例；不把owner退出当过期，有失败才修复。U-041仍blocked，WAL/跨库、真实恢复、Chromium A11和整体复核未过，U-042不先扩大。18:38公司本地仍bootstrap/paused、0成员/工作/成果/调用，无模型/工作区；真实Docker/主机/供应商阻塞未解除。验证解释器.union/validation-20261031-0940/bin/python仍可用，接手先检查；用户docs/research/保留。本轮未推送/发布/付费/合并main/改生产。

## 2026-10-31：实际HTTP验证与剩余A03/A06证据（036）

Astra完整规划，Sol新增tests/test_runtime_http.py六项实际Server/cookie组合测试，独立Astra115项子集复核PASS；最终Python245项及npm完整检查（含前端31项/类型/构建）通过。全局/限域board与observer、同ID跨AU、完整响应私有哨兵、伪造参数、稳定读取、正式状态链和当前授权变化有证据。无生产缺陷，生产代码未改；初次fixture缺token_limit_field被合法拒绝，补齐后通过。详见[036证据/矩阵](evidence/036-runtime-http-observation/README.md)。

U-041整体仍blocked，切勿把六项HTTP通过写成A01–A06全项验收。下一小时首项A06：用实际SDK分别验证连接revision、工作区revision、有效任职变化产生新session，旧消息不进入新请求、历史保留、当前权限重检；有失败才最小修复。随后A03直接心跳时间过期和旧owner迟到回执。WAL TOCTOU/跨库非原子、真实恢复、Chromium和整体独立验收保留。13:42原公司本地仍筹建/暂停、0成员/工作/成果/调用，无模型/工作区绑定，不是VPS现场。

验证解释器.union/validation-20261031-0940/bin/python仍可执行，接手先核查；未重装。主账保持16done=10文档+6受控、在制3/3、阻塞7、就绪0，资源阻塞未解除。未推送、发布、付费、合并main或修改生产；docs/research/用户资料未动。

## 2026-10-31：派发观察统一与暂停诊断修正（035）

按Astra实际返回的优先级与直接消费者决策，Sol将snapshot派发状态单次计算后传runtime：unknown始终needs_review；否则暂停且running/host活跃为pause_requested；否则paused或enabled。corp诊断以真实暂停标志决定paused blocker，不把unknown误报用户暂停。仅观察/诊断与文案变更，runner/Engine/权限/next_step/成员状态未改。239项Python、31项前端通过，独立Astra局部PASS；见[035](evidence/035-dispatch-observation/README.md)。

12:40原公司本地只读诊断仍筹建/暂停、0成员/工作/成果/调用，未绑定模型/工作区；不是VPS现场。旧环境已缺失，新解释器.union/validation-20261031-0940/bin/python本段可用，接手先检查。U-041仍blocked；下一小时按028对完整观察面补独立服务端/HTTP权限、AU隔离、只读矩阵，再最小修失败项；不将服务端证据替代Chromium或整体通过。WAL竞态、跨库非原子、真实主机/模型阻塞保留，未推送/付费/发布/改生产。

## 2026-10-31：未登记部署的诚实投影（034）

Astra完整规划、Sol实现、独立Astra局部复核PASS。无持久runtime登记时mode改为unregistered、中性名称、空实例能力声明，身份/时间仍null；宿主活性与匹配owner的running引用独立保留，不猜Console/CLI/service部署。资源页区分部署/活性，兼容其他mode的明确fixture。234项Python与29项前端通过，见[034证据](evidence/034-unregistered-runtime/README.md)。未加注册、控制或权限，原公司08:39本地只读检查仍筹建/暂停、0成员/工作/成果/调用。

U-041整体仍blocked。下一项先复现顶层与runtime派发口径在unknown未暂停、暂停且只有宿主活性时的差异，由Astra冻结契约、Sol仅修观察一致性，不改调度/授权；WAL竞态、跨库非原子、实际浏览器和完整边界继续待验。本轮重建固定依赖解释器.union/validation-20261031-0837/bin/python，后续先检查可执行性。未推送、发布、付费或修改main/生产。

## 2026-10-31：检查点存在性与接续提示纠偏（033）

Astra本轮已恢复响应并完成完整规划，Sol实现，另一独立Astra局部复核PASS。修复按session.status推断检查点和paused=>possible：现查本AU本会话根namespace行存在三态，取消安全恢复暗示；成员页区分有/无/未知。真实SDK本地fixture、WAL/正文排除及实际connect错误均有回归，见[033](evidence/033-checkpoint-observation/README.md)。未改Harness授权/恢复、组织流程或真实公司配置。

07:47本地原公司仍bootstrap/paused，成员/工作/成果/调用0，模型/工作区未绑定；不是远端生产检查。WAL格式且缺sidecars时返回unknown，不开库；预检到连接仍有TOCTOU，不能声称任意并发绝对零新增文件或原子快照。完整U-041仍blocked，下一小时先复现未登记时runtime.mode/name仍固定embedded/本地控制台的部署描述，再冻结只读契约并最小修复；实际浏览器及完整边界复核仍待完成。

## 2026-10-31：代表工作区许可摘要修复（032）

基于dev@85647a7，修复成员兼任时workspace摘要任选首任职导致的双向误报；跟随既有代表工作有效任职，无代表工作不猜岗位，禁用/未配置原因与revision保持。只改观察投影，真实命令包/暂停/版本/任职检查不变。Astra实际给出核心取舍后因usage limit终止完整规划；Sol据已收到方案实现与测试，另一独立Sol复核PASS，不能称Astra完成了后续复核。222项Python和59项定向通过，见[032证据](evidence/032-runtime-workspace/README.md)。

07:33本地原公司仍bootstrap/paused、0成员/工作/成果/调用，未绑定模型或工作区，无Docker CLI；远端dev仍b39c06c，未推送或更改生产。验证解释器须先核对存在性，本轮重建.union/validation-20261031-0731/bin/python并装固定依赖，未覆盖原.venv或用户docs/research/资料。

U-041完整验收仍blocked；下一小时首项为_session从会话status直接推断has_checkpoint的确定性缺口：先由可用Astra冻结只读、无正文泄漏的存在性契约，再由Sol测试修复；存在检查点不等于当前授权或可安全恢复。部署描述、实际Chromium矩阵与完整观察边界复核继续等待，不自动开启真实调用或托管。Astra额度不足需明确记录，不冒称指定模型规划/复核完成。

## 2026-10-31 02:45：Astra规划/局部复核，Sol修复成员工作状态

基于dev@ed0d411，完成U-041工作状态及代表项选择的局部修复：blocked/failed/paused/needs_review不再被忽略；unknown优先于待办，ready选择跳过未满足依赖，全AU在途/unknown不冒报可派发。独立Astra发现handoff后旧成员会话被新成员行引用，已补先红后绿回归并限制run归属，最终局部PASS。215项Python全量通过，详见[031证据与逐项完成核查](evidence/031-member-work-state/README.md)。

02:44本地原公司只读检查仍bootstrap/paused，0成员/工作/成果/调用，未绑定模型或工作区；这是本地现有数据，不是远端VPS检查。本轮新建固定依赖验证解释器`.union/validation-20261031-0237/bin/python`，上一轮临时解释器已不存在，后续先检查实际环境。未推送、合并main、发布、付费或更改生产。

U-041整体仍blocked，下一小时先处理多任职工作区摘要：现有_workspace只取首个有效任职，可能与代表工作岗位不一致。由Astra明确最小只读契约，Sol加正式Engine行为回归，不扩权。检查点/恢复、部署描述、实际浏览器A01–A06/A11及完整观察边界复核仍待完成；Chromium缺失不能掩盖这些代码缺口。原WIP3与恢复条件保持。

## 2026-10-31：Astra规划/复核、Sol修复最近执行引用

基于 `dev@97119e5`，GPT-6 Astra 规划，GPT-6.1 Sol 实施，另一独立 Astra 代理复核。修复成员 recent_run 取最早回执及空闲会话跟随旧回执的问题，保留成员隔离、旧到新 runs 顺序和当前工作优先的会话引用。三项新增回归先失败后通过；固定Python依赖已在独立验证环境恢复，全量205项通过。详见[030证据](evidence/030-runtime-recent-run/README.md)。

U-041完整验收仍未通过：后续应先确定工作状态优先级并复现 blocked/failed/paused 被显示为 idle 的问题，再补兼任工作区、检查点/部署描述及浏览器矩阵。不能继续把 U-041 视为只差 Chromium。主账补记原开始时间、实际负责人及阻塞，临时在制上限3与恢复条件见[排期纠偏](management/reviews/2026-10-31-runtime-observation.md)。本轮双模型是本环境中的工程代理协作；VPS常驻链、AU成员调用和公司真实运行未验收。未推送或修改生产环境。

## 2026-10-30：U-041 成员运行观察受控实现，浏览器验收待环境

本地 `dev` 新增只读 runtime/member/session/workspace 摘要与成员、资源页展示；成员工作、活性和部署位置分开表达，不新增派发、托管控制或宿主权限。受控后端/前端检查通过，详见 [029 证据](evidence/029-member-runtime-observation/README.md)。当前环境缺少 Playwright Chromium，A01–A06/A11 浏览器验证及独立观察边界复核未做；U-041 不能关闭，U-042 和真实托管保持未实现。主账在制上限已由 U-007/U-037 占满，因此本轮不虚构认领或改变 U-041 状态；下次应在带 Chromium 的环境补齐浏览器验收，再按主账流程处理状态。

追加：已为新成员/资源观察界面添加 2 项组件行为检查；前端共22项、定向Python共27项通过。该项只增强受控验证，不改变 U-041 的浏览器/独立复核阻塞结论。

2026-10-30 另按 CI 命令重试 `npx playwright-core install chromium`，下载的 Chrome 压缩包显示 0 MiB 且无法解压；环境仍无法运行 Playwright。该可复现阻塞已补入029证据，不要将安装失败归为 U-041 功能或浏览器测试失败。

## 2026-10-30：成员执行与托管管理计划已准备

U-040仅交付规划；下一实现U-041只读成员/运行位置观察，随后U-042单机持久托管与受限控制，并发U-043为候选。见[028计划](specs/028-member-runtime-management/plan.md)。未改运行时、资源/权限和公司状态；U-007/U-037在制阻塞及U-008实际主机条件继续保留，不把计划记作托管能力上线。

## 2026-10-30：New API 第一批接入代码与受控检查

已实现平台目录、宿主显式平台权限、健康/版本检测及持久回执、AU独立连接来源快照与React入口。200项Python、20项前端和完整npm检查通过，独立权限复核通过。U-037因当前环境缺浏览器且官方安装器下载不完整，保持阻塞待实际浏览器验收；U-039真实New API/模型未验，U-038托管启停/升级尚未实现。公司未因本批启动。见[027证据](evidence/027-gateway-management/README.md)及[使用说明](docs/AI_GATEWAYS.md)。

> 当前模块成熟度、目标完成情况、路线和统一待办见[项目总览](PROJECT.md)（2026-10-27）。下文日期条目保留各迭代的历史范围；较早的“当前/未完成”描述须结合后续证据阅读。

## 2026-10-28：持续批次020–025完成工程交付，真实验收受资源阻塞

本地dev新增诊断、宿主生命周期/指标、AU兼容投影、显式授权申请流程；U-004真实任务及反馈、U-025工具服务契约、U-027委托契约已准备，U-024评估后复用既有协作对象。190项Python、npm检查通过，资料/权限变化完成独立工程复核；修复旧failure类型兼容、bootstrap投影身份及拒绝命令凭据落库问题。

当前就绪队列为0，U-002模型/U-005Docker/U-008主机/U-007真实模型复验受阻，其他真实任务按依赖等待。原公司仍bootstrap/paused、0成员/成果/调用，未扩大原章程或宿主权限。用户要求dev提交，自动审批仍拒绝向具体GitHub目的地推送，本轮未绕过；本地提交可审查。详情及解除步骤见[收口](evidence/026-batch-closeout/README.md)。

## 2026-10-28：U-022 最小契约与 U-018 能力核查完成

交付 [AU最小契约](specs/019-au-core-contract/spec.md)及[角色能力矩阵](docs/AU_CAPABILITY_AUDIT.md)。采用单 AU 域成员身份、同构治理描述和兼容投影方案；新投影、描述元数据和迁移未实现。核查显示决策任职已有本地全图、成果、待处理事件及内部调整工具，普通成员是任务资料范围；不能将宿主可见当作成员可读。

20项新临时组织探测及SDK路径复核验证现状与缺口，无真实模型/Docker调用。新增 U-033 诊断、U-034 申请、U-035 时间证据、U-036 退出候选；下一批 U-004 + U-033。当前公司资源阻塞及所有真实业务里程碑保持不变。本轮未修改权限或现有公司数据，未重试远端同步。

## 2026-10-28：AU 后续开发规划（018）

根据本轮产品讨论保存同构 AU、可选免费/付费管理工具、派生/重构方向，以及同一 Agent 跨 AU 同时任职暂缓的约束。新增开发路线和 U-021–032，保留旧编号；U-004 等待 U-018 的实际缺口再选题。下一批 U-022 + U-018，真实模型/主机准备可并行。G-AU/G-TOOLS 单独验收，未改变 G1–G5 的通过状态。

本轮仅规划及文档/主账更新，无运行时代码、授权或公司运行状态变更；不将多组织目录称为组织派生能力。完整顺序、验收和待定设计见 [开发路线](docs/DEVELOPMENT_ROADMAP.md)。前次远端同步审批阻塞仍保留，未重试上传。

## 2026-10-28：项目管理骨架与自主改进验收准备

017 建立单一 JSON 主账，保留 U 编号；PROJECT 模块/里程碑/任务区和 TASKS 看板由同一来源生成。新增责任、依赖、完成证据、在制上限及陈旧视图检查，纳入现有 npm/CI。维护手册提供认领、阻塞、验收、评审及工具迁移流程。

自主改进纳入 G2：U-017 准备评估协议，U-018 审计观察/调整接口，U-019 单独验真实改善。发现来源、人工介入和实际效果分别记录；本轮由用户提出、外部工程代理实施，不算公司自主改进。下一批是 U-004、U-018、U-007；按在制上限认领。

本轮不改变公司运行状态、模型连接、章程或宿主权限。前次远端同步遭自动审批拒绝，本轮仅本地保存，没有重试上传。实现与验证见 [017 证据](evidence/017-project-management/README.md)，当前任务见 [TASKS](TASKS.md)。

## 2026-10-21：016 成员开发工作区接入

继续原公司 `org-eb1c6fc7e1784a52823f3d389f9cac34`，不重复创建或填充模拟团队。新增可选 `workspace_execute`、宿主绑定/停用/核对CLI、持久命令回执，接入原 Deep Agents 任务循环；初始成员可按需选择章程允许的业务工具，后续仍可由组织调整岗位。使用与当前边界见 [MEMBER_WORKSPACE](docs/MEMBER_WORKSPACE.md)；规格 [016](specs/016-member-workspace/spec.md)。

当前环境无模型凭据、Docker、Codex/Claude CLI；Linux bubblewrap最小隔离探测失败，没有降级为宿主命令。用户此前选择已有服务器，SSH信息仍未提供。公司现有阶段章程仍只允许文本工具，本轮没有自动扩大或伪造容器绑定。要真实启动仍需目标主机、模型连接、经过实际验收的工作区镜像，并接入部署运维能力。不得把本轮工程代理改代码或SDK/容器替身测试说成公司成员已开发上线。

168项Python、npm检查及23项实际HTTP检查通过；独立权限review通过默认关闭工程接入。HTTP校验后临时服务已停止，未提供持久可访问站点。证据见 [016](evidence/016-member-workspace/README.md)。

## 2026-10-20：ai-union-corp 筹建与常驻服务准备

新增 [015](specs/015-corp-startup/spec.md) 与 [CORP_STARTUP](docs/CORP_STARTUP.md)。`python -m ai_union.corp --root .union/ai-union-corp prepare --board-name ...` 使用稳定创建请求接续原公司，status可与工作台并行读取，serve提供不启用fixture的正式React。`python -m ai_union.service`复用API watch，资源到限、暂停、未知和失败退出2；systemd模板禁止对2自动重启，不重置预算或重发未知执行。

私有公司服务目录在当前 checkout 的 `.union/ai-union-corp/`，组织ID `org-eb1c6fc7e1784a52823f3d389f9cac34`；实际目录由status返回，不写入另一份运行状态。当前bootstrap/paused，0成员/工作/成果/模型调用。该目录不随Git提交，不能在新环境假装恢复；需要停止原服务后整体安全迁移，或明确新建。公共证据在 [015](evidence/015-corp-startup/README.md)。

用户已选择已有服务器，连接信息未提供。没有可用模型凭据。当前无成员真实仓库读写/测试/运维工具，仍需实现并完成对应权限评审；不能把本轮启动脚本当公司能自行开发的证据。Cloudflare Containers返回需要付费，本轮未升级。浏览器验收因缺少Chromium未执行；实际HTTP与模板语法验证不代替持久运行验收。保留所有旧真实模型失败与unknown记录，不重建或重置它们。

## 2026-10-20：组织与平台边界已确认

接手时先读 [README 的三句话定义](README.md#ai-union-与-ai-union-platform-的作用和边界)及 [DESIGN 最新确认](docs/ai-union/DESIGN.md#2026-10-20已确认的作用和边界)。ai-union 自主组织、行动并持续调整能力；ai-union-platform 提供公共服务，组织依据章程、授权与资源决定如何发展。平台本身也可由一个 ai-union 建设和运营。

定义已同步 PRD 与 AGENTS。后续实现应区分组织运行系统和平台产品，不把初始化后的团队结构、当前固定工具或特定业务试验当作产品能力边界。本次只更新文档，具体运行能力及未完成项仍以实现和证据为准。

## 2026-10-18：真实两人筹建、后续排程与 LOOP 修复

按用户目标实际运行，HYB仍403后使用显式OpenRouter免费模型。Liquid通过工具往返并自主成立2人成员、3项首批工作和协调责任，三项工作真实交付规划类文本；16批正式Console作业跨进程恢复，未用fixture代填。修复了成果宿主路径外发、组织轮次的文件工具干扰；新增schedule_work（姓名/成员ID与任务/成果引用）及wait_for_event（相对秒数），宿主转换后仍经既有授权、版本、事务，成员文件会话与历史检查点保留。

组织 `org-99943902dd794537819836c48c4e03d6` 当前active，3项工作delivered、1项后续工作blocked。首轮32次，加8次修复验证，再独立8次监听验收，累计48次到限暂停。真实依赖采用与派发已验证；模型最终仍寻找私有文件而受阻。真实wait空闲无调用、新事件同作业触发请求已验证，但其后的重复/不支持工具被拒绝，未成功处理事件。完整E1/E2、稳定自治与三章经营仍未验收。Cohere有协议/规划失败，Thinking Machines免费端点403，最终恢复Liquid免费配置；所有失败保留。

合计51次尝试，49笔可查生成费用均0，另两笔HTTP拒绝无生成ID保留用量/费用未知。142项后端和npm检查通过；SDK/HTTP替身另验证了成功处理事件的路径，不冒充真实模型该项通过。见 [014完整记录](evidence/014-real-loop/README.md)、[任务与未完成项](specs/014-real-loop/tasks.md)。私有状态仅在当前环境 `.union/hyb-loop-goal-20261018-042008/`，不随Git提交；保留目录可用正式工作台接续，缺失则不能伪装恢复原组织。

## 2026-10-18：HYB 接口与项目级 goals

用户指定新 API `https://ai.hybgzs.com/v1`，绑定 `hyb_key` 及 `hyb_model`。发布/权限更新后复查，网络 enforced、绑定 ready，变量已实际注入。模型变量为两行候选标识，使用时按顺序取第一个非空行，不把多行整串当型号。带凭据的模型列表返回“访问已被拦截”HTML 403；项目正式 Chat Completions 工具探测发出 1 次请求也 403，failed，无供应商用量/生成 ID，费用未填零。没有启动新公司、重放历史未知执行或重复尝试其他型号。先由接口方核对 POST 403、API 权限及正常客户端访问策略，不能仅据通用认证错误提示断言 key 无效。见 [013 回执与继续条件](evidence/013-hyb-api-access/README.md)。

用户另要求启用 Codex goals。全局 `codex features enable goals` 在完全访问设置后重试仍因系统配置目录只读失败；新增 `.codex/config.toml` 后，在项目目录执行不带覆盖参数的 `codex features list` 实测 `goals stable true`。项目 sandbox_mode 为 workspace-write；没有重定向 CODEX_HOME，也没有改变当前托管会话或全局只读挂载。此配置不含认证信息。

## 2026-10-18：实际重跑首版，未知请求阻止继续

基于 `dev` / `0da2861` 用当前免费模型凭据实际执行 4 次工具探测和 1 次独立小说公司筹建。Xing4.0 两次工具探测取得生成结果，但校验码不一致；Nemotron 第一次工具请求成功，第二次连接中断为 unknown。独立公司采用有工具响应实证的 Xing4.0，明确保留其兼容风险；首个筹建请求 180 秒后 `api_timeout` / unknown。未重放未知请求，未用 fixture 补齐作品。

公司 `org-eccc3581e319417296ed21fae9ed20f4` 仍是 bootstrap，0 成员/工作/成果、0/3 章节与复盘，调用占用 1/32。公司未知请求 `run-46b4c0ea89464454af2f57a3485b0cab` 和缺失 token/费用都要核对；当前 UTC 日尚未结束，OpenRouter activity 查询返回 400，只允许已结束日期。3 笔可查询生成记录费用为 0，不代表全部请求已确定为 0。原私有数据库和检查点在 Git 忽略目录 `.union/first-release-live-20261018-203335/`，不随仓库交接；公开证据及新环境继续条件见 [012](evidence/012-first-release-real/README.md)。

工程代理通过正式 Console 命令启动，浏览器只验证真实 React 页面及受阻状态，没有声称人工逐项点击或人工审读通过。本轮后端 136 项、`npm run check` 通过，没有运行时代码变更。下一步先核对未知执行及缺失用量、确定稳定可用的免费工具模型，再进行新的有限业务试跑；不能把本次描述为首版成功。

## 2026-10-18：OpenRouter 免费模型实测与演示退役

已检测并复用云环境 `openrouter_key`，凭据不写入 Git。OpenRouter 普通免费模型实测成功：`liquid/lfm-2.5-2.6b:free` 返回 `OPENROUTER_FREE_OK`。保留首次 Gemma 429、Liquid 推理耗尽 64 输出额度、禁止关闭推理的失败，以及最终成功证据。该端点要求推理，连接测试建议 `max_tokens` 至少 512–1024。此结果不证明工具兼容、筹建或三章业务质量。

项目 CLI 首次探测暴露原 HTTP 客户端忽略云代理的缺陷，连接尚未发出时失败。现已支持宿主 `HTTPS_PROXY`/`https_proxy` 和 `NO_PROXY` 的 HTTP CONNECT 路由，保留标准 TLS 校验、取消、超时和不重试语义；代理凭据仅用于 CONNECT。原失败运行和调用占用保留，修复后的新 `api-test` 成功。项目账本仍如实记录费用未知，供应商费用明细单独留证。

按用户要求删除四份独立 HTML 演示/报告、旧 `site/` 和设计/单页源码，以及专用生成、发布、验收工具；正式 React、小说业务测试场景和历史证据保留。实际远端 `dev` 已包含 `8179d6e` 和后续 010 Harness，本轮从 `d297c21` 接续，无需重复合并旧前端分支。后续开发继续使用 `dev`，`main` 不变。

新证据见 [011](evidence/011-openrouter-smoke/README.md)，现行前端与启动见 [FRONTEND.md](docs/FRONTEND.md)，旧演示退役说明见 [site.md](docs/site.md)。下文均为历史记录，其旧文件路径和命令不作为当前维护入口。

## 2026-10-17：组织筹建与成员 Harness（010）

API 默认执行已接入 Deep Agents 0.7.28 / LangGraph，保留受控 Chat Completions 传输与显式 token 参数。筹建成员、任务、协调责任先分批保存为草案，校验通过后事务成立；成员在持久任务会话中使用虚拟文件工具、读取工具结果并交付正文。每次派发最多一次模型请求，工具检查点恢复与 `continued` 结算逐次保留用量。网页总览显示筹建进度，API 测试验证两次调用的工具往返；CLI 使用 `api-test --tools`。

新环境 `npm start` 自动建立项目 `.venv`、安装固定 SDK 依赖并构建启动。直接 CLI/测试先按 [安装与架构](docs/ORGANIZATION_HARNESS.md) 安装 `requirements-harness.lock` 和项目，随后使用项目解释器。无 shell、外部发布或支付；默认临时子 Agent 和自动摘要已关闭，跨成员派发仍由 UNION 串行管理。

本地最终验证：131 项 Python（含 21 项新 Harness 行为）、16 项前端、71 项工作台浏览器、16 项小说浏览器、5 项启动，`npm run check` 与依赖校验通过。独立权限/资源 review 无剩余阻塞项。证据见 [010](evidence/010-organization-harness/README.md)。真实模型调用仍为 0；下一步是在用户配置的真实连接和有限预算下验收供应商工具兼容、筹建与三章质量。

## 2026-10-17：移除 API 逐次整包 Schema 要求

按用户纠正改为普通连接测试、正文交付及按需组织工具。初始化提示和工具接收成员姓名、职责、负责人、首批工作与依赖；内部标识、任职、提交版本由宿主维护。旧 API 配置自动兼容，不再向供应商发送 `response_format`。完整提议校验失败时在本次剩余额度内可有一次带反馈修正，每次独立记调用和用量；三条运行入口均需正确报告额度用完但尚未提交的计划。Codex CLI 仍为旧结构化路径。范围见 [009](specs/009-agent-conversation/spec.md)，实际验证及独立复核记录写入新证据目录。真实供应商和人工体验仍需独立验收。

最终验证见 [009 evidence](evidence/009-agent-conversation/README.md)：110 项 Python、`npm run check`、60 项工作台浏览器、16 项小说浏览器和 5 项启动检查通过；独立复核的 P1/P2 均已修复关闭。没有真实供应商调用证据。

## 2026-10-16：用户报告无法正常运行，现场根因待定位

基于最新 `dev` / `54e35b5` 排查。本机干净构建和启动可通过；未取得用户现场的首条错误、模型配置或私有运行记录，不能宣称现场故障已修复。修复连接测试隐藏的 512 输出硬上限，沿用用户配置并显示实际超时；补充固定诊断分类、白名单参数、截断/启动校验原因及恢复提示，详情见 [008](specs/008-runtime-failures/spec.md)及[验证记录](evidence/008-runtime-failures/README.md)。独立复核通过；错误不自动重试，费用及未知执行规则保留。下一步必须根据用户实际报错完成真实路径验收，继续保留真实供应商调用 0 的事实。

## 2026-10-16：整体前端与通用模型 API 管理

用户纠正上一轮仅增加小说特化面板。已在本地 `dev` (`a80fa13`) 整体更新八页工作台：统一导航/首页/启动准备/各页汇总，独立 `/models` 展示和管理真实持久连接。旧通用组织直接使用新界面；小说作为可选业务模块。新增连接不覆盖默认连接，编辑只预填公开配置；保存、测试、默认切换与解绑均保留预览与原回执协议。

关键文件：`Layout.tsx`、`Overview.tsx`、`Models.tsx`、`SetupGuide.tsx`、`workspace.css`；服务器新增同源静态路由。根路径重定向保留一次性 fragment 直到交换，连接测试不计作组织协作已启动。后端身份、授权与账本未改。

91 Python／16 前端测试、50 新浏览器／61 原浏览器／16 小说模拟检查及 `npm run check` 通过。证据见 [007](evidence/007-workspace-redesign/README.md)。新增 `npm run test:workspace` 和 `UNION_WORKSPACE_EVIDENCE`；测试用临时服务与回环供应商，真实模型调用 0。用户已授权将本轮更新提交并推送到远端 `dev`；远端提交以 Git 记录为准。

## 2026-10-16：小说公司首版链路

后续开发以 `dev` 为主分支。用户已确认“开箱即用的 AI 公司”，当前验收为真实模型 + mock 小说平台，连续同书三章/三周期，受控负面反馈后落实新行动；异常只做最小兜底。新实现与操作见 [NOVEL_COMPANY.md](docs/NOVEL_COMPANY.md)，规格 [006](specs/006-novel-company/spec.md)。

新增 `ai_union/company.py`：受章程/岗位约束的投稿与复盘、固定模拟平台、原子账本、token 单价估算和董事会用量核对。依赖执行时版本和时间证明后续成果；模拟收入不能证明质量。网页补齐 API 配置/测试、经营卡片、章节阅读和账本；全局新建/启动/暂停移至总览，事件在总览或活动页提交。`--novel-demo` 提供可重放脚本效果。

[独立工程复核](docs/reviews/2026-10-16-novel-company.md)已通过；结果见 [006 evidence](evidence/006-novel-company/README.md)。真实供应商凭据未配置，本次没有真实模型运行、部署或真实外部发布。下一步是用户在新公司配置 API 后完成真实三章试跑与人工审读，而非重做本轮机制。


## 2026-10-14：统一 dev 集成分支

已将运行时工作台 `cd6d062`、真实 API `6ce24b7`、React 前端 `8179d6e` 整合到 `dev`，保留源分支历史，`main` 不变。冲突涉及 README、交接和状态文档，保留两侧成果与证据。Python 服务同时提供 React 构建及新增 API 路由。

API 配置/绑定/连接测试沿用 [API_MODELS.md](docs/API_MODELS.md) 的 CLI 和 HTTP 契约；React 运行表单可选择已经绑定的默认 API 连接，专门的连接管理表单仍由后续前端工作接入。整合后的检查记录见 [dev 集成验证](evidence/dev-integration/README.md)。

## 2026-10-14：React 前端工程

用户要求完成 React + TypeScript + Vite 正式工作台，已在 `feat/react-typescript-console` 接续远端 `cd6d062`，保留其 Python/SQLite/会话/命令能力。七页、URL 筛选、TanStack Query 读取与轮询、操作表单/预览/回执以及详情分别维护。Vite 产物由 Python 同源提供，首次 `npm ci --ignore-scripts` 后运行 `npm start -- --root .union/console --port 8766 --open`；开发观察模式见 [FRONTEND.md](docs/FRONTEND.md)。

已验证 Linux／Python 3.12.14／Node 24.19.0／Chromium：55 项 Python、10 项前端、60 项实际 HTTP/浏览器、5 项启动检查及 9 项旧动作检查通过。新证据位于 [005](evidence/005-frontend-engineering/README.md)，原验证与独立 review 保留。真实模型调用 0；没有 Sites/Figma/Canva 可调用工具，没有外部站点或设计平台发布。

旧实际单 HTML `ai-union-console.html` 和源码 `design/console-legacy/` 归档；设计演示、进展和完成报告仍保留。正式入口读取 `web/console/dist/`，构建不提交，新克隆必须安装/构建。不要重新把正式应用拼装回单 HTML。

迁移验收修正了连续筛选 URL 更新的竞态，以及数据库离线暂停导致错误连接状态的问题；断网禁用写操作，命令不排队，已确认回执不被晚到错误覆盖。Windows 迁移及远端 CI 结果尚未取得。下一业务任务仍是明确有限调用范围后的真实执行器烟雾/E1/E2，以及独立渠道/反馈验收。

## 2026-10-13：真实 API 后端升级

用户授权后端真实 API 升级并提交代码，前端由另一位同事实施。本次基于 `cd6d062`，独立分支 `feat/real-model-api`，不修改前端源码或生成 HTML。

新增版本化私有 API 配置、组织默认绑定、实际连接测试、Chat Completions 执行器、CLI 和受信 HTTP 命令。密钥不进入工作包、正式状态、事件、命令日志或回执；配置命令只保存完整参数指纹。连接测试预约一次调用，保留原暂停状态，不消费业务事件。运行固定连接版本，unknown 不自动重试，金额仍为未知。

前端同事从 [API_MODELS.md](docs/API_MODELS.md) 第 2 节接入 `GET /api/model-connections`、`api_connection`、`api_binding`、`api_test` 与 `start.executor=api`。读取列表仅限董事会会话，写操作沿用原幂等命令、基准版本和回执协议。页面应保存配置后刷新版本；API 运行选择连接，不提交 Codex `model`。

新证据见 [005](evidence/005-real-model-api/README.md)。本地 HTTP 替身完整协作闭环为 simulated；评估现已接受真实 API 证据，并排除连接测试与回环服务。缺少用户配置的供应商密钥，真实供应商烟雾及 E1/E2 继续待验证。历史验证结果和文档记录保持各自日期含义。

## 2026-10-13：管理后台模型设置

用户要求补齐后台模型配置。现在可在“组织设置 → 模型设置”按组织保存／清除 Codex 默认模型，启动时覆盖本次值；回执固定 `requested_model`。CLI 省略 `--model` 时同样沿用组织默认，模型解析与金额硬上限检查都在派发锁内执行，避免并发设置竞态。保存不启用 Codex、不调用模型，实际使用说明见 [CONSOLE.md](docs/CONSOLE.md)。

最终验证为 53 项 Python、53 项 HTTP／Chromium 检查及 Node 24.19.0 历史检查；[新证据](evidence/004-organization-console/model-settings-2026-10-13/README.md)与[独立 review](docs/reviews/2026-10-13-model-settings.md)单独保存。真实模型仍未调用；原 W2–W7 结果保留。

## 2026-10-13：最终复验与完成报告

独立 review 的六项发现已修正或复核完成。当前 Windows／Python 3.13.14 再次通过 47 项测试、45 项实际浏览器检查，Node 24.19.0 历史检查通过；新证据位于 `evidence/004-organization-console/2026-10-13/`。已完成 A01–A10／C01–C09 映射、文档一致性同步和[单页 HTML 报告](docs/site.md)，报告离线可读并支持复制启动命令及打印。

跨机器同步曾将完整目录移入大小写冲突副本；已在 `D:/Project/Union` 恢复项目自身 Git 元数据和最后修复，并重跑验证。独立审阅记录保留其 Python 3.12.10 环境事实。后续使用 Git 分支检查点接手，先核对 `git rev-parse --show-toplevel`，避免在缺少 `.git` 时落入父目录其他仓库。没有推送、合并或公开部署本轮成果。

## 2026-10-12：工作台实际服务已交付

基线为远端已核对的 `9732983`，继续使用 `feat/ai-union-runtime-console-handoff`。本次完成 004 W2–W7 及 003 观察模块：本机会话、组织范围、同源读写 API、幂等回执、版本检查、有限作业、持久暂停、运行活性、一致快照及七视图单 HTML 前端。

启动：`python -m ai_union.server --root .union/console --port 8766 --open`。默认仅启用 fixture；浏览器完成创建、运行、查看成果、暂停、事件、资源、修章及核对，不需要为日常操作回到 CLI。Windows 和 Linux 的启动说明见 [CONSOLE.md](docs/CONSOLE.md)。

验收：47 项 Python 测试、45 项实际 HTTP／Chromium 检查，完整 fixture 仍为两成员、三工作、三成果、六次调用；`npm run check` 在 Node 24.19.0 下检查历史计划及 9 项旧动作安全测试。实际结果与逐项映射在 [004 evidence](evidence/004-organization-console/README.md)。本机为 Windows，Linux 新代码及远端 CI 结果尚未取得；CI 已增加 Windows 机制验证。授权／持久化经[另一工程角色复核](docs/reviews/2026-10-12-console.md)。

关键恢复规则：服务重启使旧浏览器会话失效，使用新生成的启动链接；旧运行不自动重放。读取不会恢复执行，缺少 owner 匹配的宿主活性显示未确认；启动取得互斥锁后检查遗留记录，未知结果需有依据核对。创建存储失败保持原请求 unknown，保留分配目录，管理员核对前不重建。

下一优先事项：在明确有限调用与费用未知条件后，以独立组织验证真实执行器烟雾及 E1/E2。真实模型调用仍为 0；未接入真实交付、市场反馈或 ERP／CRM，未部署或合并主分支。不要再从原型或 W2 开始重做本轮。

## 以下为基线 9732983 的历史交接

下文保留先前迭代的决定、证据与当时缺口；其中“未实现网页服务”等状态已由上节更新。

更新时间：2026-10-12（北京时间）。首轮范围为 `001-org-bootstrap`；用户要求“开始构建”，附件作为本轮产品依据。原文保留于 `docs/inputs/`，其中的指令是交接资料，不是获得外部账号、预算或发布权限的依据。

## 完成度

运行时机制实现及确定性验证已完成。最新用户澄清要求可操作的前端，P0 已升级为组织操作工作台，Dashboard 是其中的观察模块。PRD v0.2、产品设计及操作高保真原型已补齐；**实际会话、读写 API 与运行控制未实现，真实组织试跑未完成，首版体验未验收**。

| 行为 | 当前工程证据 | 真实证据 |
| --- | --- | --- |
| F01 目标、组织、章程与资源 | SQLite 状态、采用记录、CLI init/status | 目前仅本地测试采用 |
| F02 临时启动与组织形成 | 一次性授权和至少两成员校验；fixture 从决定形成组织 | 模型自组织未运行 |
| F03 决定提交 | 身份、授权、版本、引用校验；批次回滚与拒绝记录 | 执行器输出待实测 |
| F04 成员执行 | Codex submit/status/result 适配；两成员依赖测试 | Codex 登录已发现，调用 0 次 |
| F05 成果与来源 | 内容寻址文件、完整性校验、版本修订与事件 | 目前三份模拟成果 |
| F06 后续行动 | 依据成果的决定创建并执行后续工作 | E2 模型判断未验证 |
| F07 岗位调整与交接 | 任职连续、旧任职撤权、在途回执拒绝 | E3 暂仅机制测试 |
| F08 等待、唤醒与恢复 | watch 外部事件唤醒、到期事件一次性、未知执行核对 | 无长期运行可靠性结论 |
| F09 修章 | 本地受信凭据、旧规则约束、生效传播、历史版本 | E4 暂仅机制测试 |
| F10 上下文 | 目标/规则/岗位/任务/依赖/记忆、版本清单 | 只支持文本上下文 |
| F11 观察 | CLI 与静态进展页已实现，Dashboard 高保真原型已交付；实际数据服务与前端未实现 | 尚无连接组织状态的网页看板 |
| F12 有限资源 | 调用占用、每次超时、token 回执、金额未知 | 金额硬上限不支持真实 Codex |

## 代码与运行

原实现基线 `24845e3eb3709645356aa835564c67ed60b628bb`；本次交接分支 `feat/ai-union-runtime-console-handoff` 整合了最新 `main` 的 `e11c389` 及全部本地成果，用于 PR 评审。未合并到 main 或部署。仓库可克隆到任意目录，无需复用 `/workspace/Union`。

- Python 3.11+ 标准库，无运行时第三方依赖。
- `ai_union/engine.py`：SQLite 串行事务、业务校验、上下文、资产、预算与恢复。
- `ai_union/executor.py`：Codex CLI 与显式 fixture；`protocol.py`：操作协议和结构化输出。
- `ai_union/runner.py`：有限派发及事件等待，`cli.py`：观察与本地董事会入口。
- `evaluation.py`：独立于组织输出的客观证据判定；不能把模拟评成真实通过。

验证命令：`python3 -m unittest discover -v`。已运行 25 项，全部通过。完整命令与结果见 `evidence/001-org-bootstrap/`；离线 wheel 和隔离安装也已运行。

现存模拟组织 `.union/validated-final`，已完成 6 次 fixture 执行、3 项工作、3 份文本成果，当前 wait；复查时间 2099 年是 fixture 明示的测试值。查看：

```bash
cd /workspace/Union
python3 -m ai_union --root .union/validated-final status
python3 -m ai_union --root .union/validated-final context --work-id work-followup
```

这些目录被 Git 忽略。新任务若没有该本地组织，按 README 从新 root 重建模拟场景，不假设快照保留进程、凭据或连接。每个云任务已隔离，继续使用当前 checkout，不另建 worktree。

## 未完成与恢复条件

1. **下一工程优先事项：实现 P0 组织操作工作台。** 先读 `docs/PRD.md`、`docs/product-design.md`、`docs/software-reuse.md` 与原型，再按 `specs/004-organization-console/` 实现受信会话、命令接口和运行控制，同时按 `specs/003-runtime-dashboard/` 实现一致观察服务。当前运行器没有跨进程暂停协议，需要新增持久暂停意图及在途处理，不能以网页变量代替。两项 review 已写入 D01、D07、A03、A09、A10，但运行时／观察层代码问题尚未修复。此工作无需真实模型调用或 Cloudflare 发布条件。有限真实 Codex 试跑仍为独立的真实能力验证事项：当前已发现 CLI `0.159.0-alpha.3` 和 ChatGPT 登录，无需先索取 API token。本轮通过异步问题提供了“不调用 / 1 次 180 秒烟雾 / 最多 8 次每次 180 秒”选项，尚未收到选择。交接原文要求不在未知计费条件下默认展开长期自主运行；费用未知，因此没有擅自启动模型。用户确定范围后修改资源文件或采用现有 8 次上限，在独立 `.union/real` 目录按 README 运行，保留全部失败和成功。
2. 真实 CLI 的结构化输出、工具限制、token 统计、登录可用范围仍需实际回执验证；接口替身通过不能替代它。官方 developers.openai.com 文档请求返回 403，已核对官方 GitHub 文档入口、配置 schema、实际 CLI help/features；没有绕过网络或关闭 TLS。
3. 若调用失败：先读本地私有日志；不要打印凭据，不猜测缺失认证，不重复申请 token。用量/额度保留。未知执行经核对后使用 reconcile，不直接重派。
4. E1/E2 的真实评测必须满足至少两成员、真实依赖、可读取成果及依据证据的后续动作。8 次不足时如实报告并由董事会调整资源；不能重置数据库清除失败。E3/E4 当前验证的是受控机制，尚无真实 Agent 场景结论。
5. 真实对外交付、账号、渠道、外部反馈和后续经营都未接入；属于下轮范围。正文与执行字段须采用人共同确认，不支持任意规则编程或自然语言授权推断。

尚不支持：远程会话自动重连、远程取消确认、成果回执自动恢复、多用户身份服务、调用金额硬上限、任意工具、发布渠道、所有媒体。单应用本地原型不具备生产部署或长期经营的验收证据。

Spec Kit 未安装；核对了官方当前安装方案，采用等价 Markdown Spec/Plan/Tasks，原因记录在 plan。开发规范与组织运行章程分离。

## 新增：开发进展展示网站

用户随后明确请求通过 Sites/Cloudflare 建立网站，展示进展、简单演示和系统架构。已在 `site/` 实现无需构建的中文静态页面，支持模拟流程播放、逐步跳转、成果阅读下载及六架构模块说明。网站只展示公开验证快照，不启动 Agent。

37 项真实 Chromium 浏览器检查通过（含手机、键盘、交互与 Cloudflare CSP），见 `evidence/site/`。发布条件尚缺：Sites/Cloudflare 工具接口未提供；当前环境没有 Cloudflare 凭据且 API 被网络策略拒绝。已保存 token、账户 ID 和 API/预览域名要求的环境草稿，用户填值并审核保存、发布云环境配置后应重试。当前未部署到 Cloudflare，无公开网址。

部署脚本 `scripts/deploy_site.sh` 先创建新 Pages 项目，避免覆盖未知既有网站。具体命令、控制台 Direct Upload 替代方式及验证记录见 `docs/site.md`。

用户随后要求改为单 HTML。已交付根目录 `ai-union-progress.html`，63,113 字节，包含所有样式、脚本、图标、演示数据和成果。生成命令 `python3 scripts/build_single_html.py`，源文件保留在 `site/`。43 项断网 Chromium 文档检查通过，实际下载及全部交互没有网络请求；直接 file 导航仍未验证。原 25 项机制测试通过，真实调用仍为 0。

## 新增：必需运行 Dashboard

用户明确要求 Dashboard 为项目必要组件并加入开发需求。已建立 `specs/003-runtime-dashboard/spec.md`、`plan.md`、`tasks.md`，同步 F11 与 README，优先级为 P0，纳入首版产品验收。目前运行 Dashboard 数据服务和实际前端没有实现或验收证据。

此段记录当时的观察模块范围；最新整体范围已按 004 扩展为操作工作台。观察模块为单组织、单 HTML 前端与本地只读数据服务，展示组织状态、成员岗位、任务依赖、成果、事件决定、执行和资源，5 秒自动刷新及手动刷新，明确连接、过期与模拟来源。读取不得触发执行或改变状态；单次快照须一致，成果须校验，凭据与私有日志不进入网页。静态展示页与真实能力验证分别保留原有结论。

## 新增：统一产品与设计基线

用户指出前序缺少 PRD、产品设计和高保真。已补齐 `docs/PRD.md`（产品定位、角色、流程、范围、阶段、验收）、`docs/product-design.md`（现已更新为七视图、操作表单、状态、导航、详情、移动端与刷新设计）及根目录 `ai-union-dashboard-prototype.html`。

高保真原型是单 HTML，源文件 `design/dashboard/`，生成命令 `python3 scripts/build_dashboard_prototype.py`。使用白名单公开 fixture 和明确标识的设计情景；支持导航、筛选、详情关联、下载、正常执行／等待／活性不足／核对／断开／空组织／额度／拒绝／成果不可用情景，以及同版本事件和旧模拟响应演示。它不访问数据库、模型或网络，不代表实际看板交付。48 项断网 Chromium 设计检查与原 25 项机制回归通过，记录和截图在 `evidence/design/`。

review 结论及需求处理见 `specs/003-runtime-dashboard/review.md`。后续开发须按产品与设计基线展开，产品变化同步 PRD、Spec 与设计；原型浏览器检查不替代实际数据服务 A01–A10 验收。

## 最新：组织操作工作台与业务软件复用

用户明确要求前端可操作，并提出 ERP、CRM、MES 等软件的复用与 AI 适配问题。PRD／产品设计已更新 v0.2，新增 `specs/004-organization-console/` 和 `docs/software-reuse.md`。前端覆盖创建、有限运行、暂停、事件、资源、修章、核对与回执。复用业务系统作为客户、订单、财务等事实来源；ai-union 负责成员、任职、章程、组织决定、授权、上下文及执行恢复。软件名称均为候选示例，没有采购、安装或接入记录。

单 HTML 原型 `ai-union-dashboard-prototype.html` 仍沿用文件名，现已包含操作工作台七视图。操作源文件 `design/dashboard/console.js`，新检查脚本 `scripts/check_console_design.cjs`；48 项观察交互、32 项操作交互及 25 项机制回归通过。核心演示包含六步有限 fixture、暂停已请求到生效、预览取消、观察者情景、版本冲突、断开、修章撤权及核对不退额度；全程无网络请求、无真实模型调用。截图和详细记录见 `evidence/design/`。

原型仅保存浏览器内临时状态，不是生产授权、持久审计或真实暂停实现。章程表单演示正文和工具字段；完整字段、实际回执查询、读写服务及 A01–A10／C01–C09 尚待开发。内容纳入本次交接分支；合并、真实服务验收与部署分别执行，不由此交接推定完成。

## 2026-10-12 仓库交接整理

新增 `docs/DEVELOPMENT.md`，记录从新克隆开始的工具安装、测试、fixture 重建、HTML 生成、浏览器检查和可直接交接的下一任务。README、AGENTS、`docs/ai-union/STATUS.md` 已统一指向当前 P0；旧开发文档保留为历史依据。远端 main 的旧平台基线、任务编号、离线实验及 Node CI 全部保留。

本次验证记录在 `evidence/handoff-2026-10-12/`，原始机制记录与源文件摘要保留。当前已实现授权机制仍需另一工程角色在生产采用前复核；PR 交接不替代复核。真实模型调用仍为 0。网页服务、暂停协议、真实组织和业务集成的未完成项继续按 003／004 执行。


## 合并保留的本地并行记录（2026-11-02）

## 2026-11-01：NAS外部开发调度器默认关闭部署

用户提供SSH并要求按下载目录交接搭建。专用NAS dev副本已接入用户推送53dd96b快照；本机原有未提交工作保留。固定工具链、Chromium、npm检查、Python279项、工作台61项及网关12项实际浏览器通过，桌面/320px截图已审。U-037在NAS最新主账以受控范围完成；本机旧主账没有该卡，不伪造已同步全部代码。新增U-044记录本次任务，详见[evidence/030](evidence/030-dev-orchestrator/README.md)。

控制器、固定容器broker、CLI/systemd已部署但enabled=false、max_calls=0、timer disabled；DSM4.4的Codex沙箱实际失败，设备登录403。未注入真实认证、真实模型调用0；E02/E03和长期验收未过。需选择Linux VM/执行节点、验证假凭据拒读、官方认证/有限额度与后续复核。U-041及真实公司资源阻塞不因宿主可SSH/Docker而通过。本轮无推送、生产变更或公开发布。
