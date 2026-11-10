# U-075：用户指定 OpenCode Go 的有界验收

2026-11-10 Responses新增证据：[Go GPT-6 Luna资料工具往返](../U-099/README.md)、
[真实生成后取消与原请求恢复](../U-100/README.md)，共享批次实际4/6次；以及
[DeepSeek Responses协议实测与此前结论更正](deepseek-responses-research/README.md)，
另用2次DeepSeek既有授权。#52通用续接/新输入仍未完成，父卡完整出口保留。

2026-11-10 新记录：[DeepSeek V4.1 Flash 真实往返、中断、重启和浏览器验收](go-deepseek-2026-11-10/README.md)。
4次真实请求；保留未知用量/费用与原责任，修复中断原文本读取403。权限修复需独立
采用，Responses 子卡未关闭。以下 2026-11-08 GLM 验收与原失败历史保持。

2026-11-08，用户提供 Go 订阅接入授权。官方 Go 文档 https://opencode.ai/docs/go/ 列出该 API 端点和 glm-5.3-flash；只读 models HTTP 200 后通过既有核心身份/治理、modeld AU grant、两阶段资料检查完成 2 次推理、1 次真实 read_document。没有假模型或假资料回执。

证据见 go-api-acceptance.json。输入 292/286，输出 38/83 tokens；每次输出上限 1024。费用金额与币种未提供，保留 unknown，不记为零。资料是本轮生成的公开合成部署清单；原资料/校验码不在首轮请求，只经工具读取进入第二轮，回答包含校验码。

编译 modeld 来自独立安装的 90 文件发布包；核心 HTTP 使用同一提交的源码。该构建的安装/升级/代码回退已有 5 项受控检查通过。重启核心后正常密码登录，原 check 与两次 attempt 保留，无新请求。配置、登录恢复信息、原请求、数据库和密钥只存宿主；一次性派发标记防止误重跑。

范围为 Go 订阅提供的 Chat Completions API profile；不据此宣称 Go 原生 OAuth/profile、S03 自主目标执行、真实业务部署或持续运行完成。原失败资料仍保留，U-075 的其他 profile 验收不能提前关闭。人工参与为用户选择资源及有界授权，非例行业务劳动。

2026-11-10：PR73取消历史读取修复经独立工程复核与14/14当前CI已采用，merge `b4e435b`；[独立探针与采用记录](go-deepseek-2026-11-10/duty-review/README.md)。指定Go真实报告与值守受控复核分列，Responses及父卡完整验收保留。
