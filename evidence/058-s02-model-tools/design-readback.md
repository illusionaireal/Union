# S02 接续：运行链设计与开发卡核查

日期：2026-11-06。范围：用户要求的部署图、目标到首份交付时序、模块改造表及 U-072 四块样板；**本记录不关闭 U-072，也不证明 V1 自主工作已接通。**

## 输入与交付范围

恢复会话 `01a1ae87-b0d7-7ef2-809a-b61b9f24689b`，经其上游 `01a1ae83-829b-7263-846d-b27c10a152f1` 定位原会话 `01a1a9fa-d89d-7091-ba52-c31a1df00b23`。最后的具体要求是“先补清关键执行链的技术设计，再据此改写开发卡片”，先以 U-072 为完整样板。此前完整 S02、验证、提交推送的目标保留；不能因这次设计检查点完成而关闭整卡。

核查基点为 `rewrite/charter-v1` / `c31bf0efac7e54565e3a5fce0d6becd807b12b5a`，当时上游相同。S02 代码和相关契约仍在工作树；本次开始前保存逐文件摘要与空暂存区快照，未重置或接管其他修改。部署描述来自源码与启动器，没有观测真实部署。采用的 Charter SHA256 为 `01b2c7f0b40be6e761376cd719e2c7b61c0d782df6f53ca9b9e4ad0ad50e6174`。

可直接审阅：

