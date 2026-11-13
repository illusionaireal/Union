# U-106：Core 原 AI 成果采用与交付（编码前冻结）

> 2026-11-13交互替换：本文件保留该次工程实现与身份、当前授权/版本、原请求、预约及unknown恢复保障。其旧Core路由、分步手工推动或legacy界面保留要求由[U-110完整体验](../../docs/product-design.md)替代。U-113须先冻结服务端持久工作意图与适用采用权限，再改对应旧交互/断言；不能只在浏览器自动串POST或删安全测试。新实现未验收前不得把本文历史工程成功称为新旅程已完成。

2026-11-09，基线 `3e1071b`，在线 #60 / 22-E，上级 #22；认领 v2→v3。
实施 actor 为当前单一 Codex 值守会话，在线成员 codex-home。源码复评仍为
2–4h、一个可独立验收结果，不拆分。依据 PRD F03/F05/F11、Chapter D-03/D-04、
R-01/R-02、ADR-0004/0005/0006 和 U105 原命令合同。

- 实际 Core `/tasks` 对既有自动执行候选提供采用、再交付操作，显示原成果
  ID、摘要、来源、采用/交付状态及下载。复用 `adopt_result/deliver_work`，
  不开放手工成果正文、结束执行、预约/结算控件，不新建执行循环。
- `access.can_manage_results` 独立于 `can_start`：当前有效治理主体可治理处理
  已有成果，默认模型连接停用不撤销此资格。投影复用现有治理有效性和存活
  主体判断；实际命令仍在 GovernanceStore 的单 AU 事务内执行
  `rules.authorize/effective`、版本、成果摘要、采用状态与未结束 attempt 校验。
  不改变这些规则、schema 或原事实写入者；读取不写库、不派发模型。
- U105 `useWorkCommand` 顺序扩展：旧 start_work sessionStorage 键与引用保持；
  采用/交付各自以 principal/service/AU/kind/Work/result 隔离存储。只存原 ID、
  base_version、成果 ID/sha256 等身份，不存正文/来源材料/凭据。
  POST 前先存原引用，失败不提交；重复点击同步拦截。未知只查原命令，
  不换 ID 重放。不同成果、工作、命令不得覆盖恢复引用。
  原回执经重新验证为 rejected 后，可显式“重新核对”并按最新资格发起新动作；
  保留旧 ID 历史，unknown 和仅存在浏览器的完成提示都不能解锁新动作。
- 新动作前重验 session、工作投影的协议/主体/AU、治理资格、版本和原成果
  ID/摘要/状态，交付还核对无 running attempt；最后重验 session。
  POST/GET 接纳检查原 command/kind/AU/base_version/actor/version/status；
  采用成功必须匹配原 result.id/sha256/adopted，交付成功匹配 work_id/result_id
  和 delivered。接纳后重验当前 session/AU读取/session。
- 新动作资格与原请求读取分开。采用后结果变 adopted、交付后 Work 变 delivered，
  原恢复组件仍挂载，刷新后仍可 GET。当前401/403、主体/服务/AU变化清除旧内容；
  回执单独403先核对当前AU读取。普通迟到传输错误不覆盖已确认事实。
- 下载继续服务端实时校验摘要；新增可选 work_id 范围并返回 work_id，当前
  页面链接携带原 Work/result。旧仅 AU/result 的唯一匹配仍兼容；若同 AU
  不同工作存在同名结果，拒绝歧义，不能误下载另一成果。
- HTTP/SQLite 与实际Chrome通过现有 loop + 明确替身生成候选，记录替身调用，
  采用/交付/重开/查询不增加调用。覆盖停连接、失权/旧版本、响应丢失、
  重启、原回执、摘要/来源/下载一致和事务失败；DOM覆盖身份错配和迟到。
  严格真实 RED→最小 GREEN，全量 npm/Python、当前 head CI、另一工程角色
  权限/身份复核后采用。本实施会话不自称独立复核，不完成父卡真实验收。

## HTTP RED 后的范围复评（实施该增量前）

完整自动 loop 产出成果后仍留下 running attempt，正常采用之后交付被既有
未结束约束拒绝（实测 HTTP200/rejected）。不撤掉交付约束，也不添加手工结束控件。
采用同一 AU 事务内允许依据原持久事实关闭该成果的原 attempt：原成果 ID 须
匹配既有生成规则所关联的原 loop 最后一个已用 step（不改写旧来源列表），
该 step 及原 loop 的完整 succeeded/result 回执须存在，
attempt 仍 running 且全部步进已结算。关闭只表示该轮停止（outcome=stopped，
理由含原 loop ID），不宣称 Work 已交付。缺失/unknown 回执、未决步进或另一
attempt 均不关闭。采用当前身份/治理/版本/摘要校验和回滚仍适用。
不读时修复、不重放、不改变旧回执或模型事实；历史已完成 loop 可在显式采用时
使用同一依据。范围复评为 4–6h，仍是本卡一个实际可交付闭环，不拆横向子项。
