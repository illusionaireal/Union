# M1 模型目录机制（U-048）

2026-11-01。范围：只读目录快照、schema 校验、三态能力查询、连接投影附带目录元数据。
不含凭证引用、角色绑定、协议适配与成本金额。

## 实际改动

| 文件 | 改动 |
| --- | --- |
| `ai_union/catalog.py` | 新增。版本化快照加载、记录校验、按 provider/model 查询、三态能力查询、读路径容错 |
| `tests/test_catalog.py` | 新增 25 项机制测试 |
| `ai_union/model_api.py` | `public_connection` 增加 `catalog` 字段（未知显式为 null）；新增模块导入 |

## 关键语义

- 未知模型、未知能力一律返回 `None`，不推断、不默认 False。
- 同一模型 ID 出现在多个 provider 时视为歧义，同样返回 `None`。
- 目录记录出现 key/token/password/authorization 等字段直接拒绝，目录不承载凭据。
- 配置路径（`load()`）严格报错；读路径（`metadata()`）遇到损坏快照降级为 unknown，不中断连接列举。

## 验证

- 容器内 Python 3.13.5 运行 `tests.test_catalog`：25 项全部通过（见 `catalog-tests.log`）。
- 全量 `unittest discover`：323 项，1 failure / 1 error，与 HEAD 基线（298 项，同为 1 failure / 1 error）一致，无新增失败（见 `full-suite.log`）。
- 未重启 console 容器：新字段在下次重启后才出现在 `/models` 接口，以免打断进行中的订阅授权流程。

## 环境事实

宿主机 `python3` 为 3.8.15，`.venv/bin/python` 的 `pyvenv.cfg` 记录 3.13.5 且符号链接指向 `/usr/bin/python3`；
因此宿主侧解释器无法导入 3.9+ 语法（`dict | dict` 等）。**测试必须在运行容器内执行**，宿主侧只做语法检查。

## 未覆盖

- 目录数据本身未提供（`UNION_MODEL_CATALOG` 空），能力查询全部为 unknown。
- 无前端展示、无角色绑定、无回退、无成本金额。
- 本改动未触碰凭据路径，但新增了连接投影字段；M1b 凭证引用仍需独立权限复核。
