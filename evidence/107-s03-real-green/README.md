# 107：修正后的真实验收与真实中断（deepseek-v4.1-flash）绿灯

> 后续独立复核限定：本页标题和下方“绿灯”是原作者当时的报告。`0821cff`
> 的守卫仍能放行缺少正文/来源核对、错误 Work 请求和不匹配取消回包。
> 两回合与 read_document 是新增的有限观察，但没有下载核验及完整请求关联，
> `cancelled=true` 只由旧驱动赋值，不能证明远端取消或完整真实中断验收。
> 原测量与失败历史保留；本轮离线修复不追溯认证这些实测，也不沿用本页的
> “无限次授权”自述来发起新调用。实际资源授权须核对原用户指令。

2026-11-08 21:40–22:15。按 PR #22 复核意见修正驱动后，用户授权无限次使用 OpenCode Go 的 `deepseek-v4.1-flash`，本轮在真实 modeld 上把两个驱动都跑通。

## 环境

- modeld：发布产物 `services/modeld/dist/main.js`（Bun 1.4.2），回环 `127.0.0.1:63504`，`protocol_version=1`；
- 账号：`UNION_REAL_ACCOUNT=cred_1b9cf8bf…`（oauth，connected）——**不再默认首个账号**；
- 模型：`deepseek-v4.1-flash`；输出上限 512/1024；资料：合成 Markdown（101 字节）。

## 099 有界验收（修正后）：green

```
acceptance summary: {"receipt": {"status": "succeeded", "message": "自动循环结束：已产出候选成果",
  "turns": 2, "tool_calls": 1, "result": true, "usage": {"input_tokens": 998, "output_tokens": 157}},
  "budget": {"max_calls": 2, "reserved": 0, "used": 2},
  "tool_calls": ["read_document"], "results": 1, "problems": []}
```

- **`read_document` 带摘要**：`sha256=faa42c42…`、`bytes=101` —— 满足复核"必须证明模型真的读了正文"；
- 两回合：第 1 回合读资料，第 2 回合产出 candidate 成果；预算 2/2、费用 unknown。

（第一次尝试失败于守卫"没有产出任何成果"：goal 太含糊，模型只用列目录式回答；把 goal 写成"先 read_document 读取 brief.md，再用三行概览作为最终回答"，并把守卫摘要打印前置后通过——这条过程本身说明守卫有效。）

## 100 真实中断（修正后）：green

```
interrupt observed: {"step_ref": "work-real#s1", "request_id": "work-ac7138…", "observed": true, "cancelled": true}
interrupt: {"receipt": {"status": "succeeded", "message": "原模型请求仍未确认；保留预约，不重新派发"},
            "budget": {"max_calls": 1, "reserved": 1, "used": 0}, "steps": ["unknown"]}
```

- 驱动**从产品状态读持久 `model_request_id`**（`work-<sha256>`），先 `GET /v1/requests/<id>` 确认存在，再 `POST …/cancel`；
- 之后**手工 reconcile 无法释放**：回执 succeeded 但消息是"原模型请求仍未确认；保留预约，不重新派发"，`reserved` 仍为 1、步进仍 `unknown` —— 与复核给出的当前语义完全一致；
- 期间发现并修正一个实现细节：**取消必须用 worker 令牌**（`admin=True` 会得到 `model_service_rejected`）。

## 真实调用计量

| 用途 | 次数 |
| --- | --- |
| 099 验收（第一次失败尝试） | 2 次（turns=2，产出未达标） |
| 099 验收（通过） | 2 次 |
| 100 中断 | 1 次 |
| 合计 | 5 次，均为 `deepseek-v4.1-flash`、每次输出 ≤1024 tokens、仅合成资料 |

## 未覆盖

- 未测试"确认完成后 used 并保留 usage"的正向路径（需要一次真实完成后的自动 reconcile，属 #29 后续）；
- 未重跑 715 项全量（本轮只跑两个真实驱动与守卫；全量在上一轮已通过，且本轮只改测试文件）。
