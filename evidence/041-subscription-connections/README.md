# U-045 AI-UNION前端订阅配置

2026-11-01，基线NAS dev@2bbf8df（含用户发布53dd96b快照）。用户确认没有现成工作台网址，并明确由AI-UNION自身前端配置Go/ChatGPT，不以SSH或独立OpenCode页面代替。

正式React /models增加平台订阅区：Go密钥同源提交、清空不回显；ChatGPT官方设备授权、原流程查询和显式人工核对。空组织也可配置。后台采用固定回环认证适配器，无客户端指定URL/路径/命令。宿主平台管理员才能管理；账号认证不自动绑定AU、不授予成员工具或额度、不验证模型、不启用调度。

## 验证

- npm run check通过：管理/历史/Node检查、TypeScript、34项前端和React构建。
- Python全量290项通过，76.028秒；其中11项新增订阅权限、HTTP来源、幂等、未知、核对、私有权限测试。3项组件测试包括迟到mutation不跨会话显示设备码。
- 正式HTTPS页面8项真实Chromium检查通过：空组织配置、密钥遮挡、ChatGPT入口可用、Secure HttpOnly Cookie、跨来源403、匿名401、320px无溢出、无JS错误。桌面及手机截图已审。
- 浏览器以ignoreHTTPSErrors显式放行本次自签证书，仅为测试例外；不是公网可信证书验收。证书SHA256：C1:CF:62:FE:46:9D:B5:9B:40:3D:CC:9E:8D:90:02:09:DD:F6:AE:04:01:82:74:CC:E8:6D:B8:4C:C7:F9:4E:BF。
- 新服务目录/private/console权限0700、数据库0600，秘密文件0600；固定HTTPS入口仅当前NAS LAN地址，原loopback Server不放宽。代理验证Host/Origin/SecFetch，TLS握手在线程中限流16个、超时10秒。新服务无fixture、无Codex宿主执行、未迁移或重建旧公司状态。
- 原始失败保留私有：首次构建缺Receipt.action类型、私有目录权限未预建均已修复；首次浏览器过早检查按钮、复用已消费ticket属测试时序，修正后通过，不当作产品Bug成功证据。

## 部署与访问

AI-UNION实际React工作台位于 https://192.168.1.29:18766/models 。初次由宿主生成的私有一次性管理员链接建立会话，cookie有效8小时；新链接10分钟有效，匿名页面不会自动获得管理员权限。首次浏览器有自签证书提示，须核对上述指纹后再输入真实密钥。私人访问文件不进Git。此原型尚无公共账户/多租户生产登录，不能报告公共生产托管完成。

运维源见ops/console-subscriptions。部署不修改群晖原有生产代理/证书。旧独立Web容器已停止，认证API保留回环+Basic的受信维护入口；opencode serve可能仍提供其根UI，不能宣称所有维护UI路由已关闭。CLI写入口有managed marker拦截；维护者禁止与AI-UNION同时配置同一账号，root级外部修改不在应用锁保证内。

## 结果边界

真实Go密钥没有输入，ChatGPT官方授权未实际提交，真实模型调用0；UI/后端工程通过不等于订阅权限或Astra/Sol路由已验证。用户须在本页面完成私有账号操作后再验证能力与明确资源。U-044的DSM沙箱/凭据隔离/实际双模型运行阻塞保持，原自动调度仍disabled/max_calls0。
