# S02 Responses 与私有 Schema 独立工程复核

2026-11-06。复核者：外部工程子代理 `s02_protocol_review`。目标分支 `rewrite/charter-v1`，已核对 HEAD `d5802f8672df88db447e7e0bb86c2f1a5265ad18`。结论针对当前未提交工作树中下列文件，不能仅凭 HEAD 复现。

**结论：本次协议、私有持久化和受支持发布兼容范围没有发现阻断项，可进入协调者的隔离安装及已经授权的指定连接验收。规格符合；所检查质量边界通过。** 本报告不关闭 U-072，不表示真实调用、完整用户验收或发布完成。本复核真实模型调用为 0。

## 先核规格

依据 `specs/053-union-rewrite/s02-contract.md` 的两个 2026-11-06 续接段、ADR-0005 的 Codex 细化，以及 `services/modeld/AGENTS.md`。

| 冻结边界 | 核查结果与证据 |
| --- | --- |
| 显式协议，保留旧请求语义 | `api-accounts.ts:23` 限定协议及 reasoning 设置；缺省仍为原 Chat。`kernel.ts:202` 按持久显式设置选择固定 SDK Responses，不按端点、模型名或错误猜测/回退。新设置纳入原 registration digest。 |
| 固定当前所选资源与 native 配对 | Responses HTTP fixture 实际核对 `gpt-6-astra`、`max`、512、`stream=true`、`store=false` 及 `/v1/responses`。第二次请求带回原 encrypted reasoning、function_call 和对应 function_call_output。`kernel.ts:233`、`:243` 保留 AU/account/model/upstream 及公开工具参数配对校验。 |
| 原单次服务与授权所有者 | 沿原 Journal grant / server 派发 / inferStream 路径；API 账号不成为可重授的 Go 宿主账号。原 AU、principal、model、grant revision 和撤权取证边界通过现有 API/迟到/权限回归。modeld 不执行业务资料工具，不另建 Agent loop。核心完整两阶段应用闭环未在本报告重复审计。 |
| 原始摘要和回执保持 | `journal.ts:89` 同 ID 先比较完整摘要；旧无显式字段的记录不重写，升级后及重开后仍返回原回执。撤权后重复 registration 不复授 grant。 |
| 持久升级与恢复 | `journal.ts:98` 在原 registration 事务内增加 nullable options、设置 user_version=1、建立 grant/account；注入 grant_audit 写失败时 DDL、版本、账号与 grant 全部回滚。读取/启动不升级版本；已升级保持 1。未知版本在恢复 connecting/streaming 请求前拒绝。 |
| 受支持发布与回退窗口 | `release_package.py:127` 声明 modeld_schemas=[0,1]，旧清单缺字段只认 0。`:297` 按与 modeld main 相同的配置相对路径读实际库版本。preflight、activate 与 run 都检查；不兼容时尚未改 current 指针/启动子进程，原数据库字节保持。 |

## 再核质量与实际执行

- 固定 Bun 1.4.2：Responses、API、Chat kernel、Journal、server 和迟到结果共 **38/38** 通过；日志 `protocol-review-modeld.log`。Responses fixture 两次正常推理分别报告用量；401/403/404/429/503 各只发送一次 HTTP，请求保留 interrupted，外部错误中的假密钥未进入查询结果。
- 原 Go 正常对照 **2/2** 通过；日志 `protocol-review-go.log`。覆盖账号 scope、native 工具、一次刷新、HTTP/首事件超时以及设备认证一次持久保存；全部为临时目录和替身。
- 固定 `.venv/Scripts/python.exe`，UTF-8：`tests.test_modeld_release_schema` 与 `tests.test_core_model_release` 共 **5/5** 通过；日志 `protocol-review-python.log`。覆盖 0→1 后拒绝旧代码采用/运行、坏清单、未知/损坏私有库、当前构建包的 schema 声明与 AU schema 3 原有回退边界。
- `usage.ts` 对 requested/resolved 资源与未证实 actual_model 保持区分，actual_model 为 null；缺失 token 不补零，SDK 无币种浮点 cost 不变成已知币种金额。两次 Responses 用量各属于其原 request，不相加流中累计与最终值。
- 未修改源码、Git、主账、在线卡或真实配置；仅生成本报告和上述独立本地测试日志。保密增量 matcher 由另一审查者负责，本报告只核查协议接入处的共享调用及 HTTP 错误边界。

## 结论限制

尚未对最终隔离安装目录运行真实指定连接；本次包测试核查当前包声明及发布选择拒绝行为，不代替协调者最终安装候选取证。用户指定的真实两次推理、工具继续回答和供应商费用仍须实际记录。使用受支持发布器是回退保证的边界；绕过它执行任意旧二进制不在保证内。没有从这些受控测试推断真实自治、稳定运行或整个 U-072 已完成。

下列 SHA-256 由报告生成时的实际文件读取；若相应实现再次变化，应对变动范围补核。

| 文件 | SHA-256 |
| --- | --- |
| services/modeld/src/api-accounts.ts | 8d7242f693616b21c0073fafb3d13096e2cb61dc93c2b56c1315663b28f314d2 |
| services/modeld/src/journal.ts | 5c72b1ba488801c9f0cb540839912dc7ee2a06aa3055b21de583ef67c1eb5a67 |
| services/modeld/src/kernel.ts | cac040511eed9ec6cd025f569d59ca0014d9aa9e80abf9c3f4b271dd7d1f5aa4 |
| services/modeld/src/usage.ts | 0c84b7549421fca520565eee5b516892acb202ba6765f0733073b1bdc6bfc587 |
| scripts/release_package.py | 5f629fe07fc4521bc99de87ddf1cd89d9fc365154b59521dd41b62ca34a3185d |
| services/modeld/test/responses.test.ts | 70bede16fa4ca7d5c072e046ff1097a4d812dd0562254fd91ae73f23f1effda9 |
| services/modeld/test/fixtures/responses-probe.ts | 6f97483d263bcf630829742a3de844cb923a6a400fec9565dc1a8385c8bbd073 |
| tests/test_modeld_release_schema.py | dfb0bcc079c5adcac6f1c3000f8d61ca1a4c9a274e1804c613f1147e35ccbea5 |
| tests/test_core_model_release.py | ceeb6969558c37104156332b2d6c01914e538816ad4c48a78b399c6e0fcfcd08 |
