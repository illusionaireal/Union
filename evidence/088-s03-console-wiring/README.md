# 088：宿主 Console 按需装配模型通道（U-067 / 在线 #22）

2026-11-08 07:14–07:50。补上 087 之后的最后一处宿主接线：**Console 只在宿主显式配置时装配通道**，未配置时保持"没有通道"的明确拒绝，不会静默塞入假实现。

## 本轮用户可验证结果

- 启动时若设置了宿主环境变量 `UNION_MODELD_CONFIG`（指向宿主私有的 modeld 配置文件，0600），`Console` 会把 `WorkService.transport_factory` 接成 `modeld_factory(该路径)`；`run_step`/`run_loop` 因此可以真正调用模型。
- **未设置**时工厂保持 `None`：调用仍返回"宿主尚未配置模型执行通道"的拒绝，绝不静默降级或伪造成功。
- 配置路径只由宿主提供，核心不读默认位置、不猜端点；路径缺失/格式非法时，工厂在建立通道时抛 `Rejected` → 回执拒绝、**不留步进**（与 085 的"明确拒绝"一致）。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-console-wiring.txt` | 真实 RED：设置 `UNION_MODELD_CONFIG` 后 `transport_factory` 仍为 `None` |
| `green-console-wiring.txt` | 34 项 `test_core_work` 通过：未配置宿主 → `None`；配置宿主 → 可调用工厂 |
| `regression.txt` | 相关回归（work/console/governance×2/models/workspace/documents/creation/isolation/adapter） |
| `management-check.txt` | `npm run check:management` |

## 所有权与边界

- `ai_union/console.py`：新增 `_work_channel_factory()`（读 `UNION_MODELD_CONFIG`，缺失即 `None`），在构造 `WorkService` 后立即接线；未改变任何既有启动参数或默认行为。
- 工厂本身仍在 `ai_union/work_transport.py`（087），核心不持有密钥正文，只把宿主给的路径交给 `ModelServiceClient`。

## 仍未验证（如实说明）

- 真实 modeld 往返仍未执行（网络不可用、服务未启动）；本轮的验证止于"工厂按配置存在/不存在"。
- 真实有界验收协议（≤2 次调用、≤1024 输出 tokens、仅合成资料）见 [086](../086-s03-pr-readiness/README.md)，仍待网络与宿主环境。

## 下一步

1. 网络恢复：推 `dsh/s03-work-runtime` → PR。
2. 宿主设置 `UNION_MODELD_CONFIG` 并启动 modeld → 跑一次 `run_loop` 完成真实有界验收，记录 usage / 费用未知项 / 候选成果。
3. 若 modeld 不可用：用 `model_api`/`model_protocols` 实现同一端口（直连供应商），同样先受控再真实。
