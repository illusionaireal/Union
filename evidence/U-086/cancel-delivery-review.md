# U-086：22649f4 的取消送达与页面续接仍缺持久恢复边界

最新读回：作者随后发布 `22649f49000496ff6e298c6c4d1197975d45e14a`，产品
差异仅WorkExecution，另合并旧评审与页面证据；服务端产品字节与abfa9ee
一致。评论144及fresh revision500/#40 v9确认原owner/progress保持。已fresh fetch并
重新导出准确源码复验：原自动取消路径1通过、预算4通过、原页面5通过；
新增事务/回执/身份6项仍全部失败（7.059s）。下面abfa9ee观察保留为历史，
不是把旧失败冒充新head结果。

依[补充合同](cancel-delivery-contract.md)进一步验证页面完整路径，新2项
DOM反例均失败，扩展集合2失败/5通过（3.50s）：

- 页面实际发送run_loop后响应丢失，服务端投影显示原自动step仍reserved。
  刷新保留原run_loop ID，但点击可见的“取消本次执行”没有发送cancel_step，
  命令POST总数仍为1。`cancelLocal()` 的 `reference` 早退把原运行引用变成
  取消阻塞；未决运行与取消应分别持有原ID。
- 取消成功后刷新，原取消查询入口消失。保存的cancel引用已经resolved，
  `reference` 选择只找未决引用或当前run_loop/start_attempt种类，遗漏已成功
  的cancel_step。旧“丢响应取消恢复”通过不能证明成功取消也可核验。

两例通过实际WorkPanel发送命令建立sessionStorage原引用，没有伪造存储或
修改产品。新增断言并入独立 `cancel-page-probes.tsx`，仍不进入默认套件。
最新候选仍不能采用；需要原作者一并修正服务端6项与页面2项，保留已通过
路径。真实模型调用0。准确来源及每轮日志hash均见同目录JSON。

2026-11-09，回应 #40 评论142。准确候选
`abfa9ee2d9168ebaf260f1584c1c5c4ea16703b7` 已由 GitHub HTTP200、fresh fetch
和隔离导出副本核对；依赖锁与当前安装一致。原实施者 DSH，本轮单一
codex-home 值守会话独立复核，原 owner/progress/WIP 保留。范围与约1小时
复评已在评论143 GET200读回（revision498，#40 v8）。

**候选暂不能采用。** 原自动请求取消探针现在通过（真实 Core HTTP 到
fake modeld，原取消 POST=1），四项预算保护也通过。此进展保留；新的
事务、回执及身份故障探针6项失败，旧页面探针仍4失败/1通过。

先冻结[送达复核合同](cancel-delivery-contract.md)，再编写
[六项故障探针](cancel-delivery-probes.py)。没有修改被评产品制造失败。

| 准确 abfa9ee 上的行为 | 观察与结论 |
| --- | --- |
| 发送前独立 SQLite 读取取消意图 | FAIL：cancel POST进入时，意图不可见，原取消回执数量为0 |
| 外部等待不占 AU 写锁 | FAIL：独立连接的立即写事务无法进入；不是以机器耗时判断 |
| POST已送达，重启后GET原取消命令 | FAIL：POST `cancel_accepted=true`，GET200返回false及旧“须送达”文案 |
| 错误原模型请求ID回包 | FAIL：仍返回 `cancel_accepted=true` |
| 错误AU身份回包 | FAIL：仍返回 `cancel_accepted=true` |
| 事务提交失败 | FAIL：取消POST=1，Core返回503，唯一取消意图回滚丢失 |
| 原自动取消路径 | PASS：同一model_request_id/AU收到取消；不宣称实际远端停止 |
| 原unknown/单次预算/重启/完成用量 | 4 PASS，未知预约未释放、没有新增模型派发 |
| 实际页面自动取消、丢响应恢复、主体/服务变化 | 4 FAIL；浏览零写入对照PASS，详见此前页面合同 |

六项故障探针每例只派发一次明确替身模型请求，检查结束unknown仍占一个
预约。提交故障只在取消事务退出前注入一次SQLite异常；此前原模型派发
预约不受影响。真实模型调用为0，没有业务部署、迁移或监督变更。

源码原因在 `ai_union/application/work.py`：`store.save()` 执行SQL不等于
事务提交。新增 `channel.client.call()` 仍位于 `store.transaction` 和全局
mutex 内；原事务在退出context时才提交。发送后修改Python回执对象没有
再次写入，所以POST与持久原GET不一致。响应内容则完全未核对，错误
ID/AU同样被记为送达。文档所称“提交后送达”与实际行为不符。

原作者应继续复用GovernanceStore提交原请求关联的意图，离开账户/AU锁后
发送，再以明确的持久观察保存送达结果。保持原回执不可变，可以分别
查询命令受理与送达观察；不能只改返回字符串或内存true。线端身份/状态
校验、丢响应核对及重开恢复须一起完成。不得恢复unknown释放，不另写
模型循环。页面仍须复用原命令恢复和接纳边界，不能依赖仅手工预约按钮。

首轮6失败中的原回执测试错用了不存在的 `/work/receipts` 路由，其404是
探针错误，单列保留；其余5个行为失败当轮已真实出现。改用现有
`/api/v1/governance/receipts?organization_id=...&id=...` 后，GET200实际
复现回执不一致，最终6项均为行为失败。日志留宿主私有目录；
[结果与SHA256](cancel-delivery-review.json)保留两轮分类，不上传私有日志。

复现（固定Python环境，Windows启用UTF-8）：

```text
python evidence/U-086/cancel-delivery-probes.py <exact-source-export>
python evidence/U-086/cancel-route-probe.py <exact-source-export>
python evidence/U-086/cancel-boundary-probes.py <exact-source-export>
python evidence/U-086/run-cancel-page-probes.py <exact-source-export> <node-executable>
```

新探针作为独立候选准入反例，不加入默认应通过套件。PR42只交付评审证据，
不采用abfa9ee产品代码，也不关闭#40/父#22。U106已通过PR39采用、#60已done，
不重复实施。#28剩余真实profile授权、#37获准共享源码、#61身份目录升级
授权仍需各自新事实；这次不重复刷旧求助。NAS最新巡检running/OOM=false/
restart=0，原业务服务未切换。后续由原作者提交修正候选，值守绑定新SHA复核。

本次交付工作树的固定工具链检查：npm check通过（315前端、37管理、9动作
检查），Python全量782项/9跳过/0失败。独立候选故障RED与默认回归GREEN
分列，不把评审证据PR的CI通过当成被评产品候选已合格。新PR head仍需自己
的完整CI与交付评审；没有代替原owner实施产品修复或自行采用候选。
