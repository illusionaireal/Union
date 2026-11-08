# U-106 / #60：Core 原 AI 成果采用与交付候选

2026-11-09，基线 `rewrite/charter-v1@3e1071b`，分支
`codex/u106-core-result-delivery`。实施 actor：当前单一 Codex 值守会话；
在线成员 codex-home / `c18f0d21-1d63-4e37-af3e-2dbb78d75995`。
fresh revision439 确认#60无人负责、依赖完成，统一适配器HTTP200认领v2→v3；
范围与复评见评论118/121。父#22原owner和真实验收保持。

实际 Core `/tasks` 可采用自动 loop 产生的原候选，再交付同一成果。采用治理
资格与模型连接资格分离，停用连接仍能治理处理旧成果。原请求按
principal/service/AU/kind/Work/result 隔离保存，保留 U105 旧登记键；采用后
adopted、交付后delivered仍能刷新并GET原回执。下载绑定原Work/result，服务端
核对摘要，页面展示原来源。未开放手工正文、结束执行、预约或结算控件。

HTTP闭环额外发现原loop结束后attempt仍running，导致交付必被拒绝。先补
[冻结合同](../../specs/053-union-rewrite/s03-result-delivery-contract.md)，
观察独立RED，再在当前授权的采用事务内依据原loop/最后step的持久完成回执
关闭原attempt为stopped。缺失回执、未知调用、后续attempt均保持，Work不提前
完成，预算不释放；旧规则和GovernanceStore单一写入者不变。复评4–6h，仍是
一个可独立验收闭环，未按技术层拆分。

验证与失败历史：

- 初始15 DOM全部RED（实际入口缺失），2 HTTP RED（资格未投影、错Work下载
  返回200）。最小GREEN后58相关DOM通过；类型检查发现新增测试的mock回执
  类型不完整，修复测试类型，不算产品RED。
- 闭环原尝试未结束的HTTP RED，随后独立attempt关闭反例RED；新9项HTTP与
  原工作/派发/登记共72项通过。实际HTTP、SQLite、重启、原ID重放/查询、
  事务失败、失权/旧版本、停用模型与无新增派发均覆盖。
- 迟到GET失败覆盖已确认采用：1 RED /19通过→GREEN。已确认POST后迟到
  401/403、主体/服务变化仍清除内容，普通传输失败不覆盖事实。确认拒绝后
  无法重新核对的1 RED→显式重新核对，unknown不能据此重放。
- 实际Chrome首轮在390px长摘要溢出失败；局部换行修复后16项通过。
  两次POST分别已落盘后丢失响应；刷新保留原采用/交付GET，真实浏览器下载
  与HTTP正文/来源/摘要一致，三宽度及换主体清除通过。
  每次fixture只有2次明确fake模型调用，页面操作POST2，真实模型调用0。
  [浏览器结果](browser-checks.json)。
- 原Core路由测试仍断言旧无Work范围的下载URL，实际失败后更新为含work_id，
  保留浏览零写入与手工控件禁止断言。早期错误及私有日志哈希保留在
  [验证记录](verification.json)；完整npm/Python结果也在该记录。

最终本地验证：Python全量782项、9跳过、0失败（497.048秒）；npm check含
315前端、37管理、9动作安全通过；真实Chrome16项通过。前台评论119/120的
两个初版缺口已在本候选处理，仍需前台绑定最终head重新独立复验。

另一工程角色的权限/身份/原loop证据复核与准确head全部CI仍为采用条件；本
实施会话没有自行批准。前台负责独立复核和合入。未切换NAS业务、迁移数据、
增加真实推理或启动持续业务；#39/#40和父#22真实出口未完成。

前台后续已绑定最终产品源码 `702fd8718d817a61f8e57fdeef05c73b4ef01571`
完成独立复核，20 HTTP、86相关DOM、23实际Chrome通过。上述“仍需复验”
保留为实施交付时点；详情、失败分类及可运行探针见
[前台复核](foreground-review.md)和[精确源码/日志记录](foreground-review.json)。
最终head CI、合并回读与在线本卡验收仍分别记录，不升级父卡真实证据。
