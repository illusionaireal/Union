# 110：步进用量归属的受控核对（排除产品侧嫌疑）

2026-11-08 23:05–23:12。真实运行（[108](../108-s03-real-exits/README.md)）里 PR32 守卫报告"原步进与观察到的模型用量不一致（×2）"。为防止把驱动问题误判成产品缺陷，我在集成 head（`86f283a`）上做了受控对照。

## 做法

`run_loop` 两回合，FakeTransport 第 1 回合返回 `read_document` 工具调用 + usage `{111, 7}`，第 2 回合返回正文 + usage `{222, 13}`；然后打印每步 usage、work 汇总、loop 回执。

## 结果

```
loop receipt usage: {'input_tokens': 333, 'output_tokens': 20}  turns: 2
steps usage: [('used', {'input_tokens': 111, 'output_tokens': 7}),
              ('used', {'input_tokens': 222, 'output_tokens': 13})]
work usage: {'input_tokens': 333, 'output_tokens': 20}
budget: {'max_calls': 4, 'reserved': 0, 'used': 2}
```

**结论：产品侧归属正确** —— 每一步记录的是该回合自己的 usage，work 与 loop 回执是两步之和（333 = 111 + 222，20 = 7 + 13），预算 used=2 与两回合一致。

因此真实运行里的"用量不一致"**不是产品按步归属的缺陷**，更可能是驱动侧比较口径问题（例如把 modeld `result.usage` 里 `cached_input_tokens` 等字段计入、或按事件累计与 `result.usage` 混用）。建议 codex-home 在 PR32 驱动里统一以 `result.usage.input_tokens/output_tokens` 为口径，并记录它对"不一致"的具体比较式。

## 边界

- 受控替身，无真实调用；本轮真实调用 0 次；
- 未改产品与测试（探针只存在于临时克隆，未提交）。
