# 订阅登录修复：独立授权复核

日期：2026-11-01。复核者：`subscription_security_review`。范围仅为本批 `subscriptions.py`、`test_subscriptions.py`、`SubscriptionConnections.tsx`、`SubscriptionConnections.test.tsx` 与特定操作脚本 `close_old_attempt.py`；未修改实现或用户原有变更。

## 结论

通过本批**受控采用**复核：Go 使用官方原生 Console 设备授权，ChatGPT 使用固定 OpenCode v2.2.5 的原生浏览器授权；AI-UNION 提供入口、状态及严格限制的单次回调转交。此前 v1 的实际发起失败不再被替身测试掩盖。

这不表示用户真实账号已完成授权、NAS 后续令牌交换成功、Go 权益或 Astra/Sol 型号可用。模型调用仍为 0，组织绑定、执行与自动调度未由本次认证修复自动启用。

## 关键代码核查

- 继续要求显式全局平台管理员；发起者会话拥有授权 URL、设备码与回调入口，其他管理员仅可读脱敏摘要。前端按 session scope 分区，并拒绝旧异步响应写入新会话。
- 原生后端固定 loopback 4097，Basic 凭据留在宿主私有文件；客户端不能指定后端地址、原生方法或任意回调目标。原 v1 兼容行为仅在未配置原生后端时保留。
- ChatGPT 回调严格匹配服务端保存的 loopback 目标、端口、路径及 state，拒绝额外/重复/空参数、userinfo、fragment 和错误会话。只允许 `code/state/client_id` 单值参数；由服务端保存目标重建转交 URL，不直接访问用户粘贴的 URL。
- 转交之前查询原 native attempt；404、网络未知或非 pending 状态不转交。这不是对任意服务重启、任意外部状态恢复的全面保证。原生 attempt ID 与用户请求关联，不自行重建旧 attempt。
- 回调请求在外部调用前持久预约，同 intent 的 submitted 标志阻止换 ID 重放；相同请求 ID 改参数也被拒绝。原始回调 URL/code 不进入 AI-UNION 回执、日志或浏览器持久存储，输入在提交后清空。原生关联、目标与 state 保存在私有记录中。
- 回调转交不发送后端 Basic 凭据，不使用环境代理，不跟随重定向。失败保留未知；只有同一原生 attempt 的明确 complete/failed/expired 观察才能按审计字段收口未知，并且仅执行 GET，不重放回调。旧 unknown 不被静默重派或清除。

## 原生 client_id 合同

已独立读取 [OpenCode v2.2.5 官方 ChatGPT provider 源码](https://raw.githubusercontent.com/anomalyco/opencode/v2.2.5/packages/core/src/plugin/provider/chatgpt.ts)。首次请求的注册占位 client ID 与首次回调返回的新 issued client ID 不同，因此不能要求回调值等于初始占位值。保留单值 client_id 转给固定原生 provider 是必要合同；原生实现负责重授权 ID 一致性、PKCE、state、nonce、issuer、签名及 JWT audience 检查。AI-UNION 不自行信任该参数或替代原生令牌验证。

## 独立执行与现场回执

独立运行新增 `NativeSubscriptionTests` **8 项，全部通过**：Go 无密钥设备登录、ChatGPT 原生方法与会话绑定、回调 SSRF/重复参数/state/目标拒绝、终态或异常 attempt 不转交、重启保留未知、脱敏、无 Basic/代理/重定向，以及同 attempt 明确终态仅用 GET 收口未知。

本机 Console 早于当前开发基线，独立运行使用仅补平台权限授予参数的 CompatConsole 夹具，实际执行新版订阅模块；不是远端完整集成回归。前端新增测试源码覆盖无密钥入口、清空回调输入、不持久保存授权码、跨会话迟到结果及不同 provider 阻塞隔离；本复核未冒称独立重跑这些前端测试。

实施者现场回执：原生 Go/ChatGPT 发起探测均得到 authorizing、官方地址及对应设备码/回调要求；仅取消本轮测试 attempt ID，并经 GET 404 核对。未完成真实用户授权。原先一次私有配置文件权限错误导致的失败未产生 native 请求，修正私有副本权限后才取得上述发起回执。NAS 完整回归先前 297 项通过，最终 298 项当时尚在运行，最终数量与退出码以本轮验证清单为准，不提前计为通过。

## 原失败尝试的特定人工诊断

已审阅 `close_old_attempt.py`，同意只收口精确 ID `5ccdee89-d427-4324-a356-e894324d065e` 的旧 v1 发起失败。脚本校验 action、created_at、unknown、无授权 URL/说明，核对仍运行的原 v1 实例、线程情况及唯一匹配的静态发起错误时间；先私有保存原回执字节、哈希和诊断审计，再事务写 failed、previous_status=unknown 及人工诊断来源/时间。

此结论是“没有取得可继续的本地授权流程”，不是证明供应商从未处理请求。没有取消、重新授权、退款或自动派发。现场私有日志及原记录由实施者核对，本复核者审阅脚本并批准该精确诊断操作，未执行生产库更新或读取用户凭据。不得把此脚本泛化为按时间相关性自动关闭任意 unknown 的规则。

## 保留边界

实际登录仍需用户在官方页面完成授权并在 AI-UNION 页面提交短期回调；不得将回调地址、cookie 或认证文件发到聊天。NAS 此前对旧设备授权端点直接返回 403，新浏览器授权能发起并不证明后续令牌交换网络已经通过。真实登录、额度、路由、组织执行和长期恢复须分别留真实回执。
