# 037：A06实际SDK会话版本与交接验证

2026-10-31 14:35开始，18:36恢复并重新核对现场；基线dev@6ed3470。GPT-6 Astra实际完成规划→GPT-6.1 Sol实施→独立Astra首次额度中断、18时恢复完成最终子集复核。均为外部工程角色，不是AU成员/VPS常驻开发链；工程模型解析型号、token和费用未返回，保持未知。

## 当前事实与完成声明

dev起始领先origin/dev 13提交，tracked干净；用户docs/research/未跟踪资料保留。18:37重新ls-remote：dev仍b39c06c76e3b83a6d5413b45f58a9c736e2f15bc，main仍e11c389366814060ea4475a359c9b62036ccd176。combined-status的statuses=[]，workflow_runs=[]；后者只覆盖PR触发首批结果，不能证明所有Actions不存在或通过。本地变更未上传，无本地新SHA的远端CI。CI定义仍有Ubuntu/Windows npm与机制检查及Linux浏览器作业，定义不是运行证据。

本轮重读当前branch/status/log、PROJECT/TASKS、management主账/规则、028规格及测试/CI证据。43任务、16done仍为10文档/6受控，没有real/sustained完成或accepted结果里程碑；逐项内容/代码映射按[031审计](../031-member-work-state/completion-audit.md)与当前代码/回归复核，[completion-audit.json](completion-audit.json)重新核对各项范围/产物及哈希。文件存在或哈希不能证明历史真实业务，更不计算16/43的产品完成率。

[14:37诊断](company-status.json)及[18:38本地原公司只读复查](company-status-final.json)仍为原身份bootstrap/paused、成员/工作/成果/模型调用均0，模型/开发工作区未配置、无Docker CLI、费用unknown。未核查远端生产；Chromium缓存和常用浏览器命令不可用。公司真实筹建、交付及持续运营未验。

## 规划与变更

[Astra规划](plan.md)选择036留下的A06实际SDK缺口。[新增七项测试](../../tests/test_session_revisions.py)通过实际Engine/Runner/DeepAgents/LangGraph/SQLiteSaver与回环HTTP，模型响应和容器为明确替身。SDK先实际执行workspace工具形成非空命令回执（只run_container替身），再write_file生成可续接旧草稿；不手填session/task_key/checkpoint。

三类正向验证连接revision、工作区revision、正式交接后产生新session/key，新请求/SDK历史排除旧私有草稿，旧session/run/用量/命令回执/旧thread检查点和writes保留；同版本新Engine/Executor仍续接同thread历史作对照。负向验证新factory遇禁用连接零消耗、禁用workspace不提供工具且伪造调用不执行容器，以及工具已提供后正式岗位撤权仍在执行阶段拒绝、保留已收到用量。详见[矩阵与边界](matrix.md)。

没有发现生产缺陷，**生产代码零改动**；本轮交付测试与验收/交接记录。平台不增加业务岗位、组织流程、权限、托管控制或预算。本轮SDK/替身验证不是公司真实开发交付。

## 执行与测试

| 检查 | 结果与证据 |
| --- | --- |
| 首轮七项 | 7失败：误将SDK最新delta checkpoint当完整草稿；[原始日志](focused-first.log) |
| 第二轮 | 5通过/2失败：误期待单步correction，现有Runner实际收口为blocked；[日志](focused-second.log) |
| 第三轮 | 6通过/1错误：误期待feedback必有值；后改查实际executor.tool_errors的岗位撤权原因；[日志](focused-third.log) |
| 纠正上述测试假设后 | 7通过，7.954秒；[日志](focused-before-extra-assertions.log) |
| 最终版Python全量 | 强化全部session表/请求/预算断言后252项通过，82.797秒；[日志](python-tests.log) |
| 独立Astra最终 | 54项通过，36.132秒；[复核](review.md)、[日志](independent-review-final.log)；早期独立2失败另保留 |
| npm完整检查 | 退出0：管理8项、历史82任务/181依赖、动作安全9项、前端31项、类型与构建通过；[日志](npm-check.log) |
| 实际浏览器 | Chromium仍不可用；没有运行A11或用组件检查替代 |

上述先失败后通过是**测试构造/断言纠正**，不能称生产bug红绿修复。SDK根记录用get_tuple确认存在，完整历史用list读取；新会话写同库正常，只比较旧thread记录而非整个SQLite文件。当前同版本用例证明历史续接，不额外声称已直接断言read_file返回的ToolMessage正文。Python使用.union/validation-20261031-0940/bin/python，本轮仍可执行，未重装依赖。

## 阻塞与下一小时

U-041保持blocked、completion=null，在制3/3、就绪0、阻塞7、done16未提升。A06上述受控子集独立通过，不等于A06全部或真实恢复通过。旧Executor连接热撤销、在途配置/全部授权组合、WAL TOCTOU、跨库非原子、实际Chromium和完整观察验收仍待完成。真实模型/调用授权、Docker/镜像、持久VPS/SSH、真实New API资源阻塞保持；U-042未实现。

下一小时首项：Astra核对A03现有activity/owner/receipt机制，冻结直接心跳时间过期、旧实例迟到回执的最小行为用例，由Sol执行；不把owner退出当过期，有失败才最小修复，不先扩大托管。本轮未推送、发布、付费、合并main或改生产。
