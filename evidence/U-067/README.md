# U-067 证据索引

当前采用见[前台交付记录](coordinator-adoption.md)和[五卡粒度复核](../../docs/reviews/2026-11-08-task-granularity.md)。以下候选/待复核描述保留形成时的历史范围。

- [2026-11-08：长期阻塞的验收驱动修正](acceptance-intervention/README.md)：正文/来源/原请求/取消与核对逐项验证；保留旧失败历史，不把离线通过当成真实验收。
- [2026-11-08：用量元数据误报修正](usage-metadata/README.md)：保留供应商完整证据，按逐请求的规范 token 字段核对；真实 HTTP 反例 RED/GREEN，不追加真实调用。
- [2026-11-08：同请求并发准备失败不能抢占原派发回执](preflight-receipt-race/README.md)：4 RED → 6 GREEN，迟到拒绝与真实调用事实分开；保留原预约、用量和重启幂等，待独立工程复核。
- [2026-11-08：组合候选的 V1 HTTP 夹具超时修复](core-http-fixture/README.md)：真实延迟 RED/GREEN、原 POST 一次与显式短超时；不改变产品权限或 CI 门禁。
- [2026-11-08：待审候选的组合验证](combined-integration/README.md)：PR #24/#25/#26/#27 顺序组合，schema 4 下成果与未知预约的真实浏览器验证；不是独立复核或真实模型验收。
- [2026-11-08：后续准入拒绝仍保存父循环用量回执](loop-receipt-fix/README.md)：4 个真实 RED 后最小修复，保留已发生调用、未知预约及原请求恢复；真实验收另计。
- [2026-11-08：自动派发的代码回退兼容候选](dispatch-compatibility/README.md)：事务内 schema 4、旧候选拒绝、原预约保留及跨版本探针；待当前 CI 和另一工程角色复核，不关闭真实父卡。
- [2026-11-08：modeld 完成后撤权的事实保留候选](model-observation-fix/README.md)：codex-home 协助 PR #17；严格 RED/GREEN、执行/用量与不可采用分开。原 owner 与整卡验收不变。
- 原独立评审及三个探针保存在集成分支的 [independent-review.md](https://github.com/illusionaireal/Union/blob/9fff47713bf99cfc296c079acf143502526b7acf/evidence/U-067/independent-review.md)，历史不覆盖。本次基于作者分支创建小差异候选，未把集成分支的其他改动混入。

文档、受控工程、真实集成和持续业务分别取证；此处不是运行态看板。
