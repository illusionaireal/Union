# AU 资源和工具申请

这是需求记录与治理响应，不是自动采购或授权。旧章程不会自动加入 request_support；只有章程及有效决策岗位都允许时，模型才会看到该工具。普通工作成员继续报告受阻或交付建议，由决策职责接续。

模型工具输入为 kind（resources/tool）、need 和 reason。宿主生成申请ID，保存提出者、有效任职、证据及时间。决策资料和工作台快照提供最近12项摘要，每项只带最近响应；旧响应事件保留，不将全部历史反复灌入上下文。

受信操作者可使用当前工作台同源命令接口，kind=respond_request，data为request_id/status/reason，携带当前base_version与稳定命令ID。观察者、无组织访问权限的会话不能响应；重试查询原回执。

也可在宿主使用CLI：

```sh
.venv/bin/python -m ai_union --root ORGANIZATION_ROOT support-requests
.venv/bin/python -m ai_union --root ORGANIZATION_ROOT respond-request --request-id REQUEST_ID --status needs_information --expected-version CURRENT_VERSION --board-key-file BOARD_KEY_FILE --reason '请补充数据范围'
```

状态：pending、needs_information、accepted_for_action、declined。accepted_for_action仅表示治理方受理待处理，实际新增额度、宿主工具绑定、章程修订或服务购买仍需各自真实授权和受信操作。它不能作为“已经获得资源”的回执。响应可以使组织在新事件后继续决策，但不能绕过未知执行核对或自动重派。

当前实现不声称已有企业审批系统、付费开通或真实自主申请证据。
