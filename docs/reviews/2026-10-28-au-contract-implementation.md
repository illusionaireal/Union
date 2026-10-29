# U-023 AU 契约兼容接入：独立工程复核

2026-10-28；审阅角色 `workspace_authorization_review`。范围为 `au_contract.py`、Console 的可选 `controller_ref` 创建与 `controller_descriptor` 命令、同一读取事务中的 snapshot 投影及相应用例。同时核对 U-035 生命周期记录对冻结工作包及工作区授权的影响。**新增 U-034 申请、响应和 `respond_request` 业务分支另行审查，不包含在本结论内。**

## 结论

**两项阻塞修复后通过，可采用当前兼容元数据与只读投影实现，无剩余阻塞项。** 治理显示引用始终标明 `authority_source=legacy_board`，不会赋予外部主体实际控制权；未接入 SSO、跨 AU 授权或共享成员身份。真实企业身份集成、模型行为及持续运行不在本次验收范围。

## 权限及持久性

- 未配置新元数据的旧组织从原 board_name 和 AU ID 派生显示引用，读取不迁移、不修改 state 或 meta。
- 未绑定成员的宿主投影 `supported_operations=[]`。带行动身份的库调用须先确认 active、成员存在、任职有效且匹配，再通过原 `_authorize` 检查当前决策责任及章程/岗位操作交集。库接收的是受信 Engine 句柄，不是新的 HTTP 身份声明入口；Console 仍先验证会话与组织范围。
- `controller_descriptor` 沿用 board 会话、本地实际董事会凭据、派发互斥、基准版本和命令幂等机制。描述与章程、模型配置、资源和实际控制凭据相互独立；修改描述不会授予任何操作。
- snapshot 在已有只读事务中使用同一 state 和连接构造 projection，避免重新读取不同版本的描述/资源。成员引用补充 AU 域，内部键不改写。
- 独立模拟创建中元数据写入后发生 OSError：原创建回执成为 unknown；相同请求返回原回执，没有重复注册。测试只使用临时组织，不涉及真实公司。

## 发现及关闭

1. **筹建身份绕过投影的成员约束。** 原实现直接调用 `_authorize`，`actor=bootstrap` 加伪造 assignment 在筹建组织可取得内部操作列表。修复后 projection 先验证正式 active 成员和任职；原筹建授权机制未扩大。新增筹建与 active 场景回归通过。
2. **拒绝的描述请求仍将 board key 写入命令 payload。** 原实现到 `configure_descriptor` 才检查 extra_secret；Console 捕获拒绝后仍保存原请求。我在临时 Console 复现为 `receipt_status=rejected` 且原 key 出现在该请求 payload 中，未输出凭据。修复后 Console 在持久化和原回执查询之前检查整个 public_input，拒绝包含实际 board key 的请求。新增 Console 用例确认 commands、events 与描述 meta 均不含该 key。

## U-035 交叉检查

生命周期只根据宿主持久提交的工作状态变化记录；旧工作读取不补造时间，首次新变化保留 partial。`begin_work` 在同一事务内先保存状态时间再冻结工作包，预约失败仍由原事务回滚。检查点及工作区授权相关回归通过，未发现新增时间字段导致工作包与原持久包不一致。`work_metrics` 是只读记录指标，交付状态不被解释为业务验收成功。

## 独立验证

以下26项在修复后独立运行通过：

```sh
.venv/bin/python -m unittest tests.test_au_contract tests.test_lifecycle tests.test_workspace tests.test_workspace_harness -v
```

另执行上述元数据创建中断/幂等探测。测试使用本地临时组织、实际 SDK 及 HTTP/容器替身；真实供应商、Docker、企业系统调用均为0。全量回归由主实施记录另报。本审阅未修改实现。
