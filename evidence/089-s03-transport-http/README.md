# 089：适配器经真实 HTTP 回环验证（U-067 / 在线 #22）

2026-11-08 07:29–07:55。网络仍不可达，无法连真实 modeld。本轮**只加测试、不改产品**：用一个真实的 HTTP 回环替身把 `ModeldWorkTransport` 的线格式跑通，验证 085 里"字段形状取自既有代码"的假设在协议层面站得住。

## 本轮验证内容（新增 `tests/test_work_transport_http.py`）

真实 `ThreadingHTTPServer` 模拟 modeld 三个端点，配一个真实的 `ModelServiceClient`（临时宿主配置 + 两份 40 字符令牌文件）：

1. **请求体**：`POST /v1/requests`；`id` 由 `work-overview#s1` 规范化为 `work-overview-s1`；`au_id`/`connection_id`/`model_id` 正确；`messages` 原样；`generation.maxOutputTokens=1024`；使用**worker 令牌**（非 admin）。
2. **成功路径**：轮询请求与事件后读取 `result.message` 与 `result.usage`，返回值与替身一致。
3. **明确拒绝**：HTTP 422 → `Rejected`（运行时不留步进）。
4. **未知**：`state=interrupted` → `ServiceError`（运行时保留预约、走 `reconcile_step`）。

## 与 TDD 的关系（如实说明）

这三项是**对既有实现的验证/特征测试**（adapter 已于 085 实现），因此**没有先观察 RED**——不是新行为。它补的是"协议层真实性"：此前只用 mock client 验证过调用序列，没有走真实 HTTP 与真实 `ModelServiceClient`（含配置解析、令牌选择、错误映射）。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `tests.test_work_transport_http` | **3 项通过**（1.5 秒） |
| 相关回归（adapter×2 / core_work / console / governance） | **89 项通过** |
| `npm run check:management` | 退出 0 |
| 真实模型调用 | **0**（替身是本地回环 HTTP） |

## 仍未验证（不得隐去）

- 真实 modeld 进程的**实际**响应仍未经此测试覆盖：替身按既有 `ModelServiceTransport` 的用法实现，若真实服务的事件/结果字段不同，测试不会发现。
- SSE/事件流的具体类型与顺序（替身返回空事件列表）。
- 网络恢复后仍需一次真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）。

## 下一步

1. 网络恢复：推 `dsh/s03-work-runtime` → PR（清单 [086](../086-s03-pr-readiness/README.md)）。
2. 启动 modeld、宿主设 `UNION_MODELD_CONFIG` → 真实有界验收；若与替身协议不符，本测试即为对照基线。
