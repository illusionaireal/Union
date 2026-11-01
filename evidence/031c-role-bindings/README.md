# 角色绑定与可用性回退（M2a / U-050）

2026-11-01。范围：默认连接与 planner/worker/reviewer 分别绑定、未绑定角色继承默认、
有界回退链、不可用连接的解析期回退、按工单类型选择执行连接。

## 实际改动

| 文件 | 改动 |
| --- | --- |
| `ai_union/model_api.py` | 新增 `ROLES`/`ROLE_BY_KIND`/`MAX_FALLBACKS`；`resolve_connection(role=...)` 支持继承与解析期回退；新增 `resolve_roles()`；`bind_connection` 支持 `role` 与 `fallbacks` |
| `ai_union/console.py` | `api_binding` 接受可选 `role`/`fallbacks` 并透传；`start` 构造 Harness 时传入各角色连接 |
| `ai_union/harness.py` | `HarnessExecutor._select()` 按工单 kind 选择连接（work→worker，decision→planner），连接进入会话键 |
| `ai_union/cli.py` | CLI 构建 Harness 时同样传入角色连接 |
| `tests/test_role_binding.py` | 新增 14 项机制测试 |

## 设计取舍（参照 dsh-superagent-prototype 的实现）

- **绑定是「角色 → 连接」的显式映射**，不把角色名散落在多处；`ROLES` 是唯一来源。
- **未绑定即继承**，等价于 dsh 的 `model: null`，但继承的是组织默认连接而不是宿主默认。
- **换绑只影响后续工单**：连接 id 与 revision 进入会话键，改配置会开新会话，不会让在跑的
  工作中途换模型（dsh 的 `docs/003-execution.md:143` 同样如此）。
- **回退只用于「不可用」**：连接停用、凭据缺失这类**解析期**失败才会沿链下移，并记录
  `fallback_from`。请求已发出后的失败**不在此处切换**——结果未知仍须人工核对，保持仓库
  既有的行动安全规则。

## 验证

- 14 项角色绑定测试全部通过（`role-tests.log`）。
- 全量 348 项，1 failure / 1 error，与 HEAD 基线一致，无新增失败（`full-suite.log`）。

## 未覆盖

- **运行期失败切换（401/429/5xx 后自动改道）未实现**，这是 M2b；当前只在解析期回退。
- 前端没有角色绑定入口，命令层已可用。
- 未做独立权限复核；角色绑定不扩大权限，但改变了执行所使用的凭据来源。
