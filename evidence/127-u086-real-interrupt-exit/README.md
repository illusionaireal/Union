# evidence/127 — U-086 真实中断页面级出口（真实 modeld + 用户已授权模型）

## 结论

22-C 验收的**真实出口**达成：真实 modeld 通道（OpenCode Go `deepseek-v4.1-flash`，用户已无限授权）下，页面经真实 Console 完成登记→run_loop 派发→**在途自动预约取消**→modeld interrupted→unknown 保留→**Console 重启后持久**。13/13 checks，exit 0，单次真实派发。

## 检查清单

1. private ticket page loads — 票据会话（单次消费）。
2. can_start probe — modeld_grant 连接已采用且默认启用。
3. tasks page reachable — 治理 adopt+activate 后核心 tasks 页。
4. work registered and attempt started through the product API — `work-exit` + `work-exit#a1`。
5. in-flight automatic reservation visible — 页面 run_loop 按钮触发后，Core 在 transport.chat 中持久化了自动预约。
6. in-flight reservation carries the line-end id — `work-eddd707a30eac5dc5ffe0108e0fc0e7bc54e0175914b70287039fcfa9dbb5acd`（dispatch.prepare 的线端真实 ID）。
7. cancel accepted by the product — `cancel_step` 命令 200/succeeded，真实模型 streaming 中发出。
8. delivery observation recorded — `cancel_accepted=true`（线端取消送达原请求）。
9-10. **interrupted → unknown 保留**：步进结算为 unknown、cost=unknown、budget.reserved=1（取消受理/interrupted 不证明未执行，费用未知）。
11. **reconciliation 前置保护**：本驱动只断言 unknown 结算必须经原请求核对（不手工释放）；真实模型在取消竞争后返回 interrupted（未完成），按合同保持 unknown 待核对。
12. settled step survives the rebuild — Console kill/同 root 重启后 unknown 事实保持。
13. settle reason persists — 取消与核对理由随事实持久。

## 边界与诚实声明

- 真实模型调用：1 次派发（被取消竞争打断）；无产出/无费用可核，cost_status 保持 unknown——不宣称远端已停止或费用已清。
- 本证据与组合功能实现（PR44 已采用 902b429）互补：功能合同探针（值守 6/6+2/2）为合成替身级；本证据为真实线端级。
- 真实中断历史证据 evidence/112（transport 级）、evidence/114（重启重放）保留；本证据为**页面级+组合实现后**的真实出口。

## 偏差说明

- 无页面截图（evidence/115 有 first-load.png）：本驱动沿用 22-B 骨架的检查/快照
  结构但未截屏；页面渲染事实以 checks.json 的 13 项断言与
  snapshot-before/after-restart.json 的持久字段为准。
- 快照关键持久字段（重启后读取）：step `unknown`/`cost unknown`、
  reason=`模型通道结果未知…work_step_interrupted`、`cancel_requested_at` 已记、
  budget `reserved=1/used=0`——真实中断的未知预约与理由跨重启保持。
