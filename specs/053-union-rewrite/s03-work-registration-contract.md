# U-105：Core 目标登记与原命令恢复（编码前冻结）

2026-11-09，基线 `bb5795b`，在线 #59 / 22-D，上级 #22。
当前 codex-home 认领 v3；有效工程估计 4–6h。一个可独立验收结果，
目标输入、责任/预算绑定、原请求恢复需一同交付，故不再拆分。
依据 PRD F03/F04、ADR-0004/0005/0006 与既有 S03 工作合同。

- 实际 Core `/tasks` 的空态及已有工作页提供登记入口。显式输入标题、
  目标、负责 AI 成员名称、资料引用、工具和调用上限；显示所采用的默认
  连接。只调用既有 `start_work`，不调用模型、不自动准备/运行，不开放
  手工成果正文、`finish_attempt`、预约/结算操作。单成员即可。
- 服务端仍由 GovernanceStore 在一个 AU 事务中保存 Work、Member、Binding、
  Agent Definition v1、Mandate v1、预算和命令回执。版本/连接修订、治理、
  工具和总预算校验沿用既有领域规则；无新 schema、无另一个事实写入者。
- 浏览器共享命令恢复边界绑定 principal、service instance、AU、kind、
  command ID、Work ID 与 base_version。新请求前重读 session、工作与模型
  投影，核对协议、主体/AU、当前授权、版本、原连接 ID/revision；再核对
  session。发现变化先拒绝本次提交，刷新供用户核对，不能静默换连接。
- POST 前在 sessionStorage 保存上述原身份（不保存目标/资料/正文/密钥），
  存储失败不 POST；同步在途门闩防止重复点击。原 Work/责任对象 ID 随同
  单次 payload 生成；不确定响应、刷新与重开仅 GET 原回执，不另建 Work。
  未解决引用不得被新登记替代。确认终态后才可显式登记另一项工作；保留
  历史引用与服务端原事实，绝不自动重试。
- 接纳 POST/GET 回执前验证原 command/kind/AU/base_version/actor、合法
  status/version，成功时核对 Work ID；并重验当前 session 与 AU 读取权，
  最后再验 session。合法读取但 can_start=false 时仍可查询原命令。
  当前读取/身份拒绝即清除旧内容；主体/服务/AU切换后的迟到结果不展示。
  回执单独 403 沿 U084 合同重验 AU 读取，仅说明暂不可取得，不释放原引用。
- 登记预检的 `can_start=false` 只是新登记资格不足（例如默认连接停用），
  不等同于 AU 读取权丢失。当前主体/服务及 AU 读取仍有效时，拒绝该次 POST、
  刷新资格并保留已有工作与原执行查询；实际 401/403 或身份错配仍清除旧内容。
- 复用 UI/client 与既有工作 API；#60 顺序复用本命令恢复边界，当前不实施
  采用/交付入口。legacy 路由与 U084 已交付运行合同保持。
- 先真实 DOM RED，再最小 GREEN；HTTP/SQLite 验证原回执、事务完整性、
  重开不重复及零模型调用，实际浏览器从 Core 路由登记并丢失响应/刷新。
  npm check、Python全量、当前 head CI 与另一工程角色权限/身份复核后采用。
  受控工程证据不完成 #39/#40/#22 的真实或持续验收。
