# U-099：Go GPT-6 Luna 的真实 Responses 资料往返

2026-11-10。用户明确选择 Go GPT-6 Luna，批准 #53/#54 合计最多6次推理、每次
最多2048输出token。本项使用2次；后续中断场景另属 U-100。实施 actor 是 Codex
开发会话 `01a1c217-f4aa-78e3-830b-173a7b72e707`，在线成员 codex-home /
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`，不是产品 AU 成员身份。

真实源基线 `04407dc0aac14792c7bb0c5343dab6375d9a78bb`；[执行前合同](contract.md)、
[固定验收入口](acceptance.py)、[真实页面检查](browser.cjs) 和
[脱敏结果](validation.json) 可核对。本项无产品行为修复，只按实际结果更新能力
数据。现有核心、SQLite、锁定 OpenCode/modeld 和 Responses 传输均真实使用。

## 结果

连接保存为 `openai_responses`、`wire_api=responses`、`model_id=gpt-6-luna`，
原注册 ID、AU/主体和 grant revision 均核对；保存产生0次模型请求。

正常验证完成2次真实模型请求和1次真实 `read_document`。首轮没有材料正文或
随机校验码；第二轮的原生 assistant 消息与第一轮真实返回完整相等，包含原
工具调用，实际工具结果随后送入模型；回答包含工具取得的校验码。本次首轮
返回的 native 类型仅 tool-call，没有声称收到或独立验证不存在的加密 reasoning
项；第二轮报告 reasoning token 27，原始 native 内容仍只在私有存储中保留。

| 原阶段 | 输入 token | 输出 token | reasoning token |
| --- | ---: | ---: | ---: |
| 请求资料工具 | 160 | 42 | 0 |
| 使用工具结果回答 | 289 | 94 | 27 |

本项已知小计449输入/136输出。提供方没有报告已结算金额/币种，均保留 unknown；
不把目录价格折算成真实费用。未把用户对 DeepSeek 的不限调用授权用于 Luna。

干净关闭并重启同一核心/modeld后，原主体、Work、Member、Mandate、Definition、
注册和两次请求不变，原回答及材料/native摘要保持，资源占用2次，没有重派发。
Chrome实际页面首次10项、更新声明后12项检查通过：原回答、Responses连接、逐次用量、未知费用、原
事件重建回答、重复查询和刷新；除正常登录外POST0。最初探针误在检查卡内查找
连接协议标签，实际标签位于连接区；修正探针后通过，失败记录保留。

## 范围与后续验证

此结论只覆盖所选 Go GPT-6 Luna 的 Responses 往返、正常记录重开和页面读取。
生成中断、取消与 unknown 恢复由 U-100另验；#52/U-098 的运行中新输入仍等待
#46/#47通用合同，不由本项宣称实现。Go服务同时提供多种协议；DeepSeek目录只
列Chat Completions并不构成其所有服务端协议的实测否定证据。

Python全量812项、8跳过通过（含实际SDK）；U-100声明更新后14项profile/SDK
补验通过；npm check通过（363前端、306出口断言、37管理）。全量与声明补验的
范围分别记录，准确提交CI与独立采用仍以PR为准。

工程检查、更新声明后的浏览器、准确提交CI与采用结果在 validation.json / PR
记录中分别陈述。未部署、迁移或开展持续业务。所有密钥、私有地址、数据库、
原资料/输出与浏览器截图留在宿主；公开记录只保存计数、请求、版本和哈希。
