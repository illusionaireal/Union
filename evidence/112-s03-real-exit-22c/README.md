# 112：22-C 取消受理与未知预约保留的工程观测（**不关闭 #40**）

> 评审收窄（2026-11-08 23:59，见 [113](../113-s03-evidence-corrections/README.md)）：前台 #99 指出本证据不足以关闭 #40。

## 三类事实必须分开陈述

1. **取消受理**：`POST /v1/requests/<id>/cancel` 返回 `cancel_requested=true`（已获得）；
2. **modeld 中断**：同一请求最终 `state=interrupted`（已获得）；
3. **远端取消确认**：未获得（未验证供应商侧确实停止生成）。

## 未采集 / 未闭环（评审指出）

- 只观察到 `streaming` 状态，**未验证实际输出事件**，也未校验响应里的 AU/请求身份；
- **未在重启后**核对或重放同一命令，也没有统计“是否发生原派发之外的新派发”；
- 脚本里的 `reconcile_step(used)` 回执是 **succeeded 但拒绝记账**（命令未失败、记账未发生），早期文字把它写成“被拒”容易误读；
- 真正关闭 #40 需要：真实输出事件 + 身份校验 + 重启后同 id 核对/重放与派发计数。


2026-11-08 23:15–23:25。在集成 head `86f283a` 与真实 modeld（`deepseek-v4.1-flash`）上完成 **#22 的 22-C 项**：真实取消一次在途请求，验证「未知结果保留预约、原请求核对不记账、不重放」。

## 结果（`exit.log` 原文摘要）

```
request_id = work-a0c38d64fe1c…   ← 从产品状态读出的持久原请求 id（非硬编码）
states: connecting ×70 → streaming
cancel_reply = {"state": "streaming", "cancel_requested": true}
final = {"state": "interrupted", "cancel_requested": true}

receipt = {"status": "succeeded", "model_outcome": "unknown",
           "message": "模型通道结果未知；已保留该次调用预约等待核对，不自动重放：work_step_interrupted",
           "step": "work-cancel#s1"}
budget = {"max_calls": 1, "reserved": 1, "used": 0}
steps = ["unknown"]

reconcile_step(status=used) → receipt succeeded，消息「原模型请求仍未确认；保留预约，不重新派发」
budget 仍 {reserved: 1, used: 0}，steps 仍 ["unknown"]
```

要点：
1. **取消真的发生**：请求处于 `streaming` 时 POST cancel 得到 `cancel_requested: true`，最终 `interrupted`；
2. **产品按未知处理**：回执 succeeded + `model_outcome: unknown`，预约保留（reserved=1、used=0），步进 `unknown`；
3. **不重放**：没有二次派发；
4. **核对不记账**：`reconcile_step(used)` 被拒记账——原请求状态是 `interrupted` 而非 completed，正符合"确认完成才 used"的语义。

## 与 PR32 驱动失败的差异（为什么这里能过）

- 取消用 **worker 令牌**（admin 令牌会 402/403 → `model_service_rejected`）；
- goal 要求"逐行输出 1..600"，把生成拉长到 `streaming` 窗口内（约 70 次 20ms 轮询后进入 streaming），而不是 2 秒即完成；
- 轮询用 20ms 间隔，并在 GET 到 streaming 后立刻 POST cancel。

## 边界

- 真实调用：本轮 1 次（本次中断），均 `deepseek-v4.1-flash`、≤1024 tokens、仅合成资料；
- 脚本为一次性证据工具，未修改任何产品/既有测试代码；
- 未覆盖"取消后原请求最终 completed"的正向路径（那需要模型在取消前完成，属竞态；如需要可单独取证）。
