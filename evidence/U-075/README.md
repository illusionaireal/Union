# U-075：用户指定 OpenCode Go 的有界验收

2026-11-08，用户提供 Go 订阅接入授权。官方 Go 文档 https://opencode.ai/docs/go/ 列出该 API 端点和 glm-5.3-flash；只读 models HTTP 200 后通过既有核心身份/治理、modeld AU grant、两阶段资料检查完成 2 次推理、1 次真实 read_document。没有假模型或假资料回执。

证据见 go-api-acceptance.json。输入 292/286，输出 38/83 tokens；每次输出上限 1024。费用金额与币种未提供，保留 unknown，不记为零。资料是本轮生成的公开合成部署清单；原资料/校验码不在首轮请求，只经工具读取进入第二轮，回答包含校验码。

编译 modeld 来自独立安装的 90 文件发布包；核心 HTTP 使用同一提交的源码。该构建的安装/升级/代码回退已有 5 项受控检查通过。重启核心后正常密码登录，原 check 与两次 attempt 保留，无新请求。配置、登录恢复信息、原请求、数据库和密钥只存宿主；一次性派发标记防止误重跑。

范围为 Go 订阅提供的 Chat Completions API profile；不据此宣称 Go 原生 OAuth/profile、S03 自主目标执行、真实业务部署或持续运行完成。原失败资料仍保留，U-075 的其他 profile 验收不能提前关闭。人工参与为用户选择资源及有界授权，非例行业务劳动。
