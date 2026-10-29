# U-034 资源与工具申请：独立工程复核

2026-10-28；审阅角色 `workspace_authorization_review`。审阅 `support_requests.py`、Engine 操作和上下文接入、协议/工具编译、Harness 提交、Console 响应、CLI 及观察投影；独立于 U-023 治理描述审查。

## 结论

**通过，可采用当前申请记录与受信响应机制，无剩余阻塞项。** 这是需求及处理意向记录，不是预算、工具、采购或宿主授权机制；`accepted_for_action` 不会授予这些能力。真实组织能否正确提出需求、治理方是否实际处理以及后续业务效果仍待真实验收。

## 边界检查

- 新操作默认不加入旧章程；组织决策工具只有在章程与当前决策岗位权限交集包含 `request_support` 时才出现。普通工作不暴露该工具或组织申请历史，筹建身份不能提交正式申请。
- 请求通过原 `apply_decision` 校验当前身份、任职、版本及证据后提交；提出者、任职和时间由宿主记录。快捷工具不接受伪造提出者，手动操作也限制字段集合。请求与该次决定中的其他操作遵守原事务回滚规则。
- Harness 将申请纳入单独提交工具，沿用混合工具拒绝规则；申请本身不调用外部系统、不增加调用额度，也不绑定模型或工作区。
- 响应需要实际 board 凭据及当前版本。Console 还检查 board 会话、AU 范围、派发锁和幂等请求 ID；CLI 是受信宿主入口，持有派发锁，陈旧版本重试被拒绝。对受理或补充资料的响应不产生真实授权；declined 后不再改写同一请求。
- Console 对整个新响应请求在落库前检查已保存模型 key 和实际 board key；底层 `respond` 对响应依据再次检查。U-023 审查发现并修复的“拒绝请求仍记录 board key”问题，其前置检查已覆盖 `respond_request`；独立回归通过。
- 投影默认只给最近12条申请、每条最多12项证据及最新响应，提供总数和截断标记；不将最多20条响应历史全部灌入模型资料。完整请求状态保存在同 AU 私有状态中；没有跨 AU 查询或授权入口。
- 响应不清除 paused、unknown 或原调用占用；它只写响应、事件和组织版本。后续执行仍走原调度与未知结果核对规则。

## 独立验证

下列6项通过：

```sh
.venv/bin/python -m unittest \
  tests.test_support_requests \
  tests.test_harness.HarnessTests.test_support_request_sdk_records_need_without_changing_resource_grants -v
```

另在新临时 fixture 组织完成两组探测：

1. 模拟响应保存期间 `_save` 抛 OSError，state 与 events 完整回滚；在存在 unknown 的组织记录 accepted_for_action 后，runner 仍 blocked，预算、章程与岗位权限不变；paused 时响应不会恢复派发。
2. 实际启动 CLI 子进程读取并响应申请；同一旧版本再次响应被拒绝，响应计数保持1，模型调用占用不变。

这些检查使用临时状态、实际 SDK 和本地 HTTP 替身，未调用真实供应商、Docker、采购或企业系统，未改变真实公司章程或资源。本审阅没有修改实现。全量回归和真实自主协作结果由实施记录分别报告。
