# 100：历史未知预约观察（真实取消与核对释放未获证明）

2026-11-08 的旧驱动记录。独立复核发现旧驱动使用固定请求 ID、未核对取消响应；这里的 `model_service_rejected` 不能证明原请求已发送或远端已取消。以下做法和日志原样保留为失败/不确定历史，不完成 #22 第 6 项，不是新增调用授权。

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

## 当前证据解释（覆盖旧结论）

- 原日志没有唯一原请求的发送、取消回执与重开不重派证据，不能推定真实中断通过。
- 旧 `released` 断言已失效：当前自动预约必须查询原请求；确认 completed 才记录 used/实际用量，否则保留预约，不能手工释放。
- 原日志 `usage: 0/0` 是没有测量时的旧投影，**不是确认零用量**。本次输入/输出 tokens 未知，费用未知；原字节保留，不用新测试补写历史。

## 边界

- 真实调用共 2 次（本次 1 次；另一次见 [099](../099-s03-real-bounded-go/README.md)），已达到用户授权上限，之后不再发起真实调用。
- 未部署、未改他人工作区；合成资料、临时 Console 根目录。
- 测试默认跳过（需 `UNION_MODELD_CONFIG` + `UNION_REAL_ACCEPTANCE=1`）。
