# 108：真实出口（22-B / 22-C）在集成 head 上的实测失败与根因假设

2026-11-08 22:55–23:05。在集成 `86f283a`（PR #32 合并后）用用户无限授权的 `deepseek-v4.1-flash` 跑了 PR32 重写后的两个真实驱动。**两个都失败**，但失败点是有信息量的，记录如下（供 22-B/22-C 与驱动作者使用）。

## 22-B 有界验收（`UNION_REAL_BOUNDED_ACCEPTANCE=1`）

```
receipt: succeeded「自动循环结束：模型没有给出成果，已用满本轮轮次」
turns=2, tool_calls=[list_documents, read_document], result=false, usage 935/77
budget: max_calls=2, used=2
guard problems:
 - 没有产出任何成果
 - 需要读取后第二次模型调用及候选成果，不能以单回合摘要验收
 - 原步进与观察到的模型用量不一致（×2）
 - 未证明授权资料正文及匹配工具回执进入下一轮模型
```

**观察**：两回合额度被两个工具调用用掉（先 list 后 read），没有第三次调用去产出正文。`max_calls=2` 时"读一次 + 写一次"需要模型第一回合就 read，而不是先 list。

**假设**：
1. 驱动/产品需要把"读资料"和"写成果"分配在两回合内 —— 当前 goal 没有强制"第一回合就 read_document"；把 goal 收紧到"第一步必须 read_document('brief.md')，不要先列目录"可能即可；
2. "原步进与观察到的模型用量不一致（×2）"更像**产品侧用量归属**的疑点：两回合的 step.usage 与模型事件累计对不上，值得单独立项核对（不是驱动能修的）。

## 22-C 真实中断（`UNION_REAL_INTERRUPT_ACCEPTANCE=1`）

```
request_id=work-77e9c2d2…, state=streaming, provider_output_observed=true, remote_cancellation_confirmed=false
cancel_error=unconfirmed_or_completed
AssertionError: modeld did not acknowledge the original cancellation
```

**观察**：GET 时请求仍在 `streaming`，但 `POST /v1/requests/<id>/cancel` 的响应里没有 `cancel_requested=true`——要么取消落在完成之后，要么产品/驱动用的 id 与 modeld 的受理对象不完全一致。

**假设**：
1. 取消竞态：`deepseek-v4.1-flash` 很短时间就完成，轮询到 step 再取消时已过窗口；需要更长输出或更早介入（产品侧派发后立刻可取消的钩子）；
2. 或 cancel 需要带 `cancel_requested` 的**回执确认**（modeld 返回 202 + publicRequest），驱动应重试读回而不是单次判断。

## 边界

- 真实调用：本轮 4 次（22-B 2 次 + 22-C 1 次 + 1 次失败重试），均 `deepseek-v4.1-flash`、每次 ≤1024 tokens、仅合成资料；
- 未改 `ai_union/` 或任何测试（驱动属 codex-home 的 PR32 子范围）；
- 上述均为**实测**，不是推测；根因假设已与观察到的事实分开标注。
