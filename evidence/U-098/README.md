# U-098 / #52 Responses 长工作续接

2026-11-28。用户能在原 Work 的 Responses 请求运行时补充要求。Core 收存后，下一合法请求携带新要求、原生推理片段和配对的工具结果。已经发出的请求保持固定。能力页将这项行为标为「仅受控验证」，并说明已发出的流无法注入新输入。

## 本次观察

在实际 Core HTTP、SQLite、modeld 和锁定 OpenCode SDK 上使用回环 Responses 服务。故意丢弃 modeld 已接收的 POST 回执，此时原请求仍在供应商替身上等待。用户在同一 Work 收存输入，原请求正文和步进记录保持一致。重启 Core 后，原 AU、请求 ID 与摘要找回原结果，原 attempt 和工具回执继续使用。恢复阶段未增加原请求 POST。

下一步使用不同的请求 ID。Responses 请求保留加密推理片段，function call 与 function_call_output 用原 call ID 配对，已授权工具正文和追加要求进入下一步。供应商替身实际收到合计两次 POST。采用结果后输入 cursor 从 0 变为 1，输入仅附入一次；两个步进分别保留输入用量 17、41 tokens。另用现有自动工作入口提交一次工作意图，首个 Responses 请求等待时收存输入，释放后由原执行器完成第二次请求，交付正文包含所选资料和追加要求，同一 attempt 只保留一条。Chrome 确认新范围和限制出现在模型能力页。

该验收复用 U-092、U-093 的恢复和输入路径。服务商不保存这两个 Responses 请求，Core 从自己的原记录接续。验证使用回环凭据和合成输入，真实模型调用为零。

## 复现

[冻结合同](contract.md)记录输入、身份、恢复与范围。固定 Bun 1.4.2，按 modeld 准备流程安装 SDK 依赖并设置 UNION_BUN，然后运行：

```powershell
python -m unittest tests.test_core_model_http tests.test_core_responses_profile tests.test_core_model_profiles -v
npm run test:resources
```

首次探针使用了旧 attempt 索引投影。修正为公开 attempts 记录及成果正文 GET 后，原行为走通，公开能力状态仍为 unsupported。自动交付探针最初使用不符合业务资料 ID 合同的夹具，改为合法标识后通过。最小修复只更新 Responses 公开能力声明。

[验证记录](validation.json)绑定基线、当前变更字节、受控检查和历史失败摘要。
