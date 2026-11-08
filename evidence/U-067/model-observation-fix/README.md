# 已完成但撤权的模型调用：工程修复候选

2026-11-08；原请求 [PR #17](https://github.com/illusionaireal/Union/pull/17)，精确检查基线 `1b00336fba787f93938f96b809691244a55efa8d`，分支 `codex/u067-model-observation`。
实施 actor：codex-home / 当前 Codex 会话；独立工程复核待完成。在线 Kanban 本轮失败，实际个人 user.id、原 owner/version 不推断、不写入；未认领或释放 #22。协助范围已通知 [原作者](https://github.com/illusionaireal/Union/pull/17#issuecomment-6717688099)。

发布候选已接入作者的 `a1001e47dc7cfd909b75b3a9bde1b916c93e4d51`（执行前连接检查），作为父提交。作者随后推进到 `02f8a7832f23e71a7bdbad4727914b566646f4a2`（用量汇总）；已读取并抓取精确对象，三项原问题的执行分支没有变化。保持小差异草稿，并以无冲突临时合并树 `e8a8d6945ce180c35d662b8727a37ea5365c2392` 验证与最新作者变更的兼容；未改写作者分支。

## 范围和契约

本子项预计 2–4 小时，独立结果是完成后撤权不再抹去已发生的模型调用。沿 [编码前契约](../../../specs/053-union-rewrite/s03-model-observation-contract.md) 和 ADR-0005；契约冻结时 SHA-256 为 `0bed06fadd1ed9bcfa70953e00ff2b9e403e5f16435c9fd2a2a264145f67e705`。

模型服务完成后撤权，以专用结果携带原 request ID 和安全筛选的 token 用量；不把正文或工具传给应用。领域层通过同一 GovernanceStore 事务保存 used 步进、用量和费用未知，工作与成果保持未完成；循环立即停止并计入这一轮。已接受后的越域、乱序或结果结构错误进入 unknown，不再冒称未执行。普通成功、派发前明确拒绝和未知回执保留原语义。

采用仍需另一工程角色复核权限/计量范围。没有修改运行中 AU、宿主配置、监督脚本、外部协调者分支或真实部署；真实模型调用为 0。

## 验证

- 最新原始源码：原探针 **3 tests / 3 failures / 0 errors，2.665s**，在任何行为代码改动前确认全部三个问题。
- 新测试 RED：**4 tests / 2 failures / 4 errors，1.821s**；errors 是预期应归入 ServiceError 的派发后分支实际抛出 Rejected，属于错误分类缺陷，非依赖/环境错误。
- 定向 GREEN：`python -m unittest -v tests.test_work_observation tests.test_work_transport`，**11 tests / OK，2.448s**。覆盖正文/工具不采用、已用次数/usage、原请求回执、真正服务重启后的记录，以及 used 不可改为 released。
- 原探针复验：**3 tests / 2 failures / 0 errors，3.060s**；完成后撤权项 GREEN，预约和工具正文两项仍 RED。
- `npm run check`：通过；前端 **21 files / 206 tests**、类型检查及构建通过。
- Python 全量：`python -m unittest discover -v`，**651 tests / OK (skipped=8)，381.887s**。
- 交付历史更新后 `management:render`、`check:management`、`check:plan` 和新证据相对链接检查通过；源码从定向 GREEN 至全量结束保持不变。
- 接入 `a1001e4` 后：工作/transport/HTTP 定向 **50 tests / OK，39.326s**；重新执行 `npm run check` 通过（206 前端测试），Python 全量 **652 tests / OK (skipped=8)，415.462s**。8 项跳过是 Windows 主机能力、未构建 modeld 包或未启用 Bun SDK 集成，完整原因在精简日志；不把跳过算通过。
- 与最新 `02f8a78` 的合并树：工作/transport/HTTP **51 tests / OK，48.590s**；原三项探针仍 **2 failures，3.252s**，撤权项 GREEN。该树没有声称全量/真实 modeld 已验；合并采用仍需当前 CI 和另一工程角色复核。

固定环境：Node 24.19.0 / npm 11.13.0；Python 3.12.10，deepagents 0.7.28、langgraph-checkpoint-sqlite 3.1.2，UTF-8。锁文件与原安装工具链匹配，没有把裸 checkout 缺依赖当作代码失败。
原始本地测试日志只留当前 checkout 的忽略目录 `.union/u067-model-observation/`；以下提交的精简证据仅包含合成测试结果，不含密钥、主机地址或私有运行日志。

精简记录：[原三项 RED](original-probes-before.txt)、[新增测试 RED](red.txt)、[定向 GREEN](green-focused.txt)、[原三项复验](original-probes-after.txt)、[全量 Python](python-full-summary.txt)。

发布核对：[接入作者连接检查后的定向](green-rebased.txt)、[相应原探针](original-probes-rebased.txt)、[相应全量 Python](python-rebased-full-summary.txt)、[最新作者合并树定向](combined-affected.txt)、[合并树原探针](combined-original-probes.txt)、[源文件与验证元数据](verification.json)。

## 明确未完成

1. 派发前预约与原请求关联、重入和并发治理/身份变化后的归属仍需共享事务修复；本子项只处理当前核心责任仍有效时 modeld 的完成后撤权，不能声称关闭竞争窗口。
2. 授权工具正文和 assistant/tool 消息向下一轮传递仍缺失。
3. #17 仍不能合并，U-067 不完成；真实有界自动业务和中断验收、持续运行均未通过。Go 两次额度已耗尽，不新增真实调用。

下一步：另一工程角色审查本小差异候选，跟踪该 head 的 CI；继续按最新 #17 冻结并修复预约事务和上下文传递。Kanban 恢复后必须先读最新 board/version，再同步本次协助证据，保留原 owner。
