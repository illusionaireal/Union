# U-046 修复真实订阅接入
用户反馈Go没有API Key且ChatGPT链接打不开。调查官方OpenCode v2文档、维护者答复与源码：Go可Console账号设备授权；个人密钥入口Account/Personal API keys与服务账号不同。旧v1申请ChatGPT设备授权失败，NAS认证地址GET403，不能宣称网络已修复。
AI-UNION /models以Go账号登录为默认，保留个人密钥可选；ChatGPT使用官方v2 chatgpt-token-sharing浏览器授权，远程用户在同一会话粘贴最终loopback回调。native负责PKCE/state/nonce/JWKS/凭据，平台只转交一次并观察。
仅宿主平台管理员，秘密不入Git/回执/浏览器持久存储。固定4097 Basic私有backend，回调从受信目标重建、同owner/attempt/state、无Basic/无重定向、预约持久化、未知不重放；旧unknown保留显式核对。认证/模型能力/组织授权分开，模型调用0。
