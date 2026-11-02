# 043 登录与模型接入独立权限/费用复核

2026-11-02。独立工程角色：`final_security_review`。实施者为主工程代理；复核者只读源码并独立运行测试和额外复现，没有编辑源码。

结论：在既定本地 / 受信HTTPS代理边界内，可受控采用。最终52项身份、HTTP、凭据、导入、路由、费用、上下文及原生协议测试通过；多模态增量及相关组56项通过。

另行复现：同一备用预约并发恰一次成功一次拒绝，累计占用2；最新revision停用后旧捕获对象不能派发；受限board不能访问其他AU；无需认证清除旧key；主401→备用500的未知回执指向备用；跨AU媒体提交拒绝且目标库不改变；PDF编码的备用缓存密钥解码扫描后拒绝；普通工作包不新增事件读取。

修复后采用的边界包括：首次受信建户、密码/恢复摘要事务CAS、会话哈希持久化及撤销；宿主凭据仅平台管理员授权给当前AU；导入不携带引用/密钥且事务化；严格指定目标、失效绑定拒绝、预约前冻结角色元数据、全缓存密钥检查；备用请求额外计入资源及单次额度；未知不回退且不重放；按原连接版本重算整数费用、期末凭证幂等且不改原调用。

复核日志见 [独立组](../../evidence/043-usable-model-access/validation/independent-final-review.log)与[媒体增量](../../evidence/043-usable-model-access/validation/independent-media-review.log)。本次不证明真实TLS部署、实际订阅、真实供应商模型权限或031整体产品对齐通过。

最终关联源码SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| identity.py | b33a78d5c8386f86fc89c705515c6da9db882bdc4ebe7bd856b8158812223eb3 |
| model_api.py | f0e0720d24d4c1ec53432076aed93d93c5956c7448375ff8b5b0a3e1830e395d |
| model_media.py | 8d960b30e134481062ab0207a2f76d52438804c6d5b686a9090fde65d0b21ee0 |
| model_portability.py | 42dd65e9e47f342c284ee8ff4843201818de8e98d9dc2d623665aa5e052bd48b |
| model_billing.py | be52409799d8c78a765580bd91df8ff6fc05cf5666eb787fe45df6fc2a4b98e8 |
| model_context.py | 4e6c5ca8747acdb482b56d08946671b01392b19e25131d43ee9bf0cec44127e4 |
| model_protocols.py | b349966fa7458dbf64d9e2c4cb3d4eac2556da36ccbccc1d951c421a8f117d09 |
| agent_protocol.py | 31e92016d734f846ddfd7f4ba217a6d9b85f3273b5c5388f9620b6576663ee52 |
| console.py | eb47fed572326c523ef72ba75a3aff58f6d8c9494789f8c1b255ab30396f95f4 |
| engine.py | 0ad73d708d877fef5bbc0055a908752018f2cc1c59329c22fe88285a5a35707a |
| runner.py | d9f424d381f91d9936ed1289f42f5e16bb27e437af1afb308141088b73f485b9 |
| harness.py | d898829cc8cfab609bcf32a366324555f86dc29294d469410de8b382c314fd18 |
| server.py | f25758e13353f73ad8536b3746b546453abbdac087423efc378d9994af153da9 |
