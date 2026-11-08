# U-097：当前连接变化清除已停止的观测

2026-11-09，接续 PR36 `21fbb9bc8980aa85c4fed967809c571d5d57b8cb`。
实施 actor 为当前 Codex 值守会话，在线 codex-home
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`。在线 #51 v3/review 归属读回成功；
这是原 4–8h 观测结果内的小型修复，约 1–2h 含验证，不新增卡或占用其他 owner。

## 问题和变化

原事件查询到终态后停止自动轮询。之后当前模型投影即使已经显示连接停用、
移除或 revision 与原 check 不一致，组件仍显示旧正文。原选中 attempt 消失时，
另一个 fallback 还会自动选择新的请求，与明确选择原请求的合同冲突。

先补充 `s09-model-observation-contract.md`，再添加行为反例。组件现在按当前
原连接的存在、enabled 和 check 对应 revision 决定是否挂载观测；失效即卸载，
清除内存正文/游标并取消读取。迟到响应不能恢复内容。原选中项消失时保留明确
未选择状态，只有用户选择才切换；其他连接及 last_check 的更新保留当前正文。
服务端权限、持久记录、预约、用量和派发代码没有变化。

## 验证与失败历史

- 原产品代码上新增 6 项 DOM 用例：5 失败/16 通过；其中三个反例直接确认旧
  `<pre>` 在连接失效后仍存在，另外覆盖迟到响应和选中原请求消失。独立的
  无关元数据反例一直通过。首版及直接正文断言版 RED 日志均保留。
- 最小修复后 21 项观测 DOM 通过；npm check 通过，含 241 前端、37 管理及
  9 动作检查、类型检查和构建。
- 实际 Chrome + 本地认证 HTTP/SQLite + 明确 modeld 替身：原 grant 撤权场景
  6 项通过；新增连接停用场景 6 项通过。后者先将原替身请求置 interrupted，
  等待产品保存停止状态，再正常重开，按真实版本停用连接并刷新模型投影。
  旧输出清除，无额外事件 GET；两个场景各有一次夹具准备推理，浏览器 POST
  和观测新增模型派发均为 0。三个宽度、原游标、断线与重开断言保持。
  新增场景已接入原 console-browser CI job，原检查/门禁保持。
- 首次新增浏览器场景错误假设重启自动把 running 改为终态，等待超时；没有把
  它算产品 RED。之后明确让替身报告 interrupted，再等待原产品记录确认，
  当前场景通过。该失败日志及摘要保留。
- 完整 Python、精确文件与私有日志摘要见
  [projection-access-verification.json](projection-access-verification.json)。

复现：`npm run test --workspace @union/console -- src/features/models/ModelsStream.test.tsx`；
`npm run check`；固定项目 Python `-m unittest discover -v`。构建后执行
`node scripts/u097-model-events-browser.cjs`；新增分支设置
`UNION_U097_CONNECTION_REVOKE=1`，使用原 `UNION_PYTHON`、`UNION_CHROMIUM_PATH`
和私有 `UNION_U097_EVIDENCE` 入口。秘密及原始私有日志不入库。

## 采用范围

只证明受控观测行为。modeld 外部 grant 的改变仍在下次明确事件读取时由服务端
核对；本修复处理已经收到的本地连接投影变化，不宣称主动推送远端撤权。
没有真实模型调用、NAS 服务切换、数据迁移或持续业务；#28 父卡保持完整出口。
PR36 新 head 须重新通过 CI 和另一工程角色权限/身份复核；实施者不自行批准。
