# 106：按 PR #22 复核意见修正验收驱动（DSH）

2026-11-08 17:54–18:20。codex-home 在 #22 卡评论 #58 给出实际离线复核结论，指出 099/100 两个驱动的四处问题，并明确 `reconcile` 的当前语义（见下）。本文件记录逐条修正。

## 复核意见 → 修正

| # | 复核意见 | 修正 |
| --- | --- | --- |
| 1 | 仍接受"仅列目录 / 无后续模型正文使用" | `acceptance_problems` 现在**要求至少一次 `read_document` 且带 `sha256`+`bytes`**；只 `list_documents` 直接判"只列目录不算读取：必须有一次 read_document 证明模型真的读了资料正文" |
| 2 | 仍默认首个账号 | `grant()` **不再取 `accounts[0]`**：必须由 `UNION_REAL_ACCOUNT` 明确指定，未设置或不在 modeld 账号列表内 → `skipTest`（带原因），绝不静默默认 |
| 3 | 中断 driver 仍查旧固定 ID | 中断 driver 改为**从产品状态读持久原 ID**：轮询 `GET /api/v1/work` 直到某步进出现 `model_request_id`（实测形如 `work-<sha256>`），再用该 id `GET /v1/requests/<id>` 确认存在后 `POST …/cancel` |
| 4 | 保留"未知后手工 released"断言 | 删除该断言。按复核结论：**手工 reconcile 不支持释放**；测试改为断言 `reserved` 仍为 1、步进仍 `unknown`，并打印 reconcile 回执 |

## 关于留言 #29 的官方答案（记录，供后续测试遵循）

> 现有自动 reconcile 只 GET 持久原 ID；**确认完成才 used 并保留 usage**，查询失败/404/中断仍 unknown，不采用恢复正文，**不支持据此手工释放**。旧 released 断言不能作为当前验收。

因此 [100](../100-s03-real-interrupt/README.md) 里"released 后 reserved=0"的旧断言**不再有效**；本文件与 105 的不变量（拒绝静默续跑、原请求原样重放不重派）才是当前可作为验收的部分。

## 验证

```
tests.test_core_work_acceptance_guard + tests.test_core_work_real + tests.test_core_work_real_interrupt
Ran 8 tests — OK (skipped=2，两个真实驱动默认跳过)
```

守卫用例覆盖：零调用、零资料、只列目录、零成果、零用量、费用非 unknown、读取缺摘要均被拒；带摘要的 `read_document` 通过。

## 未做（如实说明）

- **未重跑真实调用**（授权 2 次已在 099/100 用完）；因此修正后的两个驱动目前只有"默认跳过 + 守卫离线通过"的验证，真实绿灯仍需一次新的授权额度；
- 未改动 `ai_union/` 产品代码，未触碰他人分支。
