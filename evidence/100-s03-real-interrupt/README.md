# 100：真实中断 → 未知预约 → 核对释放（不重放）

2026-11-08。用**真实 modeld + OpenCode Go（deepseek-v4.1-flash）**验证 #22 第 6 项：「中断/未知原请求核对与重启恢复，不静默重放」。这是本卡第二次（也是最后一次授权额度内）真实调用。

## 做法

- 与他人共用同一套已就绪的 modeld（回环 63504，Bun 1.4.2 发布产物），账号 oauth 已连接。
- 创建 1 次调用额度（`max_calls=1`）的合成资料工作，`run_step` 派发后，由外部在请求建立后调用真 modeld 的 `POST /v1/requests/<id>/cancel` 制造中断。
- 断言：回执 `succeeded` + `model_outcome: unknown`；预算 `reserved=1 / used=0`；步进状态 `unknown`；随后 `reconcile_step`（`released`）释放预约，`reserved` 归零、步进变 `released`。

## 结果（`interrupt.txt` 原文）

```
interrupt: {"receipt": {"status": "succeeded", "model_outcome": "unknown",
  "message": "模型通道结果未知；已保留该次调用预约等待核对，不自动重放：model_service_rejected",
  "step": "work-real#s1"},
  "budget": {"max_calls": 1, "reserved": 1, "used": 0},
  "steps": [{"status": "unknown", "reason": "…不自动重放：model_service_rejected"}],
  "usage": {"input_tokens": 0, "output_tokens": 0}}
→ reconcile_step(released) 后：reserved=0，steps=[released]
```

## 意义

- **不静默重放**：中断后产品没有再次派发；预约保持占用，直到人/流程用 `reconcile_step` 明确核对。
- **真实服务路径**：cancel 通过 modeld 官方端点发起，说明产品对"取消/中断 = 结果未知"的处理与真实实现一致（源码核对见 [091](../091-s03-modeld-contract/README.md)：modeld 重启也会把在途请求标记 interrupted）。
- **用量诚实**：中断的这次调用没有拿到 usage，记录为 0/0 且费用 unknown，不猜测。

## 边界

- 真实调用共 2 次（本次 1 次；另一次见 [099](../099-s03-real-bounded-go/README.md)），已达到用户授权上限，之后不再发起真实调用。
- 未部署、未改他人工作区；合成资料、临时 Console 根目录。
- 测试默认跳过（需 `UNION_MODELD_CONFIG` + `UNION_REAL_ACCEPTANCE=1`）。
