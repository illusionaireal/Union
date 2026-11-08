# U-086：原取消送达事实的重放与完整性修复

2026-11-09，codex-home 当前单一值守实施会话；实际在线成员
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`。#40 评论157冻结协助范围，
原owner DSH/progress/WIP和父#22真实出口保留。#60/U106已由PR39采用，
本轮没有重复实施。输入是作者 `a8c7280` 和页面 `915cc15`，组合提交
`66c97a8`；作者原送达合同及本值守的新页面访问修复均保留。

按[冻结合同](delivery-recovery-fix-contract.md)，GovernanceStore现在在
同一读取快照校验并合并原送达观察。首次POST、同ID同输入POST重放、原GET
和重启GET使用同一投影；外部发送仍在意图提交后、AU写锁外。原命令/审计
不重写，观察不能覆盖既有观察，缺失观察保持null而不重发。

校验包括原观察摘要、命令ID、原主体、成功自动取消回执和严格字段类型。
其他主体仍403、变更参数仍409；损坏或错绑观察不能冒充不存在并返回200。
读取不创建表，也不再另开写事务。保持schema和模型预约，不改变真实计量。

严格TDD及历史：

- 在未改产品的组合上恢复原POST重放断言，并增加8项HTTP/SQLite用例。
  9个用例中7个失败、2个对照通过；含子例共9个断言失败和1个产品连接
  中断错误（非法观察列表导致未处理AttributeError）。初两轮还出现夹具
  prepare命名覆盖和缺少辅助方法，另存为夹具错误，没有算成产品RED。
- 最小修复后9项全部通过，覆盖摘要/主体/结构/命令类型、原观察不可覆盖、
  并发写者存在时原GET仍可读取、无观察表兼容、原身份/参数边界和重启重放。
- 未修改的原六项送达探针6/6通过，原两个恢复反例2/2通过；旧aa82962的
  两项FAIL保留在[原评审](delivery-observation-review.md)，不改写历史。
- 实际Chrome/Core HTTP/SQLite正常15项、丢取消POST响应16项通过。每种
  模式1次回环模型替身请求、1次取消，原GET/刷新/重启和未知预约均核对。
  真实计费模型调用0，页面沿用915cc15产品字节，没有新增推理循环。

最终全量Python **792项、9跳过、0失败（501.666s）**；npm check通过，
包含335前端、37管理和9动作安全检查。交付历史追加后重建生成视图，37项
管理检查再次通过；没有用本地历史改写在线状态。受测源码blob及私有日志摘要见
[验证记录](delivery-recovery-fix-verification.json)。公开证据仅含合成夹具、
摘要和检查结论，没有私有运行日志/地址/凭据。

复现：固定项目Python运行 `-m unittest tests.test_cancel_delivery_observation
tests.test_core_work.CoreWorkTests.test_a_cancel_intent_receipt_survives_a_console_restart -v`；
原探针分别为 `python evidence/U-086/cancel-delivery-probes.py .` 和
`python evidence/U-086/delivery-observation-probes.py .`。实际浏览器沿用
`node scripts/u086-cancel-recovery-browser.cjs`，第二次显式设置
`UNION_U086_LOSE_CANCEL=1`；两次分别使用独立证据目录。

本轮是实施者自测，不能作为对自己页面/权限/持久恢复修改的独立批准。
PR43保持草稿并指向作者分支；另一工程角色须复核最终head，当前head CI
通过后才有采用条件。#40/父#22真实中断和业务验收未完成。NAS原服务未切换，
未迁移真实数据、追加真实模型请求或开启持续业务。
