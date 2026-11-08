# S03 循环后续拒绝的父回执修复

评审接续：[DSH #26/#27 的逐项答复](review-response.md)记录新增停止阶段字段、
schema 3 第二轮预约故障验证，以及 PR #25 的事务/版本/回退边界；这是实施者
答复，独立复核仍待另一工程角色完成。原始交付记录保留如下。

2026-11-08。实现 actor：当前 codex-home 值守会话；原在线卡 #22 的 DSH
owner 保持。基线 `e452f26fb836572673fca34965ce3a28b0da6b66`，分支
`codex/u067-loop-fact-summary`。这是[派发证据](../dispatch-reservation/README.md)
已经记录的父循环汇总缺口，不改 PR #22 的真实验收 driver。

首轮调用和工具读取已持久保存后，另一 Work 增加 AU 版本、用户退出登录、
或治理者完成交接，会使下一轮准入抛错。原接口仅返回 409/403，没有保存
原父循环回执；子步骤及其用量仍在，不能声称它们也已丢失。

修复在现有循环中处理确定的准入拒绝：核对原子请求身份和持久记录；存在
最终子回执时保留其事实，未预约时停止并汇总，已有未决预约时保持原错误和
恢复路径。父回执由原 GovernanceStore 保存，不给未派发步骤计费，不补造
子回执、不改审计 adopted 规则、授权判定或 schema。重复父请求返回原回执。

## 严格 TDD 与边界

先冻结[契约](../../../specs/053-union-rewrite/s03-loop-receipt-contract.md)，
再加入 `tests/test_work_loop_receipts.py` 并运行：7 项中 4 failures、0 errors。
三个后续拒绝返回 409/403 而没有父回执；首轮预检拒绝同样没有父回执。
已有未决预约的普通拒绝、完整性故障和存储故障三项保护测试原本通过，未
撤掉或破坏正常实现制造 RED。

最小 18 行运行代码修复后，7 项全部通过。验证实际本地 HTTP/SQLite：
首轮工具读取和 11 input / 4 output tokens 保留，第二次模型调用为零；
首轮即拒绝则调用为零；重开/重投没有再派发；失效登录不能查回执，原治理者
仍能按既有规则查询自己的回执。迟到保存故障保留 reserved，恢复只返回
unknown，不释放或重复调用。原三个独立探针在本候选上全部通过。

命令：

```text
python -m unittest tests.test_work_loop_receipts -v
python evidence/U-067/independent-review-probes.py <source-directory>
python -m unittest discover -v
npm run check
```

最终本地验证：Python 全量 714 项、9 跳过，427.807 秒，通过；npm check
通过，包含 37 项管理、9 项动作安全、21 个前端文件/207 项测试、类型检查
及构建。代码与测试摘要见 [verification.json](verification.json)。PR #17
随后已合并为 `bbe8068335c32c04bdcf6d4fa20375245b912cf9`，与原基线代码树
完全一致；本分支已快进到该集成基线，再交付上述限定差异。

本轮只使用 fake transport 和现有受控夹具，无真实模型调用。本实施会话不
充当独立复核人，采用仍须另一工程角色复核和当前 head CI。未切换 NAS
业务服务、迁移数据或关闭 U-067 真实/持续出口。
