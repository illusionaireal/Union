# evidence/139 — 原输出门控真实中断出口（83192ba 门控候选 + 1 次真实派发）

## 背景

值守 `codex/u086-original-output-gate`（d118dbb/83192ba）针对 #40 评论 237 的合同项①边界提出门控候选：evidence/138 的驱动虽探测到 Core 面，但接受失败/缺失端点、任意非空事件表与 ownEvents=0，且公开投影有意把 `model_request_id` 放在信封而非单事件内——不能确立「取消前已观察原请求真实输出」的完整验收。其 31 项 Node 门控测试对旧断言块 **1 pass / 30 fail**，对候选 **31/31**。

## 门控内容（候选驱动）

- 事件响应绑定原 AU/Work/attempt/step/command/model request/连接/principal/service；
- cursor 跟随过滤页且单调有界；非法排序拒绝；
- **取消前要求实际非空公开文本**（哈希 + UTF-8 字节数保存观察引用，不存原文）；
- U108 缺失 = 验收门失败（fail-closed）。

## 真实运行（本证据）

**118 checks，exit 0**（单次真实派发，deepseek-v4.1-flash）：

- 原输出绑定/会话/cursor/有序公开文本观察断言全过（含取消前实际非空文本）；
- 取消受理 + 回执身份 + 同 run 原 GET 身份匹配；
- unknown 保留（reserved=1）+ 重启持久 flow-aware。

## 备注

- 门控测试 `node --test tests/exit22b-original-output.test.ts` 31/31。
- 值守完整验证：808 Python/10 跳过/0 失败、npm 363/51/37、render/check 通过；其候选需「另一工程角色复核 + 当前 head CI」后采用。
- 本证据取代 138 为当前驱动基线。
