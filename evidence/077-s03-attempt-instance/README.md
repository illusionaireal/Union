# 077：S03.4d 执行绑定的宿主实例与"陈旧执行"（U-067 / 在线 #22）

2026-11-08 06:24–07:05。补上"服务重启后如何处理上一次未结束的执行"：执行尝试现在记录**持有它的宿主服务实例**，实例变化后该执行在读投影里显示为**陈旧**，并且**不能再继续用它执行**，必须先核对结束（R-03/R-04）。**仍未调用模型**，U-067 保持 `doing`。

## 本轮用户可验证结果

`GET /api/v1/work` 的 `attempts` 新增两个字段：

- `host_instance`：创建该执行的服务实例标识；
- `stale`：`status == "running"` 且 `host_instance` 与**当前**服务实例不同 → `true`（服务重启后就是这个状态）。

行为规则：

- 陈旧执行**不能**继续动作：`invoke_tool`、`reserve_step` 均被拒绝，信息为"该次执行由已结束的服务实例持有；请先核对并结束该次执行，不能继续用旧实例执行"。
- 核对路径仍是既有的 `finish_attempt`：可以用 `unknown`/`failed` 结算，结算后 `stale=false`，随后才能在**当前**实例上 `start_attempt`。
- 没有实例信息的旧执行（历史数据）保持兼容：`host_instance` 为空时不做陈旧判定，不会因升级被意外卡死。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-stale.txt` | 真实 RED：`KeyError: 'host_instance'`（投影没有该字段） |
| `green-stale.txt` | 17 项 `test_core_work` 通过，含新用例：启动执行记录实例 → 模拟重启（更换实例）→ 投影 `stale=true` 且工具/预约被拒 → `finish_attempt(unknown)` 结算 → `stale=false` |
| `regression-instance.txt` | 相关回归（work/governance×3/models/console/workspace/isolation/entrypoints/documents） |
| `management-check.txt` | `npm run check:management` |

过程中修掉自己一处实现错误：`domain/work.py` 只导入了 `CoreError, require`，我直接 `raise Rejected(...)` 造成 `NameError`，服务端线程崩掉（测试表现为 `RemoteDisconnected`）；已补导入并复验。

## 所有权与边界

- `ai_union/domain/work.py`：`active_attempt(work, instance)` 增加陈旧判定；`start_attempt` 记录 `host_instance`；`reserve_step`/`tool_target` 传入当前实例；`projection(state, instance)` 输出 `host_instance`/`stale`；`validate_state` 允许并校验 `host_instance` 为字符串。
- `ai_union/application/work.py`：读投影与各命令统一传 `self.app.instance`——**实例标识只来自宿主 Console**，不接受客户端传入。
- 规则层仍不访问存储/网络；没有任何"自动重放"或"静默重试"。

## 未完成 / 下一步

1. **S03.2e（唯一关键阻塞）**：真实模型循环（infer → tool_call → 回执 → 二次推理 → `submit_result`），需要可用模型连接与有限额度。
2. 投影里还可以显示"本次执行已产生的步骤/回执数量"，便于重启后一眼核对；前端可加一行"上次执行由旧实例持有，请核对"。

因此本卡仍 `doing`。
