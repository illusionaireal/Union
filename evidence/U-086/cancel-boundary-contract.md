# U-086 取消预约独立复核合同

2026-11-09；实施候选 DSH，独立复核 actor 为当前单一 codex-home 值守会话。
本轮约 1 小时，一个取消候选的准入结果；不接管 #40，不修改产品源码。
在线 revision487 / #40 v5 仍由原 owner 实施。

依据 [S03 派发合同](../../specs/053-union-rewrite/s03-dispatch-contract.md)
第 3、5、6、8 条及 Charter R-05/R-07/K-04，在新增探针前冻结以下断言：

1. 通过真实 Core HTTP 命令与 SQLite 建立 max_calls=1 的工作，使用产品
   ModeldWorkTransport 向明确 fake modeld 派发一次，返回 interrupted。
   远端执行结果仍未知；本地取消不得把该步进从 unknown 改为 released，
   reserved 必须仍为 1，原 step/attempt/模型引用和费用未知事实保留。
2. 随后提交不同 ID 的 run_step，不得再派发第二个模型请求。不能用
   cost_status=unknown 文案替代调用预算；必须检查实际 fake POST 数量。
3. 取消后重启 Core，原工作/步进/预约仍可读取；重启不能使释放错误消失。
4. 取消已确认 completed 的步进不得抹去 used、原始 input/output 用量和
   原成果引用。这是已结算调用的对照，不是远端取消能力验收。

对撤回的精确候选 0f4abf5 和当前集成 2ff90f1 使用同一组探针。
当前集成及作者重建 head07b6f08 的产品代码尚无 cancel_step；其 HTTP400
拒绝且原事实不变只能算安全对照，不能宣称取消功能 GREEN。

作者 07b6f08 下一步文字提到“只结算 reserved”，仍须区分手工未派发预约与
dispatch.prepare 已提交的自动预约：后者在 transport 运行期间也是 reserved，
必须先核对原请求，不能因该状态名释放。后续新命令的取消意图、原 ID、授权、
并发/丢响应/重启与远端请求核对仍由作者冻结产品合同并执行 RED→GREEN。
本探针不替代完整取消入口验收，不新增真实推理，也不关闭 #40 或父 #22。

收到新 head310c7e1（评论137）后，复评仍属同一取消候选准入结果，补一项
功能断言：通过自动 run_step 实际进入 ModeldWorkTransport，POST 已发生且
原自动预约仍为 reserved 时，当前有权主体的取消须送到原线端请求，并保留
预约。用 fake modeld 在原 GET 内触发第二个真实 Core HTTP 取消命令，检查
准确 (model_request_id, au_id) 的取消调用；不能靠手工 reserve_step 建夹具。
这是 #40 既定“原请求实时输出和取消”的功能 RED，与四项拒绝安全对照分开。
后续若作者冻结其他命令名/输入，应按新公开合同接入同一行为断言，不能把
“未实现”改为通过。单次取消受理仍不证明远端没有执行。