- [运行进程与数据库](../../docs/ARCHITECTURE.md#runtime-deployment)：Python、进程内 Harness、另启 Bun/modeld、HTTP、AU 与模型存储。
- [目标到首份交付](../../docs/ARCHITECTURE.md#first-delivery)：建 Work/责任、调度、模型/工具、成果、反馈及其切片归属。
- [接口与恢复](../../docs/ARCHITECTURE.md#execution-contracts)、[模块改造表](../../docs/ARCHITECTURE.md#module-changes)：当前接口与拟新增接缝明确分开。
- [U-072 四块样板](../../TASKS.md#u-072)：由主账生成，包含具体功能、已有/缺失代码、输入输出、入口和演示。

## 两个执行架构问题的结论

| 问题 / 源码 | 当前事实 | 设计处置 |
| --- | --- | --- |
| `model_service.py:ModelServiceTransport.__init__`；`harness.py:HarnessExecutor.__init__` | 仍构造或持有 legacy Engine，不能直接用来操作 V1 | S02 `ModelAccessService.backend()` 直接取 `ModelServiceClient`；S03 才从原 Harness 提取 SDK 驱动并注入 Runtime 的模型、工具和会话端口。旧兼容调用者保留，逐用例迁出，不建立假 Engine |
| `runner.py:step`；`console.py:Console._execute`；`server.ts:pump` | runner 遇任意 unknown/running 阻塞同 AU；Console 的 start/api_test 也拒绝 unknown，runner 锁覆盖整个窗口；modeld 另有跨 AU 的 persistent_serial 队列 | S03 新 Work 入口按工作/冲突资源选择并持久化执行所有权；S06 承接受限并发槽位、公平性和真实故障窗口。只删 runner 判断不能兑现独立工作继续 |
| `application/model_checks.py:ModelCheckRunner.run` | 目前是持久化的两次推理和一次资料工具；与旧连接测试仅共享消息规则 | 不是已接通的通用 Harness。S03 拟迁出单次 attempt 所有者供检查和业务共用，再退役重复分支 |

未来恢复设计补齐“模型事实已保存、采用尚未提交”：保存 fact_id/digest、原 cursor 和 adoption_pending；旧 worker 无权继续，新有效 owner 经受信恢复入口校验原事实及当前资格，以原采用命令幂等提交，不重发原模型。未执行的原工具提议先记意图后执行，已有工具结果读原回执，未知副作用先核对。另以核心 step_ref 绑定 attempt/请求摘要和 SDK 游标，避免 checkpoint 落后时重复推理。该设计尚未实现，S03 契约须在编码前冻结。

## 本轮源码与受控反例

两名独立工程复核者分别核查 Runtime 链和 S02 功能；范围只读，未改正式代码。新增验证使用固定 Bun 1.4.2、合成凭据和回环供应商，真实模型调用为 0；线程探针只构造内存对象。结果与限制如下。

| 项目 | 实际证据 | 结论 / 待实现行为 |
| --- | --- | --- |
| 引号/反斜杠 Key | [保密反例结果](design-secret-boundaries.log)：正常成功和普通 Key 拒绝对照成立，4 个反例失败，exit 1 | 注册公开字段、模型输入、模型输出、跨分片事件仍可泄露合成 Key。`validateAPIRegistration`、`Kernel.inferStream` 和核心 command 的 JSON 序列化字符串搜索需要修复；不能以更早的 23 项 GREEN 关闭 |
| 中断用量 | [中断事件结果](design-native-usage.log)：取消后 result=null、action_authorized=false，原 usage/安全片段在 reopen 后保留，exit 0 | modeld 持久事实已有证据；核心 `usage_from()` 只读 result.usage，`collect()` 不收集 events，这是静态代码确认的投影缺口。该 probe 的其他 observation 不是全部能力通过断言 |
| 线程 start 失败 | [纯内存探针与输出](design-runtime-probes.md)：`spawn()` 在 Thread.start 前把 key 放入 running；key_remains_registered=true、explicit_reconcile_would_start_thread=false | 启动异常没有进入线程 finally，原 check 同进程无法恢复。需清理未启动登记且保持正常同 key 不双派发；探针不替代 HTTP/SQLite 恢复验收 |
| 具体错误 | `ModelServiceClient.call`、`save_connection`、`ModelCheckRunner.run`、前端 Check/Operation DTO | 认证/模型不存在/网络故障缺完整脱敏分类；不是只差真实账号，需要新增错误生产、持久化、接口及展示 |
| 资料工具 | `ModelFields`、`ModelAccessStore.material/tool_result` | 只读用户选择/提交的一份文本；没有宿主目录授权和列目录。目录场景明确作为 S03 拟新增资料适配器，不能当成 S02 当前能力 |

[探针版本与摘要](design-probes.json)固定被测源代码和探针 hash。上述原探针保留在宿主审查目录，发布结果不含真实凭据或部署信息；后续修复应将反例纳入正式测试，并记录新的 GREEN，不能覆盖本次 RED。

## 从原会话恢复的证据及限制

以下是恢复的历史日志，不是本次重新运行的完整验收。它们用于确定已做工作、避免重复，不足以覆盖更晚发现的缺陷。

| 原证据 | 当时结果 | 不能据此声称 |
| --- | --- | --- |
| S02 Python 全集 | 561 tests，OK，5 平台跳过 | 最新最终候选、真实模型或持续运行通过 |
| React 组件 | 175 项总测试；34 项 S02 范围检查通过 | 实际浏览器闭环通过 |
| modeld 范围回归 | 23 pass / 0 fail | 后续 4 个凭据反例已修复；这组 GREEN 更早 |
| 核心 HTTP→modeld→固定 SDK→回环供应商 | 1 项通过，real_model_calls=0 | 指定真实供应商/profile 已验收 |
| schema/打包规则 | 14 项通过，含 mock preflight | 最终候选已实际安装并运行 S02 |
| 实际浏览器 | 11 项初始检查通过，随后在 1440px 完成状态文字可读性失败 | 其余宽度、丢回执/重启尾段及身份切换/撤权等全部完成 |

## 本次交付验证与下一步

本次只改变设计、卡片和交接记录；结构和固定工具链结果见 [验证记录](design-validation.json)，两份咨询复核见 [Runtime](design-runtime-review.md)和[样板卡](design-card-review.md)。独立复核提出的原事实采用、SDK 步骤去重、预算重复扣减及旧入口遗漏均已补清；Runtime 报告中的非阻断 generation 类型建议也随后补入正文。工程测试绿色不撤销上述 RED。

本次实际重跑 `npm run check` 通过（含 175 项前端测试），Python discover 运行 561 项、556 通过、5 项平台跳过；对应 [npm 输出](design-npm-check.log)与 [Python 输出](design-python-discover.log)保留原日志摘要，公开副本规范换行并替换临时测试目录名称。构建仍有既有的 500 kB chunk 提示，构建成功。以上针对含未提交 S02 代码的工作树，不是最终安装候选，也不覆盖额外凭据反例。文档结构、当前链接、主账/线上正文和预存代码保持检查见 [结构结果](design-structure.json)；HANDOFF 只核对新增条目，历史条目字节保持不改。

主账保留 U-072 doing、原 owner/历史/依赖/claim 和 6/6 占用。当前管理脚本没有先前宿主扩展的 mutateLedger 导出，使用保留的同一统一适配器快照作锁内更新，再运行当前管理生成器与校验器；没有改动或交付该宿主工具。其他 75 张任务对象、模块、里程碑和容量均保持原值。在线 #21 从 version 3 更新到 4，读/写/读回均 HTTP 200、progress、正文等于主账；其他卡未变，见 [收据](design-kanban.json)。

ADR 核查选择在原 ADR-0005 补设计核对和基线链接，不新建已采纳的未来决定。当前文档与主账可供审阅；S03/S06 接缝仍为后续契约输入，代码中的保密/恢复偏差保持 Implementation Drift，未通过降低需求来消除。

继续 S02 代码前先按样板细化错误/用量字段，严格 RED→GREEN 修凭据边界、线程启动恢复、中断用量和诊断；然后完成实际浏览器、最终安装和独立复核。指定真实 profile 的安全配置位置、资料、调用上限与费用范围尚未落实，真实调用须等这些资源条件具备，不扫描其他认证库。全部 M01–M10 和本片 real 出口完成才关闭整卡。
