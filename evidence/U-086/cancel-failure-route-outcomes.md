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

## 自检：用值守 PR83 的 6 探针复跑（2026-11-11 07:2x）

- 候选：`git archive 638e7a0`（含本刀 + 集成 d27d543 合并）→ 隔离目录。
- 探针：从 `b50850d`（PR83）原样取出 `replay-probes.cjs`、`cancel-driver-probes.cjs`、`contract.md`；
  其 `source-manifest.json` 绑定 7dd23fc，本刀改动了 4 个受绑文件，故我按当前 head **机械重算 21 文件哈希**
  另存 manifest（文件中注明「机械重签、非值守签名」），再以 `UNION_REVIEW_CANDIDATE` 指向候选运行。
- 结果：
  - `node --test replay-probes.cjs` → **5/5 通过**
  - `node --test cancel-driver-probes.cjs` → **6/6 通过**（含此前失败的两条「完整 HTTP 失败归档」探针）
- 说明：这是作者的**自检**，不等于值守复验；值守仍需按新 head 重签 manifest 后独立复核。
## 追加：网络/JSON 中断的结构化诊断（2026-11-11 07:2x）

值守在 PR83 README 里注明「未扩展网络/JSON 中断用例」。本轮补上，且不放松任何校验：

- `page.evaluate` 抛出（fetch/JSON 中断）→ 抛结构化错误：`code='transport_error'`、`http=null`、
  `route=null`、`status=null`，message 保留原始原因（`socket hang up`）。
- 响应体形状异常（`status` 缺失/非数值）→ 该路由在 `http` 中记为 `status:null`，
  并抛 `code='unknown_shape'`；**不得**把缺失状态当成功。
- 正常非 200 仍按路由归因（原行为不变）。

RED→GREEN：两条新测试先失败（transport 无结构化 code；malformed 未被识别），实现后
`tests/exit22-cancel-evidence.test.ts` **6/6**；全量 `npm test -- exit22` **340/340**；
`check:management` 37/37。仅 JS 驱动/测试改动，Python 未受影响。
## 自检复跑（新 head b948203）：值守 11 探针仍全绿

`git archive b948203` → 隔离候选；按同一方式机械重签 21 文件 manifest 后运行值守探针：
`replay-probes.cjs` **5/5 通过**、`cancel-driver-probes.cjs` **6/6 通过**——
说明本轮「网络/JSON 中断结构化诊断」没有回归其已有的失败归档断言。仍属作者自检，不等于值守复核。
## 自检复跑（head 744e082）：比较摘要与记录字段改动后 11 探针仍全绿

`git archive 744e082` → 隔离候选，机械重签 21 文件 manifest：
`replay-probes.cjs` **5/5**、`cancel-driver-probes.cjs` **6/6** 通过。
说明本轮对 `exit22-restart-evidence.cjs`（新增 `dispatch_count_unknown` / `identity_equality_only`）
与 `exit22-replay-observation.cjs`（记录统一标注计数可用性）的改动，没有回归值守既有的失败归档与重放断言。
仍属作者自检，不等于值守复核。
## 追加：后续严格校验失败也保留四路安全 HTTP 诊断（2026-11-12，回应评论 433）

值守复核 `0729da8` 的 P2 续例：before/after 两段中**四路 GET 均 200**，随后 current principal
或原 receipt ID 等**严格校验**被拒；但 `failure.json` 的 `http` 为 `null`，丢掉了
session/work/receipt/current 四路已完成的 route/status。源码定位正确：只有非 200 分支附
`error.http`，后续断言未携带该 map。

修复（不改严格性）：
- `readCancelEvidence` 把 GET 后的全部严格校验包在 try/catch 中；失败时**在原始 error 上**
  附加 `http`（四路 route/status，仍不含正文/凭据）与 `route:null / status:null`，
  并把原错误**原样重抛**（`ERR_ASSERTION` 等 `code` 不被覆盖）；
- 不吞断言、不序列化私有正文、不补造 receipt/历史快照、不把未知计数填 0。

RED→GREEN（四反例 + 两合法控制，全为真实行为测试）：
- 反例：session principal 错配、current principal 错配、原 receipt ID 错配、receipt 事实被改
  —— 四条在修复前均因 `error.http === undefined` 失败，修复后均保留四路 map 并严格拒绝；
- 控制：干净读取仍返回证据 + 四路 map；干净读取且 work version 更新仍通过。
- 结果：helper 套件 **12/12**；`npm test -- exit22` **348/348**（342+6）。
## 自检复跑（head c4b95b7）：值守 11 探针仍全绿

`git archive c4b95b7` → 隔离候选，按同一方式机械重签 21 文件 manifest 后运行：
`replay-probes.cjs` **5/5**、`cancel-driver-probes.cjs` **6/6** 通过（含此前失败的两条
「完整 HTTP 失败归档」探针）。说明本轮「后续校验失败也带上四路 map」未回归既有断言；
仍属作者自检，不等于值守复核。
## 自检复跑（交付 head 72dda8a）：值守 11 探针仍全绿

`git archive 72dda8a` → 隔离候选，机械重签 21 文件 manifest：
`replay-probes.cjs` **5/5**、`cancel-driver-probes.cjs` **6/6** 通过。
确认交付 head（含 P2 两轮修复、cancel-facts 与接线测试）未回归值守既有断言；仍属作者自检。