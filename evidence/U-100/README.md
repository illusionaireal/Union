# U-100：Go GPT-6 Luna 的真实 Responses 中断与原请求恢复

2026-11-10。依据[执行前合同](contract.md)，与 [U-099](../U-099/README.md)
共用明确授权的 Go GPT-6 Luna 批次：最多6次、每次2048输出token。正常场景2次，
本中断场景再用2次，合计4次。实施 actor 为 Codex 开发会话
`01a1c217-f4aa-78e3-830b-173a7b72e707`；在线成员 codex-home /
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`，分别记录，不是产品 AU 成员身份。

## 实际结果

复用 [U-099 固定入口](../U-099/acceptance.py) 的 `interrupt`，同一 AU 的新
check 保存原责任，首个请求真实调用 read_document，第二个请求开始回答。
原 V1 事件端点在 `streaming`、cursor 51 读到63个 UTF-8 字节后才发出取消。
取消前原正文 SHA256：
`871914f286f1ddee5b3ab16a9a2505b9ccc1b50bb58bc13d09473fdd395e2535`。
原 modeld 请求转为 `interrupted`、`cancel_requested=true`；核心检查仍为
`unknown`，等待对象及负责 Member 保留。没有把部分文本当成成功回答。

关闭并重启同一核心/modeld后，以原 check ID 执行 reconcile；原4次请求未增加，
4次预约保留，正常结果未变，中断结果仍 unknown。提供方已完成的资料工具请求
报告159输入/41输出token；中断回答的输入、输出、金额和币种仍未知。批次已知
小计608输入/177输出不含未知中断量，不能当作总消费或退款证明。

[真实 Chrome 检查](browser.cjs) 在重启后核对正常原回答、两条原检查、实际用量、
unknown、中断前缀精确字节摘要、重复查询及刷新。除登录外没有模型/业务 POST。
检查计数、补充责任/版本验证和工程回归见 [validation.json](validation.json)。
初次受控声明下17项通过，更新声明后19项通过；没有为本卡修改产品行为。

[补充重启只读核对](verify.py) 逐项比较原主体、Member、Work、Mandate、绑定、
Agent Definition、治理/资源/连接/grant版本和全部计量字段。原事件水位从105
推进到140；首次两个审计尝试把该水位也当作不变量，失败记录保留。最终检查
分别要求水位单调前进及计量字段不变，未修改产品来满足探针。

Python全量812项、8跳过通过（包括实际SDK，运行于本卡声明更新前）；声明更新后
14项profile/SDK补验通过。npm check通过，最终提交CI及独立评审由PR记录。

## 能力边界

此处取消指核心停止等待、modeld中断及查询已保存原记录。当前传输使用
`stream/store=false`，没有验证提供方 background response 取消、退款、远端
终止或原生断点续传；未知结果/占用不能释放。取消与查询成功不代表任务成功。

能力声明只覆盖 Go GPT-6 Luna 的本次 Responses 实测。#52/U-098 的运行中新
输入仍依赖 #46/#47 通用合同，没有用本卡关闭；其他模型和 profile 分别验收。
正常往返详见 U-099，不从 Chat Completions 历史推断 Responses 已可用。

所有资料正文、密钥、部署地址、数据库、完整事件、截图及失败历史保留在宿主
私有目录；Git只保存脱敏计数、身份/请求关联、版本与哈希。未部署、迁移或
开启持续业务；准确提交CI与独立评审/采用分别记录在PR。
