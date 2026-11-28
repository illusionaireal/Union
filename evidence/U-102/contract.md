# U-102 / #56：独立客户端工作登记的冻结验收合同

2026-11-16；输入 `2b3d281f7bfb6dc3fdb8e00f432cc4f76756a8fc`。
依据 Charter A-01/A-04、D-01、R-01/R-02/P-07、PRD F03/F04、ADR-0004/0005/0006，
沿 [U-101](../U-101/contract.md) 和 [S03登记合同](../../specs/053-union-rewrite/s03-work-registration-contract.md)。
actor：Codex session `01a1e041-e19d-7732-b6d8-025ff9dc3252`；在线成员：
`codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`，均非产品 AU 成员。

一个4–6小时的受控集成结果；#20/#24/#59/#55已完成，#56按HTTP200认领v4。
只扩展现有标准库黑盒客户端验收，不修改核心权限、共享事务、schema或UI。
真实Core在独立子进程运行，所有组织/治理/模型连接/工作准备只经公开HTTP。
宿主仅管理自己的临时目录、进程和合成配置；回环modeld替身仅回答合成AU授权GET，
任何推理POST均记录并拒绝。禁用真实继承配置、无私有平台依赖或模型调用。

| ID | 成对验收 |
| --- | --- |
| W01 | 普通核心账号在自己合法激活的AU登记`start_work`；原Work/Member/Binding/Definition v1/Mandate v1可读，AU版本只增加一次，pending且无执行、结果或派发。 |
| W02 | 独立平台管理员账号也不能读取/登记/重放他人AU工作和回执；未知与无权回执同样拒绝，原合法工作不变。 |
| W03 | 同主体新登录会话相同请求回放返回原回执、不重复登记；同ID更改输入409 id_conflict，原版本/责任保持。 |
| W04 | 陈旧AU版本、陈旧连接revision、治理退出或停用连接得到持久rejected回执，HTTP200不冒称成功；原状态不变。当前合法对照仍能登记。 |
| W05 | 丢弃POST响应正文后只GET `/api/v1/governance/receipts?organization_id=...&id=...` 找回同一Work；不再次POST、不改原ID。 |
| W06 | 重启Core进程并正常登录后，原principal/Work/责任/版本/回执保持；模型替身无推理POST，读取无隐式登记。 |
| W07 | 匿名/跨Origin、非法字段或类型在采用前拒绝，修正后的同ID可成功；不接受调用方伪造主体。 |
| W08 | 原回执中的request/kind/AU/base_version/actor/time/version与公开工作状态一致；拒绝的持久回执也可查。返回值不泄漏密码、cookie或宿主配置。 |

工作API为 `POST /api/v1/work/commands` 与 `GET /api/v1/work`；工作回执复用
现有治理回执URL，不发明`/api/v1/work/receipts`。准备通过create_v1、adopt_governance、
activate_governance、save_connection、set_connection完成。登记不启动自主业务。
审计仅指公开命令回执和责任/版本关联，不读取私有数据库，不声称验证拒绝日志或
跨存储原子性。响应丢弃仅模拟已应答但正文丢失，不当作远端取消/网络断连证明。

已有正确行为允许首次GREEN，不撤掉实现制造RED；若遇产品缺陷，保留真实失败并
冻结窄修复再改代码。新模块/原U101、npm check、固定Python全量和准确head CI需通过；
权限结果由非实施工程角色复核后采用。父#30、#58与真实/持续运行不由本卡关闭。
