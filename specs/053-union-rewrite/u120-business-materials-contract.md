# U-120：业务资料导入、授权与同一 Work 读取

2026-11-24；基线 b4371d8；在线 #74 v4 已由 zbook-codex 认领。用户明确批准接续 U-120。消费 VJ03/UX-02、FRONTEND §4.1、S03 工作/派发/工具上下文契约与 Chapter D-01/D-04/P-04/K-02。任务分支 codex/u120-business-materials，估时 6–8 小时，一个完整结果，顺序集成共享事务。

## 用户结果与边界

有权用户在同一组织的能力与资源页选择 UTF-8 .txt/.md 文件或粘贴文本，预览名称、来源、大小、摘要及只读范围，然后明确“导入并授权只读”。不会默认采用 S02 验证附件或要求编辑宿主登记文件。资料列表可刷新/重开；工作表单明确选择一份有效资料，保存绑定与版本，现有工具及模型循环实际读取该引用并保留来源。导入、授权、登记工作均零模型调用；受控自动工具往返验证另留证。

正文单份 UTF-8 64 KiB，上限 16 份且总计 1 MiB，名称 1–120 字符、不含路径/控制字符，正文拒绝 NUL，非空，类型只支持 txt/md；来源只允许 file/paste。导入失败不留下正文、目录或权限；未提交正文只驻留组件内存，取消/切主体/AU/服务后清除。没有未采用服务器暂存对象，因此不需要清理另一份临时权威数据。上限包含已撤销记录，原历史不删除，不声称无限资料存储。

## 公开合同

- `GET /api/v1/work/materials?organization_id=...` -> `core.materials.v1`、organization_id、AU version、access.principal_id/can_manage、materials。仅投影名称、稳定 id、source、scope=au_read_only、version、sha256、bytes、read_allowed、创建/撤销依据；不含正文、宿主路径、私有配置。发现只读，不建表、不迁移、不授新权。当前有权治理者按现有 AU 读取边界访问，治理未激活可见准备缺口，写入仍拒绝。
- 沿五字段 `POST /api/v1/work/commands`，新增 `import_material`：data={material_id,name,content,source,reason}；`revoke_material`：data={material_id,expected_version,reason}。成功回执含 metadata material；拒绝/unknown 沿原协议，原请求查询仍为 governance receipts。实际主体/当前 AU version/有效治理在接受事务内重验。导入命令落盘前以 content_sha256 替换正文，原请求比较使用同一规范化载荷；正文仅存私有表，回执和审计不回显正文。重复 ID 同载荷返回原回执，不更新版本/计量；异参 409，跨主体 403。
- `start_work` 向后兼容既有宿主 materials_root。新资料选择额外带 `material_version`，必须与该 AU 当前 id/version/read_allowed 一致；导入资料缺少版本不能降级宿主路径。Work 记录 metadata snapshot，后续调用核对当前有效资料。没有 material_version 的历史宿主 Work 继续原有路径校验，不能读到导入资料。
- 新资料只含一份逻辑文档；原 list_documents 返回其安全名称，read_document 的 path 必须恰等于该名称。同一 Work 的 Member/Definition/Mandate/attempt 与工具许可仍逐次检查，来源回执额外绑定 material_id/version/sha256。撤销增加资料 version 并关闭 read_allowed，保留正文/原请求/Work/已发生用量。不能恢复、修改或自动换版本；需要新版时显式导入另一个稳定 id 并登记新的授权范围。
- 导入资料的显式 invoke_tool 实际读取并校验正文，但即时和持久回执仅返回 sha256/bytes 与工具来源，不回显正文；原 ID 查询/重复提交保持该元数据事实，撤权后不披露正文。正文只经现有受权自动工具私有上下文供下一轮使用，每次重验当前资料绑定。历史宿主工具 text 回执保留兼容，不新增正文读取端点。

## 唯一事实、事务与恢复

GovernanceStore 仍是唯一 AU 事务和审计写者。domain/materials 只拥有纯元数据规则；MaterialStore 在调用方 cx 内持有私有 work_materials 正文，不新建数据库/文件；application/materials 编排两种命令和只读投影。元数据、正文、命令、审计在同一 SQLite 事务保存/回滚，旧 AU 无该表时可只读，第一次明确成功导入才建表。公开 state 只有元数据；摘要/字节数逐次验证正文完整性。

