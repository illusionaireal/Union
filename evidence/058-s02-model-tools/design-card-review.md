# U-072 / S02 四块样板独立复核

日期：2026-11-06。审查者：`/root/s02_feature_audit`。范围：当前工作树中的 `.union/s02-design-resume/u072-card.md` 与 `evidence/058-s02-model-tools/design-readback.md`；依据已核查的 S02 契约、源码和本轮受控反例。没有修改正式设计、实现、测试、Git、主账或在线卡。

## 问题优先

当前两份设计文件没有尚未处理的阻断性问题。此前反馈的 DTO、事务边界和证据引用问题均已解决；这只支持本次设计样板交付，不表示 S02 实现通过。

1. `u072-card.md:43` 已使用 `receipt.status='succeeded'`，并区分命令采用与异步 operation/check 完成。
2. `u072-card.md:44` 已把 `expected_revision:0` 限定为新建，编辑使用当前 revision；`modeld_grant` 明确移除 base_url/api_key，使用 grant_ref/grant_revision。
3. `u072-card.md:54` 已正确表述同 AU SQLite 的 state、意图、资料和回执在同一事务提交；modeld 账号/grant 属于另一个数据库事务，没有跨库全局事务。
4. `design-readback.md:34-40` 引用的三份证据已补齐。两份日志与本轮原始日志逐字节一致；公开 metadata 仅更新日志路径并增加匹配的日志摘要。

## 对需求、接口及当前能力的判断

- 四块内容齐全：用户可见行为、具体代码落点、完整流程与接口输入输出、完成演示及验收。样板全文已进入生成的 `TASKS.md`，`## U-072` 提供其引用锚点。
- `u072-card.md:34` 明确把 `diagnostic={code,stage,recovery}` 和 `usage.observation={kind,sequence,complete,missing_reason}` 标为编码前待细化的设计，保留现有 `usage.source` 语义，没有冒称当前 API 已提供这些字段。编码前仍需在现有 S02 契约冻结其枚举、完整性、幂等与版本规则。
- `u072-card.md:10,48,52` 保留实际的单份提交文本与精确 document_id 工具边界；宿主目录登记/列目录/越界防护清楚标为 S03/U-067 拟新增行为。没有把上传文本与宿主目录授权混为一谈，也没有授权现在实现 S03。
- 保存、有限授权、验证和默认采用彼此独立，unknown 明确核对原请求，恢复仍校验当前授权。M01–M10 与指定真实 profile 出口均保留；`u072-card.md:71` 和 `design-readback.md:57-59` 均保留整卡未完成的事实。
- 本次文档未发现新的 Design Defect。已经复现的凭据保密等实现偏差没有被删去或重命名为“仅待真实环境”；卡片将其保留为后续需要 RED→GREEN 的实现工作。

## 证据复核

本轮重新核实的基点为 `rewrite/charter-v1` / `c31bf0efac7e54565e3a5fce0d6becd807b12b5a`；工作树含预存修改。没有把 HEAD 与尚未提交的 S02 实现混用。

- 两个探针文件和 metadata 记录的三份被测源码，SHA256 全部仍匹配本轮执行快照；此次最终设计复核没有重复运行探针。
- `design-secret-boundaries.log` 与 `.union/s02-resume-audit/secret-boundaries-current.log` 相同，SHA256 为 `9dbe41413a0cc8231b20fe65b2262638c8f55028a86bd26876b3f8bd9fe350ce`。原执行 exit 1、四个保密反例失败；普通成功和普通 Key 拒绝对照成立。
- `design-native-usage.log` 与 `.union/s02-resume-audit/native-usage-boundaries-current.log` 相同，SHA256 为 `6d1feb39453f9c5292de7fc7cd2881fa27ed567772dc3c5848ea12091351f7f6`。原执行 exit 0，证明取消及重开后 modeld 的已观测用量/安全事件仍保留；不证明核心已投影这些用量，也不把其他 observation 当作全部能力断言。
- `design-probes.json` 与原 metadata 在日志路径/新增日志摘要之外完全一致。真实供应商调用为 0；使用固定 Bun 1.4.2、合成凭据、精确回环及独立临时状态。
- 两份被审文件的所有文件链接可解析；架构的四个显式锚点和 TASKS 的 U-072 标题锚点存在。卡片按其生成目标 `TASKS.md` 所在的仓库根解析相对链接。
- 文档检查脚本使用固定 `.venv/Scripts/python.exe`，退出码 0。没有将历史 Python/前端/modeld GREEN 写成本次全量复验；实际浏览器 1440px 的失败、未完成尾段和其他宽度均仍注明。

此次检查时的文档摘要：

| 文件 | SHA256 |
| --- | --- |
| `.union/s02-design-resume/u072-card.md` | `608cff6c607d68e1ae5e14567fefead941c5fb4b5f55b29bfcb93773a4ad61a3` |
| `evidence/058-s02-model-tools/design-readback.md` | `df7ca146bcdf24864652c083fc1c5c973d397ab266876edb205da68f3f6caf45` |

## 判断与剩余风险

设计样板可进入协调者最终交付检查。整片 S02 不具备合并/完成结论：凭据泄露、脱敏诊断、核心中断用量投影、线程启动失败恢复、完整浏览器、最终候选实际安装与指定真实 profile 验收仍未闭合。

此为建议性独立审查，不具有任务接受、合并、主账或在线状态变更权。文档一致性判断有当前证据支持；实现及真实出口证据仍不完整，不能以设计评审代替。
