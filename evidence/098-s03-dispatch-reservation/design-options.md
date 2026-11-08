# 098 附录：三种落地方案对比（供协调者裁定）

现状：`run_step` 先在只读事务里做规划（预算检查），模型调用完成后才在**一个事务**里 `reserve + settle`。因此两个并发 `run_step` 可以同时通过预算检查并都派发；进程在"派发后、提交前"崩溃则没有任何预约痕迹（只有 modeld 侧的持久请求）。

治理不变量（`ai_union/adapters/governance_store.py`）：**能改变有效状态的事件，其回执必须是 adopted（`receipt.status == "succeeded"`），且 `request.base_version == version - 1`、`request.kind == event.kind`。** 这条不变量是"回执与有效状态一致"的核心，不允许为某类事件开口子而不经审查。

## 方案 A：释放也作为 adopted 事件（改动最小，API 语义变化）

- 派发前：事务 1 写 `reserved` 步进 + **succeeded** 回执（`phase: reserve`，`dispatch: {request_id, at}`），版本 +1。
- 调用后：事务 2 结算（`used` / `unknown` / `released`），回执 **succeeded** + `outcome` 字段；版本再 +1。
- 客户端读 `outcome` 判断"通道拒绝/释放"（`outcome: released`），而不是靠 `status: rejected`。
- 代价：① 一条命令产生两个版本/两条回执；② 现有 UI/客户端若以 `status: rejected` 表示拒绝，需要改为读 `outcome`；③ `run_loop` 需按 `outcome` 停轮。
- 优点：不新增表、不绕过审计、重启后能直接看到 `reserved` 步进并 `reconcile_step`。

## 方案 B：预约走独立审计（不占治理版本）

- 新增 `work_dispatches` 记录（au_id / work_id / request_id / at / instance / state），派发前写入、结算后更新；预算计算把 `work_dispatches` 的进行中条目计入 `reserved`。
- 优点：不动治理回执语义；并发与"原请求归属"都能表达。
- 代价：① 同一事实（调用占用）有两处记录（治理步进 + dispatch 表），需要明确唯一写者与对账规则；② 重启恢复必须保证两表一致，否则会重复计数；③ 与"不要建第二份状态表"的评审要求存在张力，需要协调者明确允许并写进契约。

## 方案 C：按工作串行化的派发锁（最小修复，非持久）

- 以 `(au_id, work_id)` 为键，在进程内加互斥锁，锁内完成"规划→派发→结算"；跨进程/跨主机依赖 modeld 的请求 id 唯一性兜底。
- 优点：改动极小，立刻消除同机并发双派发。
- 缺陷：**不是持久化预约**，进程崩溃后没有本地痕迹，不满足 checklist 第 2 项的"持久化"要求；只能作为过渡。

## 建议

1. 若允许"拒绝以 `outcome` 表达"，选 **A**（最符合现有审计模型，代码量可控，已有 RED 与实现雏形，被我回滚保留在 `evidence/098/`）。
2. 若坚持 `status: rejected` 的对外语义，则选 **B**，但需把"预约表"写入契约与恢复对账规则，并接受一次架构评审。
3. **C 只能作为 A/B 落地前的临时缓解**，不能用来勾选该 checklist 项。
