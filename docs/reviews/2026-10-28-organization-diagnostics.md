# U-033 有界组织诊断：独立工程复核

2026-10-28。审阅角色：独立工程审阅代理 `workspace_authorization_review`。基线 `6835b645f7823dc545782d601a324e593d964840`，审阅其上的 U-033 未提交改动；不包含后续生命周期实现。

## 结论

**修复后通过，可采用为现有决策资料中的有界只读诊断。无剩余阻塞项。** 此结论仅覆盖代码、确定性行为与实际 SDK/本地 HTTP 替身；不证明真实模型自主诊断有效，也不证明组织自主改进或持续运营。

## 范围与检查

- 阅读 `AGENTS.md`、`docs/AU_CAPABILITY_AUDIT.md` 与 020 规格；审阅 `ai_union/diagnostics.py`、`Engine._context` 接入、诊断测试及新增 Harness 测试，并追踪原决策授权、模型输入投影、失败脱敏和未知执行阻断路径。
- 资料只增加在现有非筹建的组织决策上下文；普通工作上下文和筹建上下文不获得历史诊断。正常决策派发仍先验证原决策任职及章程权限。宿主 `context()` 保持原有宿主读取入口，不新增成员工具或外部 API。
- 最近调用默认12条、最大30条，成果引用使用同一上限，均提供总数和截断标记。输出使用受限状态、合法引用、规范时间、非负整数 token；费用保持未知。没有复制原始 run package、result、reason、命令输出、模型/供应商标识或成果正文/宿主路径。失败说明由 `public_failure` 依据白名单重新构造。
- 新投影只执行 SELECT 和内存投影，不改变组织版本、事件消费、预算或执行状态。未知执行不因读取诊断而核销或重放。
- 此脱敏结论专指新增 diagnostics；原有业务成果、工作和事件资料继续遵守既有范围，未声称完成全组织资料访问控制重构。

## 发现及关闭

发现一项阻塞兼容问题：最初直接对 SQLite `json_extract(result,'$.failure')` 返回值调用 `json.loads`。既有引擎允许历史决定包含额外顶层字段，通过正常 `begin_decision` / `finish_decision` 提交 `failure=42` 后，下一次 `context()` 会触发 TypeError。该问题不需要修改数据库就能复现，足以阻断后续决策。

实现方已将 SQL 改为仅在 `json_type(...)=object` 时提取 failure，其余视为空；同时防御非字典历史 usage。新增正常引擎路径测试覆盖数字、布尔、字符串与数组 failure。审阅者复跑通过，问题关闭；没有修改原历史记录。

## 独立验证

下列8项通过：

```sh
.venv/bin/python -m unittest \
  tests.test_diagnostics \
  tests.test_harness.HarnessTests.test_decision_diagnostics_reach_sdk_without_private_failure_or_worker_history \
  tests.test_harness.HarnessTests.test_provider_unknown_is_not_automatically_resumed \
  tests.test_model_api.ModelAPITests.test_provider_error_is_unknown_blocks_further_calls_and_retains_reservation -v
```

另用新临时 active fixture 组织验证：工作进入 unknown 后，读取决策 diagnostics 能看到 unknown；随后调用 runner 仍返回 blocked，执行器未被调用。读取及受阻派发前后，state、events、runs、budget 完全相同。

本次审阅未修改实现、未操作真实公司状态、未调用真实供应商、Docker 或外部企业系统。全量项目回归及真实验收由实施记录分别报告，不能从本次8项检查推算。
