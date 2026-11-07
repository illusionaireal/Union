# 090：端到端链路验证（API → 自动步进 → 真实 HTTP 通道 → 工具 → 候选成果）

2026-11-08 07:44–08:15。网络仍不可达，无法连真实 modeld。本轮**只加测试**，把整条自动执行链在本机真实跑通：真实 HTTP API → `run_step` → 真实 `ModelServiceClient` 连本地 modeld 替身 → 授权目录内的工具执行 → 回执与候选成果。

## 验证内容（`tests/test_core_work_http.py`）

流程：准备 AU（`saved` + 采用默认连接）→ 允许 `read_document` → 宿主登记 `project-docs` 目录 → `start_work` → `start_attempt` → `run_step`。

断言：

1. **工具回合**：替身返回 `tool_calls=[read_document(nested/a.md)]` → 回执 `tool_calls=1`；卡片上出现工具回执（`tool=read_document`）、步进 `used`、`usage={input:5,output:2}`、`cost_status=unknown`；替身记录到 `POST /v1/requests`。
2. **成果回合**：替身返回正文 → 回执 `result=true`；卡片上出现 1 条 `candidate` 成果。
3. 全程真实 HTTP（`ThreadingHTTPServer` 替身 + 真实 `ModelServiceClient` 与令牌文件），只有模型服务是替身。

## 与 TDD 的关系（如实说明）

这是**对既有实现的端到端验证**（产品代码在 079–088 已交付），不是新行为，因此没有先观察 RED。它补的是"整条链路能一起跑通"——此前只有单元级替身注入（`FakeTransport`）与适配器线格式测试。

调试中修掉三处**测试自身**问题（产品未改）：
1. 子类方法 `prepare` 覆盖了基类创建 AU 的 `prepare()` → 改名 `prepare_work()` 并先调基类；
2. `self.server` 与基类 Console 服务端属性冲突 → 改 `self.double`；
3. 替身把 `au_id` 写死 `au-1`，导致"模型服务回执范围不匹配" → 替身改为回显请求里的 `au_id`。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `test_core_work_http` + 适配器两组 | **11 项通过**（端到端 1 + HTTP 适配器 3 + 单元适配器 7） |
| 相关回归（work×2 / adapter×2 / console / governance / documents / workspace） | 见 `regression.txt` |
| `npm run check:management` | 退出 0 |
| 真实模型调用 | **0**（模型服务为本地替身） |

## 仍未验证

- 真实 modeld 进程；真实供应商；真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）。
- 替身不模拟 SSE 事件内容（返回空事件列表），真实流式行为仍待验。

## 下一步

网络恢复：推 `dsh/s03-work-runtime` → PR（[086](../086-s03-pr-readiness/README.md)）→ 启动 modeld 做真实有界验收；本测试可作为"链路本身没问题"的对照基线。