documents 的 scoped WorkDocuments 接口统一 list/read/binding；导入分支由明确 material_version 选择，失败无宿主 fallback。WorkService 唯一执行者接入同一接口：显式 invoke、派发前、工具执行、结果接受和历史工具上下文再披露均核对绑定。原宿主绝对路径摘要和导入 id/version/digest 各有确定 binding，不宣称跨 DB/文件全局事务。已合法发出的远端请求撤权后仍保留事实与预约，拒绝采用内容，不重派 unknown。

前端沿 useWorkCommand 的同一身份/版本/原 ID 恢复所有者扩展材料命令，不持久化正文、文件名或草稿。未知导入仅查原 ID，刷新后原 material_id/digest 仍足以核对回执；200 拒绝保留输入，可明确修改后提交新请求；已确认后迟到错误不覆盖结果。目录和选择的读取可取消，写入无自动重试；迟到响应和切主体清内容。

资料命令的浏览器元数据键按当前来源域的 principal/AU/kind 定域，进程 service_instance 仍随引用保留为 originServiceInstance。服务重启后只装载未核对引用、禁止新发送，不自动查询；显式原ID查询必须在当前session/AU检查中匹配原kind/base/actor/material_id/版本/摘要才确认。进程变化不恢复旧attempt，也不授予资料权限；其他主体/AU不消费此键。U120尚未发布，没有旧版资料缓存迁移或双键fallback。相同当前scope的迟到401/403即使用户后来编辑也清除整个草稿；普通错误和成功预览按草稿generation隔离。

## 责任、复杂度与实施计划

ArchitectureReviewRequired: yes，既有单 SQLite/治理根方向内新增私有正文和版本化公开材料合同；决定见 ADR-0007。新增两个窄所有者，不继续把导入编排堆入 WorkService。原 S02 私有 model_materials 保留连接验证用途；原宿主适配器保留历史已授权工作，不双写/双派发/读迁移。本片不退役真实资料、不删除外部持久状态。

TDD Route: strict；Mode off，用户/AGENTS 明确 strict 覆盖。顺序执行：

1. 冻结本文/ADR/文件责任；HTTP 测试观察缺少导入/目录/版本绑定的真实 RED，再最小实现 metadata、私有正文和公开导入/撤权/读取；测试事务回滚、原 ID 重开、限制和只读零写入。
2. 同一 Work 实际只读工具 RED/GREEN，再接入所有执行/派发/上下文接缝；跨 AU/主体、撤权、篡改、版本变化、路径逃逸拒绝，原模型调用事实/unknown 保留；保留历史宿主资料回归。
3. React 资料页/预览与原工作选择渲染 RED/GREEN，扩展原命令恢复；工作不手填宿主引用，选择不静默换资料，返回原组织；正常/拒绝/unknown/断网/存储失败/身份与版本变化及键盘有具体断言。
4. 真实本地认证/HTTP/SQLite/浏览器五宽 1440/1024/768/390/320，受控模型实际读取新导入文本并在下一轮接收原来源；真实模型调用 0。固定 npm check、Python 全量及另一工程角色权限/持久化复核。
5. 仅提交任务路径、推送准确 SHA 并验七项 CI，按用户已授权直接更新 rewrite 或可用 PR 交付，原保护恢复实读；在线完整验收才 done。U-112 仍需整体准备旅程验收，不自动关闭；不执行 U-121/U-124，不花费真实模型、不部署/迁移。

主要路径：domain/materials.py、adapters/material_store.py、adapters/documents.py、application/materials.py、application/work.py、GovernanceStore 完整性接缝、server.py；web api/types/client、features/materials、CoreWorkRegistration、useWorkCommand；新行为测试与本卡证据。现有共享 Work/runtime/调度所有者不另起框架；每次修复按实际接缝归属并保留失败历史。

源码复评：当前新组织 work 路由仍是缺口页。U120 只接通工作资料准备分区，消费既有 CoreWorkRegistration 和 Work 读取，显示所选绑定及真实工具摘要；不挂载旧 WorkPanel 调试控制台，不新增浏览器调度器。真正自动工作意图/持续推进/采用交付由 U121 冻结与验收，受控工具实际读取另由本卡浏览器和现有服务链证明。
