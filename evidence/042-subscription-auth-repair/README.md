# U-046 真实订阅接入故障修复

2026-11-01，NAS dev基线1b21b87。用户反馈Go没有API Key、ChatGPT链接打不开。本轮由外部工程代理执行，不计组织自主改进。

## 原因及修复

- OpenCode官方v2支持Console账号设备授权，维护者答复Go用户应登录opencode并选已有Go订阅工作区。新版个人密钥在Account/Personal API keys，服务账号与个人权益不同。旧实现只提供v1的Go Key输入，与用户实际入口不符。/models现以“连接OpenCode Go账号”为默认，个人Key在可选折叠项。
- 用户原ChatGPT请求未收到URL，v1服务唯一对应日志为09:18:42.485Z的静态“Failed to initiate device authorization”。NAS直连auth.openai.com/codex/device及设备端点GET403；此诊断不宣称所有网络路径修复或精确归因为账号设置。
- 使用固定官方@opencode/cli2.2.5的原生integration API。Go device；ChatGPT chatgpt-token-sharing。原生负责PKCE/state/nonce/JWKS和凭据保存，平台不自己交换token。
- ChatGPT浏览器最终回到用户电脑127.0.0.1，远端无法接收。页面遮挡输入最终回调地址，同发起者会话、原attempt、精确server-held loopback目标及state才转交；从保存目标重建URL，不带Basic、不代理、不跟随重定向。首次动态客户端的issued client_id由官方原生实现验证JWT audience/nonce，不与dynamic_agent_client占位符误比较。
- 回调预约先持久化，只存HMAC摘要，不存原始回调code/URL；换请求ID也不重放。仅同原生attempt明确complete/failed/expired可用GET核对transport unknown，404/网络异常保留未知。重启不恢复或重发授权；只报告原attempt查询失败被拒绝，不承诺所有未来原生版本的重启行为。
- 各供应商pending独立，旧ChatGPT未知不再阻塞Go；跨session清空并拒迟到结果，授权URL/设备信息仅原session。

## 实际验证

- npm run check通过：管理/历史/Node、TypeScript、37项前端、构建。最后仅表单class/CSS调整另行成功构建；主账最终渲染后重跑完整check。
- Python完整298项通过（77.524秒），含8项新增原生认证边界；独立复核另以CompatConsole运行同8项通过。测试覆盖Go无Key、同owner、SSRF/状态/重复参数/目标、单次预约/新ID防重放、重启、无Basic/代理/重定向、错误脱敏、明确同attempt终态只GET核对。
- 固定native后端真实start probe：Go和ChatGPT均authorizing且生成官方URL；Go无需key，ChatGPT带远程回调提示。仅取消本次测试attempt并GET404确认，不取消用户流程；真实账号未登录，模型0。首次探测因错误挂载root0600环境文件在客户端读取阶段失败，无外部请求；改用现有uid10001私有副本后通过，不是重放未知供应商请求。
- 实际HTTPS React浏览器11项：后端真实可用、旧诊断流程不阻塞；Go/ChatGPT/回调按钮流程使用明确标记的受控替身，密钥不持久化、每动作一次、320px无溢出；实际Secure HttpOnly cookie、Origin403、匿名401、无JS错误。受控截图标模拟，不将其写成供应商真实登录。
- 初次手工增量构建用了uid10001，被uid10002的Vite临时目录拒写；改用既有validator身份10002:10001后构建通过，未扩大权限。首次升级脚本使用NAS Python3.8没有的Path.is_relative_to，在停止服务前失败；改为commonpath后采用，不改系统Python。

## 原未知请求的人工诊断

仅精确5ccdee89-d427-4324-a356-e894324d065e / authorize_chatgpt / 09:18:41.380852Z：原服务仍存活、3基础线程无callback worker、原回执无URL/说明，唯一v1日志+1.104秒报告初始化失败。独立复核同意一次人工诊断收口。原回执字节、SHA和日志SHA/进程/操作者/时间留宿主0700目录、0600文件；事务保留previous_status=unknown，status=failed，source=operator_start_failure_diagnosis。没有自动新建、取消或重派请求，也不声称供应商未处理任何请求。私有材料不入Git。

## 部署和限制

正式入口仍 https://192.168.1.29:18766/models 。账号服务4097仅loopback+Basic、非root、只读根、cap-drop、独立0700home，runtime固定2.2.5只读挂载；原4096用于可选Key，均非公开通用代理。前端更新保留私有数据库，旧前端停止并改名保留，重建需新一次性会话链接；没有修改群晖生产代理。

官方Go账号/ChatGPT页面由用户自行完成；最终token交换、订阅额度与模型可用尚未验收。NAS旧认证地址403仍是已知诊断，不能从新URL生成推断后半段网络通过。新服务自签证书指纹沿用041。未把凭据发给组织或调度器，模型调用0，原公司/原沙箱阻塞/U-044及max_calls=0保持。

来源：
- https://opencode.ai/v2/docs/console/api/
- https://github.com/anomalyco/opencode/issues/50885
- https://github.com/anomalyco/opencode/blob/v2.2.5/packages/core/src/plugin/provider/opencode.ts
- https://github.com/anomalyco/opencode/blob/v2.2.5/packages/core/src/plugin/provider/chatgpt.ts
- https://learn.chatgpt.com/docs/auth?surface=cli
