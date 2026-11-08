# 087：宿主持有模型通道的自动装配（U-067 / 在线 #22）

2026-11-08 07:09–07:45。补上 086 里列出的最后一个代码缺口：**通道不再只能由测试手工注入**，宿主可通过工厂为每个 AU 装配通道（默认仍是"未配置就明确拒绝"）。

## 本轮用户可验证结果

- `WorkService.transport_factory`：宿主可注入 `factory(au_id, connection) -> channel`。
- 调用 `run_step` 时若无固定 `transport`，先向工厂要通道；`step_plan` 现在把该工作定义里的**模型连接**（`id/revision/model/grant_ref/grant_revision/max_output_tokens` 等，取 AU 的 `model_access`）一并带出，工厂据此构造真实通道。
- 工厂失败分两类：抛 `Rejected`（如"模型服务宿主配置尚未就绪"）→ **拒绝且不留步进**；其他异常 → 同样拒绝（建立通道失败，什么也没执行）。
- 两者都没有（无 transport 也无 factory）→ 仍按原语义拒绝："宿主尚未配置模型执行通道"。
- 新增 `ai_union.work_transport.modeld_factory(config_file, timeout_seconds=…)`：从**宿主私有配置**构造 `ModelServiceClient` 并绑定 `ModeldWorkTransport`；工作没有可用连接时抛 `Rejected`。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-wiring.txt` | 真实 RED：2 项失败（工厂被忽略；工厂抛 `Rejected` 时仍被当成"未知"留下步进） |
| `green-wiring.txt` | 38 项通过：工厂收到 `au_id` 与含 `model` 的连接；成功时 usage 落到步进；工厂失败时无步进且回执含原因；无通道/无工厂仍是"通道"拒绝 |
| `adapter-tests.txt` | `test_work_transport` 7 项通过（新增 `modeld_factory` 两项：按配置构造、无连接时拒绝） |
| `regression.txt` | 相关回归（work/adapter/governance×2/models/console/workspace/documents/creation/isolation） |
| `management-check.txt` | `npm run check:management` |

过程中修掉自己一处测试放置错误：新用例被追加到 `if __name__ == "__main__"` 之后成了死代码（只跑 5 项），移回类内后 7 项全跑。

## 所有权与边界

- `ai_union/domain/work.py`：`step_plan()` 输出 `connection`（仅数据，不做网络/存储）。
- `ai_union/application/work.py`：`WorkService` 增加 `transport`/`transport_factory` 两个注入点与解析顺序；失败语义与 085 一致（拒绝 ≠ 未知）。
- `ai_union/work_transport.py`：新增 `modeld_factory`（宿主侧便利装配），仍不读取任何密钥正文，配置路径由宿主提供。

## 仍未验证（必须如实说明）

- 工厂产出的真实通道**尚未对运行中的 modeld 执行**（网络不可用、服务未启动）；事件/结果字段形状来自既有 `ModelServiceTransport` 用法。
- 宿主（`Console`）目前**不自动**注入工厂；需要在启动配置里显式接上 `modeld_factory`（属宿主接线，不在本卡代码范围）。
- 真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）仍待网络。

## 下一步

1. 网络恢复：推 `dsh/s03-work-runtime` → PR（清单见 [086](../086-s03-pr-readiness/README.md)）。
2. 启动 modeld，宿主注入 `modeld_factory`，跑一次 `run_loop` 完成真实有界验收并记录 usage / 费用未知项 / 候选成果。
