# 048 模型接入设计交付

2026-11-03；实际执行者：Codex（外部工程代理）。范围：documentation。

用户要求设计真实可用且不低于OpenCode/Hermes的大模型接入，不交付模拟产品。本次核查GitHub最新`dev`，识别Go账号/模型展示没有接入AU推理、非流式传输、原生推理内容回放缺失等问题，形成正式架构与开发清单。

## 固定依据

- UNION运行时代码：`63d90f6b6bc4189daa8a33b74d984823313a33c0`；提交时同步`54f7925b9d5f7f32015f795e3431f05be505f704`新增044方案，保留原U-060，设计任务顺延U-061、完整实施顺延U-062。
- OpenCode：`805a42ffaa56b29a88baef87c7567f1ab9a40a8f`；源码`packages/ai/package.json`版本2.2.5，包含workspace依赖。
- Hermes：`f0d94882e89ab8d4098b5bb2f166adfb9ee0a0ab`。

读取UNION配置、协议、Harness、订阅、当前管理状态及043/047记录；核对上游单次stream/loop、模型解析、OpenCode/ChatGPT认证插件和Hermes凭据池/回退说明。来源固定链接在架构文档末尾。

## 交付

- [正式架构](../../docs/MODEL_ACCESS_ARCHITECTURE.md)：内核复用、真实订阅路由、AU授权、流式/原生状态、长任务、恢复、成本及对标要求。
- [048规格](../../specs/048-production-model-access/spec.md)、[实施计划](../../specs/048-production-model-access/plan.md)、[执行清单](../../specs/048-production-model-access/tasks.md)。
- U-061记设计交付；U-062列为待实施。不关闭U-002或提升任何真实运行成熟度。

## 核查与状态

本批为文档和主账修改，不修改运行时代码、不触发模型调用或部署。按本轮“不做测试/模拟/仿真”的要求，不新增或运行供应商替身、模拟业务或回归测试；仅核查文档路径、固定来源、管理JSON与生成视图一致性。没有将既有测试数量列为本次完成证据。

当前结果是可执行设计；`union-modeld`、内部v1接口和账号到AU采用命令均属于U-062待实现内容。对标与延迟数值是交付要求，不是已经取得的运行结果。
