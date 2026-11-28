# U-098 / #52 Responses 长工作续接合同

2026-11-28。输入固定为集成提交 `4d1c94611c233c3fe6b5fd80657bf2221f815ed7`，树 `94795a532740aeb8ddb9a7809e0d36a4b54bf2fc`。在线 #21/#46/#47 已完成。受影响约定依据 Chapter V1 R-06、K-02，U-110 VJ05，[恢复](../../docs/decisions/0008-work-execution-recovery.md)与[新输入采用](../../docs/decisions/0010-work-input-adoption.md)的既有边界。一个 Responses 适配结果，预估 4–8 小时。

1. 已授权用户从原 Work 追加要求。已向 Responses 提交的请求保持原 ID、输入摘要、责任及预约。输入在供应商请求进行时立即收存，原请求内容保持固定。
2. Core 遇到 modeld 已接收但客户端未得到回执时保留预约。Core 重启后根据原 AU、请求和摘要读取已完成结果，复用原步骤、attempt 和工具回执，原请求的 POST 次数保持为一。
3. 同一 Work 的下一合法步骤让固定 Responses SDK 编码原生 reasoning、原 function call、同一 call ID 的 function_call_output 及收存的 user 输入。输出可引用原工具正文与新要求；输入只附入一次，采用成功后才前移 cursor；沿用既有权限、额度和采用事务。
4. 对正常自动交付入口，以同一 Work 和 attempt 完成两次原有步骤；未收存的输入不改变已派发正文，已收存的新要求出现在最终采用成果中。
5. Profile 声明只升级到受控范围，并明确已发送的流无法接收中途注入。继续沿用固定 SDK 的无供应商端存储请求和 Core 的原恢复及输入路径。其他 profile 和既有真实验证各按其证据范围陈述。

验证使用实际 Core HTTP、SQLite、modeld、固定 SDK 与仅回环的 Responses 替身。用 on-wire 计数、原步骤身份、原生工具配对与公开能力投影验证。无需真实推理、部署或数据迁移。
