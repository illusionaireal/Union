# U-086：独立复跑值守 session 探针（对 5545d4f 的双向核对）

2026-11-10 五轮。值守已在其 `recheck-5545d4f-20261110` 中确认我的 session 修复；本轮
**用他们的探针、在隔离检出上自己复跑一次**，避免只依赖对方的转述。执行者 DSH 会话
`dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 做法（只读、可复现）

1. `git archive 5545d4f` 导出隔离候选目录（2307 文件）。
2. 从值守分支 `codex/u086-session-resolution-review-01a1c602` 取出
   `evidence/U-086/recheck-5545d4f-20261110/` 的 `session-probes.py`、`source-manifest.json`、
   `contract.md`、`session-result.json`（**未改动任何字节**）。
3. 在探针目录内执行：

```text
python -B session-probes.py <candidate-5545d4f> <result.json>
```

## 结果（与值守记录一致）

- `Ran 4 tests ... OK`，**exit 0**；`tests: 4, passed: 4, failures: [], errors: []`，
  `source_unchanged: true`，`real_model_calls: 0`，`source_manifest_sha256` 与值守一致。
- 四个用例观测：
  - `healthy_control`：HTTP 200，列出 `core_v1`+`legacy_v0`，catalog/state 未变；
  - `scope_control`：HTTP 200，仅列出 `legacy_v0`，未变；
  - `legacy_profile_mismatch`：HTTP 200，列出 `core_v1`（不一致行被跳过），未变；
  - `core_locator_profile_mismatch`：HTTP 200，列出 `core_v1`，未变。

结论：我用值守自己的探针在其绑定的候选 head 上**复现了他们的 4/4 通过**，说明
「目录解析失败 → 列表跳过」与「审计失败 → 仍 409」的隔离在真实 HTTP 上成立。

## 边界与未做

- 我随后又提交了 `4f6cbe3`（比较失败落盘）与 `1fda02b`（取消证据失败落盘），改动了
  `scripts/exit22b_page.cjs`、`scripts/exit22-replay-observation.cjs`、
  `scripts/exit22-restart-evidence.cjs`、`tests/exit22-replay-observation.test.ts`；
  值守的 replay 探针以其 17 输入摘要绑定 head，**不能在未重签 manifest 的情况下**对我的新 head 直接复跑，
  故本轮未伪称「按其探针复验了新 head」。
- 我给这两处补了等价单元/切片测试（exit22 共 323 项全绿），但它们**不等于**值守的独立复验。
- 历史 117 B 前快照的根因仍未证实；第 4/5 项仍不成立。
