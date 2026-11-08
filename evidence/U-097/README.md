# U-097 / 在线 #51：原请求生成观测候选

2026-11-09。基线 `rewrite/charter-v1@cbdbb552`，任务分支
`codex/u097-model-observation`。实际 actor 为本轮 Codex 值守执行会话；在线成员
codex-home，ID `c18f0d21-1d63-4e37-af3e-2dbb78d75995`，不是产品 AU 成员。
在线 #51 v1→v2 的认领 HTTP200 后再次GET200核对；范围/4–8h估算在评论106。
父 #28 原负责人、blocked/WIP、真实资源和完整验收保持。

2026-11-09 值守接续：终态观测遇原连接停用/改版仍保留正文的缺口已按
RED→GREEN修复，详见[补充验证](projection-access-followup.md)。原始验证与失败历史
不覆盖；候选仍须另一工程角色复核，不把实施会话的接续检查称为独立批准。

## 可检查的变化

V1 模型页可选择一个已存在的 S02 验证 attempt，展开其生成观测。在模型尚未
完成时显示已保存文本；断线保留带提示的旧前缀，重连按原序号去重。新一轮
attempt 出现不会擅自切换观测对象；收起即停止轮询。内容只在组件内存中。

新 GET 投影读取既有 `model_attempts.result.events`，不建立第二份事件存储，
不补采、不重派发、不续跑。当前 AU governor 和原 modeld grant/AU/model/revision
分别核对，锁外 grant GET 后重验会话/角色/连接；新增验证完成元数据不等同撤权。
仅普通文本与 read_document 工具名称可见，native、reasoning、工具参数和错误
正文仍私有。已知撤权、响应/事件身份错配清除旧内容，原事实/用量不改变。

冻结合同：[s09-model-observation-contract.md](../../specs/053-union-rewrite/s09-model-observation-contract.md)。
实现：[model_events.py](../../ai_union/application/model_events.py)、
[ModelStream.tsx](../../web/console/src/features/models/ModelStream.tsx)。
旧 ModelRunStream、S03 工作循环、监督脚本和宿主配置未改变。

## 失败与验证

- HTTP初始6项全部RED：接口404，包含在途正文/重启/分页/零新派发及授权反例。
  最小实现后6项通过；增加元数据并发反例得到真实403 RED，修正为只比较连接
  身份/授权版本后，完整10项HTTP/SQLite反例通过。
- DOM初始10项全部RED：缺少生成观测入口。最小GREEN后，两个畸形响应反例
  复现旧正文未清除，再修正并通过。下一attempt选择测试第一次未等待新选项，
  因此最初“通过”不是行为证据；补齐等待后1失败/14通过，固定原选择后15通过。
- 实际Chrome + 当前React构建 + 本地HTTP/SQLite + 明确modeld替身，6项通过：
  在途正文/native隐藏、后续序号、断线/去重、正常主机重开、1440/390/320布局、
  grant撤销清除。夹具预先派发1次替身模型；全部页面观测新增POST为0，重开后
  原派发总数仍1。不是实际模型/账户/profile推理证据。
- 声明检查原2项RED（旧unsupported）后修改为“共同原请求投影受控，真实profile
  流式能力未验”，23项profile/HTTP组合通过。没有把真实调用或取消能力一起升级。
- 完整检查及日志SHA见[verification.json](verification.json)。原失败日志保留于
  宿主私有目录，仓库仅保存摘要，不上传凭据、测试cookie或私有日志。

复现命令：`python -m unittest tests.test_core_model_events -v`；
`npm run test --workspace @union/console -- src/features/models/ModelsStream.test.tsx`；
`npm run check`；`python -m unittest discover -v`；构建后运行
`node scripts/u097-model-events-browser.cjs`。浏览器使用可用Chrome/Chromium；
Python与Chrome路径通过 UNION_PYTHON/UNION_CHROMIUM_PATH 提供。

## 采用边界

这是受控工程候选，须当前head CI与另一工程角色权限/身份复核后采用。本实施
会话不称作独立复核。支持读取S02已保存事件，不是一般Work流、长任务输入或
主动恢复；collector未保存的远端输出仍未知，页内过长内容明确截断。正文不是
正式成果，工具名称不是实际工具执行证明。零新增真实推理、NAS服务切换或迁移。
PR34/35仍由其原评审路径处理，不把本候选当作那两份PR已经采用。
