# 授权工具结果进入后续模型轮次：工程候选

2026-11-08；原请求 [PR #17](https://github.com/illusionaireal/Union/pull/17)，本轮重复读回的最新 head 为 `02f8a7832f23e71a7bdbad4727914b566646f4a2`。
分支 `codex/u067-tool-context`；实施 actor：codex-home / 当前 Codex 会话；独立权限复核待完成。
原 owner 与 U-067 整卡验收保持不变。[协助范围已通知原作者](https://github.com/illusionaireal/Union/pull/17#issuecomment-6717910970)。

## 实际变化

沿 [编码前冻结契约](../../../specs/053-union-rewrite/s03-tool-context-contract.md) 与 ADR-0005，成功模型轮次在同一 GovernanceStore 事务内保存私有 assistant/tool 消息、原调用 ID、实际文件列表/正文、native 上下文及来源。审计中的 step 摘要绑定私有 payload，后续模型能根据实际工具结果继续决定；带工具调用的说明正文不再提前变成成果。

接续前检查当前身份、有效治理、Work/Definition/binding/Mandate、工具范围、资料根及其实际绑定摘要。快照损坏、缺失、撤权、目录重新绑定或上下文超限时拒绝派发；不会重读文件伪造原结果，也不跨 Work 传播。正常重启后按已有规则显式结束旧 attempt 并开始新 attempt，可沿原 Work 接续已确认的资料。工具正文/native 只在私有表内，公开投影与审计保留摘要/来源；最终候选成果仍沿原公开读取接口。

同时修正自动批次的完整配对和授权校验。旧“剩余调用预算”测试授权 read_document 却返回 list_documents，本次把其测试前提改为明确授权 list_documents，保留预算断言，并新增未授权工具不读取目录的反例。

PR #20 的当前 Linux CI [运行 42451847017](https://github.com/illusionaireal/Union/actions/runs/42451847017) 暴露两个原 HTTP 测试配置的权限缺陷：临时 modeld.json/令牌使用默认文件权限，触发现有 0600 校验。对应测试文件与本分支原基线相同；本次仅让两个 fixture 的三份私有配置文件使用 0600，未改变生产校验或 CI 门禁。Windows 定向验证通过，Linux 修复结果以本候选 CI 为准。

最新来源补充：本轮进行相同 fixture 修正期间，前台协调者已在 PR #20 发布 `098a3b9a4f4593ab8015f41c6cce9518f58639ea`，包含独立工程角色复核及 Linux RED/GREEN。已抓取并逐文件对齐该相同修正，避免两份等价补丁产生集成冲突；此独立复核属于协调者，只覆盖 PR #20，不能替代本工具接续候选的复核。组合运行代码仍与 `ab31480` 一致。

PR #20 随后在当前 Windows job `128645022754` 出现另一项原测试失败：目录故障注入按未解析路径比较，CI 的等价临时路径别名使注入失效，预期 unknown 实际 succeeded。该文件与本轮基线相同；修复已经在 PR #15 的 `b9b461a` 被审阅、合入集成分支。本候选以保留来源的 cherry-pick 复用这一单文件修正，不另改生产身份/创建代码或故障断言；S03 作者分支仍须完成其余集成分支收敛。

## 验证与可复现入口

固定 Python 3.12.10、deepagents 0.7.28、langgraph-checkpoint-sqlite 3.1.2；Node 24.19.0 / npm 11.13.0，UTF-8。模型全部为合成 fake 或回环 HTTP；真实推理次数为 0。

- 原三个独立探针：最新原源码 **3 tests / 3 failures / 0 errors，2.977s**；本候选 **3 tests / 2 failures，2.982s**，工具正文项已 GREEN。
- 新行为 RED：修正测试报告方式后 **7 tests / 7 failures / 0 errors，7.263s**（含两个非法批次子例）；未改坏已有源码制造 RED。目录重新绑定和 native 保留各追加一项真实 RED。
- 最终新测试：`python -m unittest -v tests.test_work_context`，**13 tests / OK，13.836s**。动态 fake 从收到的实际文件名/正文构造答案；验证 BOM/Unicode/CRLF、工具配对、来源、重启、篡改/缺失、根绑定/章程撤权、跨 Work 隔离、完整批次、native、大小限制与事务回滚。
- `npm run check` **通过**，含 21 个前端文件 / 206 项测试、类型与构建。未新增用户界面。
- 两个修正后的 HTTP fixture：`python -m unittest -v tests.test_work_transport_http tests.test_core_work_http`，**4 tests / OK，2.635s**；Windows 不冒称 Linux 权限门槛已验。
- Python 全量：**662 tests / OK (skipped=8)，391.596s**。运行代码从启动至结束未变；期间两个已发现的 HTTP fixture 仅补 0600，另经上述 4 项定向验证。8 项平台/未启用集成跳过不算通过，不声称 Linux 或最终组合全量已验。

精简输出：[RED](red.txt)、[新测试 GREEN](green.txt)、[全量摘要](python-full-summary.txt)、[组合验证](combined.txt)；[源码和验证元数据](verification.json)。原始日志只留当前 checkout 的忽略目录，不提交私有执行日志。

组合检查没有改动作者或 PR #20 分支：从候选 Git 树 `b61e340c08f8b36b2785b683cc9016cb31ba3951` 导出到当前 checkout 的忽略目录，应用 `a1001e4..ab31480` 中五个运行/测试文件的原差异。组合的工作、上下文、撤权观察及 HTTP **64 tests / OK，58.506s**；原三个探针只剩预约项 **1 failure，3.000s**。此组合不包括后来仅调整 0600 的两个 fixture，不声称完成合并或全量组合验收；文档和管理记录仍需实际集成时处理。

## 未完成与下一步

1. 派发前持久化预约/原请求归属仍 RED；在途授权/身份变化后的事实保存及未知执行恢复仍需冻结共享事务后修复。本子项不把工具或结果被拒绝后的计量缺口冒称已解决。
2. 本工具接续候选待另一工程角色复核；[PR #20](https://github.com/illusionaireal/Union/pull/20) 已有协调者的独立限定复核，但最新 Windows CI 尚失败。各候选当前 head 全部必需 CI 通过才可采用。原 #17 仍不可合并，U-067 不关闭；作者还需吸收集成分支的已合并变化。
3. 看板通过个人 env 文件指定的代理实时读回 HTTP 200：revision 197、#22 version 7、progress，原 assignee 保持。发布后再读当前版本，仅追加本次协助证据，不接管卡片。未使用个人代理的 board 直连失败不覆盖该成功来源。
4. Go 两次额度已经用完。本次无真实模型、NAS 切换、业务迁移或持续业务；没有更改监督脚本、宿主配置、计划任务或外部协调者分支。

用户在本轮的参与属于评审后的工程补救指示；未发生真实日常业务验收。测试数不代表业务质量或自主改善。
