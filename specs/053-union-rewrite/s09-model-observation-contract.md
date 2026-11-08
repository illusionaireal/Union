# U-097 / #51：V1 原模型请求观测合同

2026-11-09，编码前冻结；基线 `cbdbb552`。上级 #28 保留原 owner、blocked
与真实 profile 验收。一个 4–8h 的受控页面/HTTP 结果，不新增模型调用、
执行循环、授权写入或存储迁移。对应 D-01/D-04、A-01/A-03/A-04、R-05。

## 读取、身份与事实所有者

- `GET /api/v1/models/events?organization_id=…&check_id=…&attempt_id=…&after=0`
  只读 S02 原 `model_attempts.result.events`。既有 ModelCheckRunner 是事件收集者，
  GovernanceStore 是唯一持久写入者；GET 不运行 runner、不 POST、不补采或续跑。
- 未采用的部分正文比现有完成记录更敏感：本入口仅当前 AU governor 可读。
  原 principal、平台管理员、提名人、普通成员或同名 AU 不因此取得权限。
  登录 token 与 AU 在本地读取边界重验；modeld 当前原 grant/AU/model/revision
  GET 在锁外核对，返回后重新核对 token、治理角色和连接版本。grant 不可用拒绝
  内容，已撤销或修订返回403。当前连接需启用且仍对应原 check 的连接版本。
  治理的历史读取资格与执行/采用资格分别处理；本查询从不采用结果或执行工具。
- private attempt 必须属于本 check/AU，payload 摘要和已观察响应的
  id/AU/request_digest 均匹配；已知 action_authorized=false 不披露正文。
  缺失/他人记录统一403，不通过原ID猜测扩大读取。
- `protocol=core.model-events.v1`；响应带 organization_id/check_id/attempt_id、
  access.principal_id/service_instance、version、state、source=persisted_modeld_events、
  events、cursor、last_seq、has_more、events_complete、truncated。
  仅投影 text_delta 的 text 与 tool_call_complete 的已支持名称 read_document；
  不投影 native/reasoning/工具参数/原消息/错误正文/凭据或宿主位置。用量仍由原
  attempt 投影提供，不从正文或事件数量推断金额、完成或采用。

## 游标、撤权与兼容

- after 为非负整数且不得超过已保存 last_seq。每页最多500个原事件；cursor
  前进经过不公开事件，has_more 仅说明本地尚有分页。相同序号内容必须一致；
  原事件归属错配/冲突返回409，不返回部分不可信正文。过大单项正文明确截断。
- 前端按 principal/service/AU/check/attempt 隔离，仅在内存保存序号和正文；
  重复页去重、失败保留游标并显示断开，重连只 GET 原ID。刷新从0读取原历史。
  主体/AU/服务切换、401/403、身份/协议/事件错配立即清除旧正文；迟到响应
  不恢复已清除数据。每次结果展示前后核对当前 session，不能只靠旧 workspace。
  观测轮询只在展开的一个原请求上运行，收起/离页停止。终态停止自动轮询，
  可显式查询原记录；本地未采到的事件明确不可见，不能声称远端未执行。
- schema 2/3/4 读取均不迁移；没有 attempt 时不建表。legacy ModelRunStream
  保持原入口/权限。本卡不新增 S03 Work 观测、取消、长任务输入或续跑能力。
  能力声明只能升级已经取得的受控证据，真实和持续出口继续单独保留。

## 验证

先观察当前HTTP缺入口及DOM缺正文的行为RED，再最小实现。覆盖在途正文、
多页/重复页/重连/重启、零新POST/DB不变、原请求/摘要隔离、当前grant撤销、
本地角色与session并发变化、旧schema和隐私投影；实际Chrome + 本地HTTP与
明确modeld替身验证部分输出和恢复。npm check、固定Python全量、当前head CI
与另一工程角色权限复核均通过后才能采用。实施者不能自行声称独立复核。
