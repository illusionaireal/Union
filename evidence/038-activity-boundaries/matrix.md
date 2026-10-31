# A03 受控证据矩阵

代码：[tests/test_activity_receipts.py](../../tests/test_activity_receipts.py)。四个临时AU测试实际执行Engine/Runner/SQLite、首拍文件和本地锁；时钟/续拍调度受控、执行器/成果/用量为fixture，不是公司运行或供应商证据。

| 用例 | 实际断言 | 边界 |
| --- | --- | --- |
| direct_ttl_boundary... | 同一非空owner真实首拍、文件/锁不变；age0/5 confirmed，5.001/负age unknown；持久running不变、显示unconfirmed、成员blocked，读取不recover/写库/资产；暂停及dispatch分列，第二runner拒绝且factory0、执行0 | 未等待真实5秒，冻结续拍；不证明后台续拍健康/远程网络失联 |
| expired_heartbeat... | 过期但原owner仍持锁，原合法回执正常delivered，一份成果，预算仍1，用量保存、费用unknown | TTL只影响观察，不是租约/取消；不将过期误判为无权返回 |
| actual_runner_startup... | 真实新owner不认领旧run，runner.run实际recover→unknown/needs_review并blocked；旧work/progress拒绝，迟到fail_run无效；全表/资产不变 | 本地受控遗留running，不是真实进程崩溃或供应商迟到网络响应 |
| reconciled_old_receipt... | 正式核对fixture从未外部执行后新run；真实新owner/run活性匹配，仅新run confirmed；旧work/progress/失败回执不改新状态，最后仅新成果，旧历史保留、预算累计2 | 依赖run.status/工作版本和串行启动保护；没有独立epoch或owner-token fencing |

“过期→未确认”“正常接管后旧回执拒绝”是两组不同事实。本轮没有实现或证明跨进程/跨主机独立fencing、强杀取消、真实恢复或任意并发安全。snapshot只读验证比较业务表定义/全部内容及资产字节，不把观察显示状态写回主账；心跳存在/锁持有另行核对。

首次两项失败仅因测试期望usage未含正式标准化cost:null/cost_status:unknown；修正断言后通过，不称生产红绿修复。完整A03/A11/U-041仍需真实环境和整体边界验收。
