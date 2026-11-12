# U-086 / #40：PR 描述（供协调者代开 PR 时直接使用）

分支：`dsh/u086-page-cancel`　交付 head：`e7b1b0c`（代码等同 `dfd4dff`，其后仅证据提交）
基准集成：`rewrite/charter-v1` = `d27d543`

## 建议 PR 标题

`U-086: 真实中断后查询原请求并重开同一工作（驱动诊断 + 会话修复）`

## 摘要

1. **会话修复（产品面，已被值守独立复验）**：`ai_union/console.py` 与
   `ai_union/application/creation.py` 区分「目录解析失败」与「创建审计失败」，
   使单个不一致 catalog 条目不再让整个 `/api/session` 409；与候选 `5545d4f` 逐字节相同。
2. **取消证据诊断**：四路 GET 的 route/status 在失败时保留（非 200 与**后续严格校验拒绝**两条路径），
   网络/JSON 中断产出 `transport_error` / `unknown_shape` 结构化诊断。
3. **取消三事实分列**：新增 `cancel-facts.json`（`local_acceptance` / `modeld_settlement` /
   `remote_fact` 恒 unknown / `reservation` 未知为 null）。
4. **重放观测**：三态记录器 + 比较失败记录；记录与比较摘要显式标注 `dispatch_count_unknown`
   与 `identity_equality_only`，未知派发计数一律 `null`。

## 范围

相对集成 **32 文件**（产品 2 + 驱动 5 + 测试 8 + 证据/文档 17），无密钥、无数据库、无私有日志、
无 `*_Conflict*`；`git diff 5545d4f..HEAD -- ai_union/` 为空。

## 验证（head `bd09ab1` / `e7b1b0c` 实测）

| 门禁 | 结果 |
| --- | --- |
| 全量 Python `-m unittest discover` | **Ran 834 / OK (skipped=11) / exit 0** |
| Node 全套 `npm test` | **354/354** |
| `npm run check:management` | **37/37** |
| 前端 `check:console`（tsc + build） | **29 文件 / 363 项** |
| 证据链接 | **197 相对链接 / 0 失效** |
| 值守 PR83 探针（作者自检，机械重签 manifest） | replay **5/5**、cancel-driver **6/6** |

## 复验指针

- 合同与四反例/两合法控制：[cancel-validation-diagnostics.md](cancel-validation-diagnostics.md)
- 失败归档与中断诊断：[cancel-failure-route-outcomes.md](cancel-failure-route-outcomes.md)
- 三事实分列：[cancel-evidence-attribution.md](cancel-evidence-attribution.md)
- 重放观测：[replay-no-dispatch-observation.md](replay-no-dispatch-observation.md)
- 收尾就绪度（含未闭合真实出口）：[closure-readiness-2026-11-10.md](closure-readiness-2026-11-10.md)

## 合入后仍未闭合（不得据此关闭 #40/#22）

- 历史 117 B 前快照根因未证实；一次有界真实运行仍缺（同运行前后快照与真实派发计数）。
- `remote_fact` 恒 unknown（本机无法证明远端已停）。
- 关闭判定与 CI 由值守/协调者按准确 head 确认。
