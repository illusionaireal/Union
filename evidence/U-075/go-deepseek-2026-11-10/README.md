# U-075 / UNI-028：Go DeepSeek 真实往返与中断查询

2026-11-10。用户指定 OpenCode Go `deepseek-v4.1-flash`，明确授权不限调用次数；
本次仍以独立 AU 的 6 次授权、每次 2048 输出 token 为界，实际派发 **4 次**。
实施 actor 为 Codex 开发会话 `01a1c217-f4aa-78e3-830b-173a7b72e707`；在线成员
codex-home / `c18f0d21-1d63-4e37-af3e-2dbb78d75995`。工程开发者不是产品 AU 成员。
基线 `f2fb72c2b31b2e2c29ea385d8ea1da05506fee3f`；构建、原请求与验证见
[validation.json](validation.json)，执行前范围见 [contract.md](contract.md)。

## 真实观察

使用真实 React、核心 HTTP/SQLite、锁定的 modeld/OpenCode 内核和合法订阅密钥；
无假模型、假工具回执或直接改库。官方 [Go 文档](https://opencode.ai/docs/go/)
及已认证的模型目录 HTTP 200 确认该模型使用 Chat Completions；连接走现有
`openai_compatible`。密钥、认证资料、数据库、原上下文/输出和截图只留宿主。

| 场景 | 原请求与结果 | 实际用量（输入 / 输出 token） |
| --- | --- | --- |
| 正常工具请求 | `model-507d9ffe6000508ca3e49a7e14253ff8`，完成 | 422 / 71 |
| 工具结果后的回答 | `model-260d3c47092c52ea9ec165b396717856`，完成 | 341 / 168 |
| 中断场景工具请求 | `model-b905cff193b95720879bdc9a714f4ad5`，完成 | 417 / 91 |
| 看到正文后停止 | `model-49256668c6015a8dbd35513992b5220d`，modeld interrupted | 未知 / 未知 |

保存连接不推理。正常验证首轮请求没有所选材料正文和随机校验码；真实
`read_document` 回执、材料 SHA、原生 assistant/tool 配对进入第二轮，最终回答
包含校验码。两个场景共两次真实工具读取；正常回答和工具内容的哈希已归档。

中断前从原 V1 事件入口读到真实 streaming 正文（57 UTF-8 字节），随后才发出
本地取消。重启同一核心/modeld，正常密码登录，原主体、Work、Member、Mandate、
Agent Definition 和请求身份保留。原请求核对没有重派发，正常输出不变；中断
check 保持 unknown，已派发 4 次占用均保留。已知 token 小计 1180 / 330，
**不是总用量**；中断请求用量、全部费用/币种及远端取消结果仍未知。

## 真实验收发现的修复

中断后保存文本的页面首次返回403。modeld 的 `action_authorized=false` 既表示
已中断不可执行，也可能表示撤权。核心将两者一律用于历史读取，误拒绝了仍有
当前授权的治理者。先冻结 [事件合同](../../../specs/053-union-rewrite/s09-model-observation-contract.md)
与 ADR-0006；新增真实核心 HTTP 取消/核对回归观察到 4 RED，旧10项仍通过。
最小修复仅允许原 check 明确停止、原远端明确 interrupted 且 cancel_requested
同时为真的只读历史。原身份/摘要、当前治理者、连接与实时 grant/revision
前后核对均保留；其他 false、缺失或非布尔停止事实、撤权/停用仍拒绝。

同一批4次真实请求复验 Chrome：14项通过，精确保留取消前文本哈希，正常
回答和用量可读，未知不显示成零，刷新保持原记录；仅正常登录 POST，模型/业务
命令0。页面能力数据另明确只验收上述 Go 模型；其他 profile 不升级。更新声明后
再用同一原数据验证16项通过，并正常停止验收宿主，modeld 请求总数仍为4。

## 历史与验证边界

- 首次 prepare 因 Python HTTP 字符编码失败，尚未创建 AU/调用模型；原失败根保留。
- 首次浏览器失败是登录按钮选择器；修正后真实发现上述403，截图/检查日志均保留。
- Windows 停止旧验收宿主后，包装进程的子进程仍持锁，首次重开被拒绝；未派发。
  核实并停止本任务残留进程后重开成功，驱动增加显式停止文件以正常关闭。
- 修复前全量 Python 808项、8跳过通过。4 RED → 29项事件/观察/恢复 GREEN。
  修复后全量 Python 812项、9跳过、0失败；npm（363项前端、类型与构建）通过。
  随后仅能力证据数据更新，由15项 profile/Responses/发布检查及最终浏览器复验；
  全量回归启动时尚未含这次声明数据更新，当前完整提交另由 PR CI 核验。
  命令结果、范围和日志哈希见 validation.json。
- 本次是有界真实接入及工程修复；独立权限审查、协调者合入和当前 PR CI 单独核对。
  没有业务部署、迁移或持续运行；人工参与是资源选择与验收操作。

该模型不支持 Responses；不能关闭 #52/U-098、#53/U-099、#54/U-100。
长任务中追加输入仍明确不支持；查询原事件不是继续推理，也不证明供应商退款。
本父卡全部验收及独立采用条件未满足前不能 done。

## 重现入口

[acceptance.py](acceptance.py) 依次使用 prepare、normal、interrupt、reopen，
每步必须显式给 `--state-dir` 和 `--bun`；prepare 另给宿主私有
`--provider-config`。先审阅合同并提供合法资源。已记录的命令拒绝整步重跑，
丢失回执必须查询原 ID；既有目录不得重做 prepare。

只读浏览器使用 serve，再给 [browser.cjs](browser.cjs) 注入
`UNION_GO_ACCEPTANCE_STATE` / `UNION_CHROMIUM_PATH`。在该私有目录创建
`stop-requested` 文件可正常停止本验收宿主。这些驱动使用现有产品入口；
不是另一套演示页面、产品调度器或持续业务验收。
