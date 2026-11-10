# U-099 / #53：真实 Responses 材料工具往返

2026-11-10 编码/执行前冻结；基线 `04407dc`。实施 actor 为 Codex 开发会话
`01a1c217-f4aa-78e3-830b-173a7b72e707`，在线成员 codex-home /
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`。#53 已以真实身份/最新版本认领。
本项预计2–4小时，一个真实 profile 结果；#54 中断验收另记，不吞并 #52 的通用依赖。

用户明确批准使用同一 OpenCode Go 订阅的 `gpt-6-luna` 完成 #53/#54，首批合计
最多6次推理、每次最多2048输出token。读取既有宿主私有密钥文件，不混用其他账号。
不从此前 DeepSeek 不限调用次数授权推导 Luna 的无限额度。未确认、已发出及失败
请求占用保留；额外调用必须符合该批剩余范围，不能静默整批重跑。

Go 目录声明 Luna 使用 Responses，DeepSeek 条目只列 Chat Completions；目录不是
穷举服务器可接受协议的实测证据。本项真实请求明确走 `openai_responses`，不得
失败后改用 Chat Completions，也不得把此前 Go/DeepSeek 成功当本项结果。

## 必须观察

1. 独立 AU 经核心真实 HTTP 注册/登录、准备、采用并激活本地治理；显式允许
   read_document、登记6次资源授权。保存 Responses 连接不产生推理；原注册回执
   的 profile/wire_api、原 AU/主体/模型/grant/version 必须与选择一致。
2. 一个正常检查保留两个原模型请求。首轮不得带所选材料正文或随机校验码；
   原 function_call 的 call_id/参数、真实工具回执及材料哈希可相互核对。
3. 第二轮使用第一轮真实 native 返回及实际 function_call_output，保留返回的
   reasoning/加密项，不伪造、不重建已签名内容。最终回答包含工具取得的校验码。
   官方依据： https://platform.openai.com/docs/guides/function-calling 。
4. 原使用量分次记录；未报告 token/币种/金额时保留 unknown，不把目录价格推算
   成已结算费用。Work/Member/Mandate/Agent Definition 与其版本持久关联。
5. 干净关闭并重启原核心/modeld；核对原身份、请求、回执、材料/结果 SHA 和用量。
   真实 React 页面读取原回答和事件；观察/刷新不派发，跨身份/撤权保持既有隔离。

只有该真实往返通过后才升级 Responses 的相应能力数据，精确指向 Go GPT-6 Luna。
共享流式投影、SDK协议及身份规则沿已有实现；若发现产品行为缺陷，先补有意义
RED，再最小 GREEN，不破坏现有代码制造失败。npm check、Python全量、受影响
检查及准确提交 CI 分别记录；权限改动另需其他工程角色复核。

## 与 #54/#52 的边界

#54 同批另做看到真实文本后取消、同原请求查询和同数据重启。modeld本地中断
不等于提供方取消成功；当前 stream/store=false 路径不凭文档声明提供方的
background response取消/恢复能力。该功能需实际服务支持、原response id与单独
边界证据，参见 https://platform.openai.com/docs/guides/background 。

#52 只消费 #46/#47 提供的通用责任恢复/输入合同，不能另造队列或用追加历史消息
伪称运行中输入已生效。本项不提供新输入支持、部署、迁移或持续业务证据。

原 Go 验收脚本/证据保留。新脚本是本批固定验收入口，仅调用现有核心/modeld；
私有日志、配置、数据库与原消息不入 Git。公开记录只含实际结果、身份关联、
原请求ID、哈希、数量、失败和限制。启动前检查无本批残留服务，结束正常关闭。
