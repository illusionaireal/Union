# 097：真实有界验收的可执行夹具（默认跳过）

2026-11-08 13:54–14:10。把审查处置里"真实有界验收（≤2 次调用、每次 ≤1024 输出 tokens、仅合成资料）"从**协议文字**变成**可执行测试**：`tests/test_core_work_real.py`。宿主条件具备时一条命令即可取证，且额度上限写死在代码里。

## 设计

- **默认跳过**：除非同时设置 `UNION_MODELD_CONFIG`（宿主私有 modeld 配置）与 `UNION_REAL_ACCEPTANCE=1`，否则 `skipTest`，正常测试运行永不花钱。
- **额度写死**：`max_calls=2`；`max_output_tokens = min(宿主配置, 1024)`。
- **仅合成资料**：临时目录内生成一份合成 Markdown（"不含任何真实业务数据"），经宿主登记的只读根暴露。
- **走的都是产品真实路径**：`start_work` → `start_attempt` → `run_loop` → 读 `/api/v1/work`；通道用 `modeld_factory(UNION_MODELD_CONFIG)` 装配的真实 `ModeldWorkTransport`。
- **断言有界与诚实**：`budget.used ≤ 2`、`usage.output_tokens ≤ 2×1024`、`cost_status == "unknown"`，并输出 `{turns_used, usage, cost_status, tool_calls, results}` 便于贴入证据。

## 与 TDD 的关系（如实说明）

这不是新行为代码，而是**验收夹具**，因此没有"先观察 RED"；它的 RED 会在首次真实运行时才出现（若协议不符即失败）。目前的证据是：默认跳过且原因明确（`skip.txt`），相关回归 38 项通过（1 跳过）。

## 验证

| 检查 | 结果 |
| --- | --- |
| `tests.test_core_work_real` | `OK (skipped=1)`，原因："real acceptance needs UNION_MODELD_CONFIG and UNION_REAL_ACCEPTANCE=1" |
| 相关回归（work / real / http） | 38 项通过（1 跳过） |
| 真实模型调用 | **0**（未设置环境变量） |

## 宿主就绪后的执行方式

```powershell
$env:UNION_MODELD_CONFIG = "C:\Users\Benedict\.union-modeld.json"   # 宿主私有，权限 0600
$env:UNION_REAL_ACCEPTANCE = "1"
.\.venv\Scripts\python.exe -m unittest tests.test_core_work_real -v
```

输出行 `real acceptance: {...}` 即为 #22 的"真实有界验收"证据；随后把结果写入 `evidence/097-.../` 并在卡片评论引用。
