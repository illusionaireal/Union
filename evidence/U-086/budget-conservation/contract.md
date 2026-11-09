# U-086 / #40：重开验收的逐步预算守恒

2026-11-09；实施 actor 为当前单一 codex-home 值守会话，在线成员另记
c18f0d21-1d63-4e37-af3e-2dbb78d75995；DSH 原 owner 不变。
基线 726dad42ec109e7dee3648ada68eabe7cb16f6f1，集成 4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c。
PR66 已进入作者分支，仍待非实施角色复核；不是集成采用。

## 冻结合同（行为修改前）

- PRD F04/F08/F12，Chapter D-05/R-01/R-02/K-04：已发生调用与未知占用不能因重开丢失。
- 复用 domain.work.budget：一个 used 步进计一个 used；reserved/unknown
  步进计一个 reserved；released 不计占用。本验收快照已要求全部步进结算，
  所以只对 unknown 计 reserved。不改变产品规则或增加新账本。
- 两 driver 经既有 readSnapshot/compareSnapshots 验证原主体/AU/Work/命令/
  attempt/model request/连接与逐请求用量。预算必须先与本快照全部步进相符，
  再比较重开前后相等。两份一致但已丢失/虚增占用的快照不得通过。
- max_calls 为正安全整数；used/reserved 为非负安全整数，且总占用不超
  max_calls。未知 usage 仍为 null，合法供应商用量元数据原样保留。
- 每份基线在保存前校验；compareSnapshots 对传入基线也独立校验，不能只
  靠调用者恰好先 readSnapshot。合法重排、不同服务实例重开仍可通过。
- 只修改验收 helper 与必要测试/证据/索引。测试用例来自两个完整重开片段，
  真实 Chrome→Core HTTP→SQLite 验证只读 helper，模型仅使用明确替身。
  不运行真实 driver main、不新增真实推理、迁移或采用产品变更。

预计1–2小时，一个共享验收结果无需另拆；依赖当前作者候选，保留所有历史。
完成需 RED→GREEN、相关回归、npm/Python全量、准确head CI和另一工程角色复核。

发布前读回（2026-11-09）：前述待复核为冻结时点。PR66准确726dad42现已获
chatGPT-online独立限定复核5827411245并进入作者分支，仍不是rewrite采用。
本预算守恒增量须另行绑定发布head复核，实施者不自行批准。
