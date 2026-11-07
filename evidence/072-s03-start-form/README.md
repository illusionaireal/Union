# 072：S03.1e 页面登记 AI 工作（U-067 / 在线 #22）

2026-11-08 05:54–06:15。「输入一个目标，让 AI 干活」的用户入口：现在不必再手写 API，工作页可直接登记一张 V1 工作。**仍未调用模型**，U-067 保持 `doing`。

## 本轮用户可验证结果

「AI 工作（V1）」面板顶部新增「**登记新的 AI 工作**」折叠区（仅当当前主体有开工资格时出现）：

- 字段：**工作标题**、**目标**、**资料目录引用**（宿主已登记的引用，如 `project-docs`）、**调用上限**、**允许的工具**（`read_document` / `list_documents` 复选，默认勾选 `read_document`）。
- 模型连接**自动取当前已采用的默认连接**（从 `GET /api/v1/models` 读取 `is_default && enabled`），提交时带 `connection_id` 与其 `revision`；没有默认连接时按钮禁用并提示"先去模型页保存、测试并采用一个连接"。
- 提交前校验：标题与目标必填；选了资料工具就必须填资料目录引用；工具至少一个。
- 提交走 `start_work`，工作与成员/定义/绑定/授权的标识按同一前缀自动派生（`work-<时间戳>-member/binding/mandate/definition`），服务端仍执行全部既有校验（治理激活、默认连接、章程工具、调用上限）。

## 严格 TDD 记录

| 日志 | 内容 |
| --- | --- |
| `red-start-form.txt` | 真实 RED：找不到「工作标题」标签（1 失败 / 7 通过） |
| `green-start-form.txt` | 8 项面板测试通过 |
| `frontend-check.txt` | `npm run check:console` 退出 0：**20 文件 / 202 项前端测试** + `tsc` + `vite build` |

过程中发现并修掉一个**测试基础设施缺陷**：该测试文件此前没有 `afterEach(cleanup)`，多次 `render` 累积 DOM，导致 `getByText` 命中多个旧面板（表现成"按钮禁用/文本重复"）。已补 cleanup。另外几处失败都是我的测试假设问题（默认工具已勾选却又点击导致取消、模拟值设置在渲染之后、表单标题与按钮文案重名），产品语义未因此改变。

## 所有权与边界

- `web/console/src/api/client.ts` + `types.ts`：新增 `api.coreModels(organizationId)` 与 `CoreModelConnection` / `CoreModels` 类型（只读）。
- `web/console/src/features/work/WorkPanel.tsx`：新增 `StartWorkForm`（复用既有 `send` → `api.coreWorkCommand`，带当前 `base_version`）；成功/失败提示与刷新沿用既有逻辑。
- 页面仍不提供改章程、改资源、删除成果或绕过 attempt 的入口；资料目录只接受引用标识，不接收宿主路径。

## 未完成 / 下一步

1. **S03.2e（关键阻塞）**：真实模型循环 infer → tool_call → 回执 → 二次推理 → 自动 `submit_result`；需要可用模型连接与有限额度。
2. **S03.4c**：中断恢复（服务重启后 running attempt 的核对路径）与更细的写目标互斥。
3. **S03.3f**：成果页（跨工作的成果列表与采用历史）。

因此本卡仍 `doing`。
