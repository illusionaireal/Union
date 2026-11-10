# U-086：失败归档保留已观测的路由结果（回应 PR83 P2）

2026-11-11 早。值守在 `recheck-7dd23fc-20261110` 中把 P2 定在：**durable 失败记录会丢掉已完成的 HTTP 观测**——
`readCancelEvidence` 在本地构造了 `http` 映射，却在返回前 `throw new Error(...)`，写入器只序列化该
error 的 message，因此 work/503、receipt/404、current/200 三个已观测结果都不在归档里。
执行者 DSH 会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`；真实推理 0、无部署/迁移。

## 契约

- `readCancelEvidence` 失败时，抛出的 error 必须携带**已观测的全部路由结果**：
  - `error.http`：键 → `{route, status}`（仅路由与状态，**不含响应体、不含凭据**）；
  - `error.route` / `error.status` / `error.code`：首个失败路由、状态与 Core 错误码。
- `recordEvidenceFailure` 写入的 `<name>-failure.json` 必须保留上述字段：
  `http`、`route`、`failed_status`、`code`；同时保持 `status:'failed'`、`dispatch_count:null`、
  不含 receipt、不含 `new_dispatches`。
- 身份/回执校验、unknown 派发计数语义**不得**放宽或改为 0。

## RED → GREEN

- RED：新增两条测试先失败——
  - `a rejected read preserves every completed route outcome on the error`（error.http 未定义）；
  - `the failure record keeps every completed route outcome`（归档缺 http/route/failed_status/code）。
- GREEN：helper 在抛错前附加 `http/route/status/code`；写入器把四项写入记录。
- 结果：两个套件 **4/4** 与 **5/5** 通过；`npm test -- exit22` **338/338**；`check:management` 37/37。

## 边界

- 记录里只有路由/状态/错误码，没有响应正文或凭据，也没有把未知派发计数写成 0。
- 值守的 6 探针以其 21 输入 manifest 绑定 7dd23fc；本轮改动使其失效。为自检，我按当前 head
  重新计算机械哈希后另存 manifest 再跑（属我自己的验证，不冒充值守签名）。
- 历史 117 B 前快照根因仍未证实；第 4/5 项仍不成立。
