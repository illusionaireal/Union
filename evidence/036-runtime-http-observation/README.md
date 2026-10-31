# 036：运行观察的实际 HTTP 验证

2026-10-31 13:31开始检查（UTC+8；05:31 UTC），基线dev@fe20291。实际GPT-6 Astra规划→GPT-6.1 Sol实施→独立GPT-6 Astra受控子集复核。均为外部工程角色，不是AU成员开发、VPS常驻链或公司运营；工程模型解析型号、token与费用未返回，保持未知。

## 实际进度与完成声明

开始dev领先origin/dev 12提交，tracked干净，仅用户docs/research/未跟踪资料；保留未动。本轮读取当前分支/status/最新提交、PROJECT/TASKS、management主账/规则、028规格、工程与CI证据，见[检查摘要](inspection.json)。远端只读核对dev仍b39c06c76e3b83a6d5413b45f58a9c736e2f15bc，main仍e11c389366814060ea4475a359c9b62036ccd176。combined-status返回statuses=[]，workflow_runs=[]；后者仅覆盖PR触发首批结果，不能据此断言全部Actions没有或通过。本地变更未上传，无本地新SHA远端CI。

43任务、16项done仍为10文档/6受控；无real/sustained完成或accepted里程碑。逐项内容/代码映射复核沿用[031逐项审计](../031-member-work-state/completion-audit.md)，本轮重新检查当前完成范围、产物存在与哈希，见[completion-audit.json](completion-audit.json)，结合当前回归；文件与哈希不证明历史业务真实或产品完成百分比。

[13:42本地原公司只读诊断](company-status.json)：原身份bootstrap/paused，成员/工作/成果/模型调用均0，未配置模型/开发工作区，无Docker CLI；只检查现有本地数据，没有读取远端生产。真实筹建、交付、持续运营仍未完成。

## 规划与实际变更

[Astra规划](plan.md)选择现有snapshot与HTTP授权/资料边界的交集，[六组HTTP测试](../../tests/test_runtime_http.py)通过实际loopback Server和cookie，覆盖全局/限域会话、两AU同名成员/session隔离、伪造请求不扩权、完整响应隐私、稳定读取、正式Engine状态链和当前授权变化。SDK检查点由实际SqliteSaver.put创建；会话元数据和业务状态是标明的临时fixture，不是实际模型产出。

没有发现生产缺陷，本轮生产代码零改动。首次六项中两项因fixture缺token_limit_field遭正式配置校验拒绝，补齐合法fixture后通过；不称作生产bug修复。随后强化私有根路径和会话字典不变断言，最终重跑6项/245项通过。

[独立Astra复核](review.md)115项通过，结论限受控子集。[矩阵](matrix.md)明确A03时间过期/旧实例迟到回执和A06连接/工作区revision/任职变化的真实SDK接续证据仍缺，不能报告A01–A06全部或U-041整体验收通过。平台未增加业务岗位、流程、权限、恢复、登记或控制能力。

## 测试

| 检查 | 实际结果与日志 |
| --- | --- |
| 首次HTTP | 6项中2失败，fixture配置缺必填字段；[原始日志](http-tests-first.log) |
| 合法fixture后HTTP | 6项通过，3.764秒；[日志](http-tests.log) |
| 强化断言后HTTP | 6项通过，3.591秒；[最终日志](http-tests-final.log) |
| Python第一次全量 | 245项通过，66.627秒；[日志](python-tests.log) |
| Python最终全量 | 245项通过，66.124秒；[最终日志](python-tests-final.log) |
| 独立Astra | 115项通过，31.831秒；[日志](independent-review-tests.log) |
| npm完整检查 | 退出0：管理8项、历史82任务/181依赖、动作安全9项、前端31项、类型与构建通过；[日志](npm-check.log) |
| 实际浏览器 | 当前Playwright可执行文件与常用Chromium命令不可用，未运行A11，不用组件检查替代 |

Python使用本轮仍可执行的.union/validation-20261031-0940/bin/python（固定Harness依赖，未重装）。GET读取前后核对业务表/预算、checkpoint文件集合与非SHM内容，执行/恢复/SDK正文读取设失败哨兵。只保证稳定fixture，无任意并发WAL绝对零写入或跨库原子快照承诺。npm检查的动作安全和组件验证也不是公司真实运行证据。

## 阻塞与下一小时

U-041保持blocked、completion=null；在制3/3、就绪0、阻塞7、done16不提升。A03/A06专项、WAL TOCTOU/跨库/恢复、实际Chromium和整体独立验收尚缺。模型/授权范围、真实Docker/镜像、持久VPS/SSH、真实New API资源阻塞保持；U-042托管控制未实现。

下一小时首项：Astra冻结A06实际SDK三组会话隔离口径，Sol分别验证连接revision、工作区revision和任职变化后的新会话、旧消息排除、历史保留与当前权限重检；有失败才最小修复。随后补A03过期/迟到证据，不先扩大托管。本轮没有推送、发布、付费、合并main或改生产。
