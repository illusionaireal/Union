# Go DeepSeek V4.1 Flash 的 Responses 实测与更正

2026-11-10。用户指出“也支持responses”，按照[核查合同](contract.md)实测后确认：
当前 Go 订阅的 `deepseek-v4.1-flash` 能接受 Responses，并完成真实资料工具往返。
此前依据目录只列 Chat Completions 推断“不支持 Responses”不成立。原先的
Chat Completions验收与错误判断历史保留，本记录更正该结论。

隔离协议实验通过核心真实HTTP创建/治理/资源授权、保存 `openai_responses`，
modeld原注册确认 `wire_api=responses` 与原模型/grant。保存0调用，正常场景
2次真实请求/1次read_document；首轮没有正文或校验码，第二轮收到实际工具
回执及首轮原生消息，回答包含校验码。原生首轮只有tool-call，本记录不声称
存在或验过未返回的加密reasoning。第二轮计量报告9个reasoning token。

| 阶段 | 输入 token | 输出 token |
| --- | ---: | ---: |
| 请求资料工具 | 410 | 64 |
| 使用工具资料回答 | 330 | 84 |

合计740输入/148输出；金额与币种未知。同核心/modeld干净重启后原主体、Work、
请求与回答不变，2次预约保留，请求仍为2。未做本模型的Responses取消或浏览器
验收；不据此外推其他服务/部署或运行中新输入能力。

本次使用用户此前对 Go DeepSeek V4.1 Flash 的不限调用授权，核查自限2次、
每次2048输出token；不使用Luna的6次额度。协议实验单独标识，保留原Go与Luna
全部历史，不用于掩盖失败。未回退Chat Completions、替换模型或伪造工具回执。

执行入口是[U-099固定脚本](../../U-099/acceptance.py)的宿主私有副本，只替换：
REPO定位、模型 `gpt-6-luna`→`deepseek-v4.1-flash`、连接ID及显示名、实验名、
两处资源上限6→2、资源授权说明。流程、协议、断言不变；依次执行prepare、normal、
reopen，每个派发意图只执行一次。副本SHA、原注册/请求、用量、材料/回复/native
摘要及重启结果见 [validation.json](validation.json)。私有凭据/正文/日志/库不入Git。
