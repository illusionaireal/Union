# 凭据环境变量引用（M1b / U-049）

2026-11-01。范围：连接可只保存环境变量名，密钥不再落库；内联密钥与环境引用互斥。

## 实际改动

| 文件 | 改动 |
| --- | --- |
| `ai_union/model_api.py` | `CONFIG_FIELDS` 增加可选 `api_key_env`；`connection_key()` 在派发时解析；`public_connection` 返回 `key_source`；`resolve_connection` 按变量名报错；`reject_saved_secrets` 纳入环境值 |
| `tests/test_model_credentials.py` | 新增 11 项机制测试 |

## 语义

- `api_key_env` 为**可选**字段，旧配置（无该字段）保持原行为，不迁移。
- 内联密钥与环境引用**只能二选一**；同时提供时拒绝，避免来源不明。
- 未配置变量的连接仍可保存（`has_api_key=false`，`key_source=missing`），派发时按变量名报错，不回显值。
- 环境变量的**值**与已存密钥同等对待：出现在配置依据或命令文本中会被拒绝。

## 验证

- 11 项凭据测试全部通过（`credential-tests.log`）。
- 全量 334 项，1 failure / 1 error，与 HEAD 基线一致，无新增失败（`full-suite.log`）。

## 未覆盖

- 独立权限复核未进行（按仓库要求，凭据路径变更需另一工程角色复核后再采纳）。
- 未做真实供应商调用；仅验证解析与投影。
- 前端仍只有 API Key 输入框，没有环境变量输入项（后端已就绪，UI 另行实现）。
