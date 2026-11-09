# U-075 取消历史读取：独立复核与采用

2026-11-10：PR73 准确 head `a7c80cc649b44c439359f0b8f5ce5970dcc5ca6f`
通过 14/14 当前 CI 后，已合入 `rewrite/charter-v1` 为
`b4e435b78280cee94e9a5d17ed97923f999cc71f`。受评与合并 tree 均为
`063e65ffc1b0b2f5579a75e42f314f1d4f9ffa5c`，GitHub HTTP200 与 fetch 已读回。
[独立工程复核](https://github.com/illusionaireal/Union/pull/73#pullrequestreview-5833445067)
由当前 codex-home 部署/集成值守完成；产品实施为另一开发会话
`01a1c217-f4aa-78e3-830b-173a7b72e707`。本次在线认证成员为
HOME-GOOSE / `cafeef64-ac40-4062-97c1-ac82ece0a379`；保留 #28 原 owner。

检查全部 12 个变更文件，4 个产品/测试源码摘要与作者记录吻合。
`modeld.publicRequest`、`Journal.authorize` 与核心 `check_grant` 的字段逐项对照：
取消不能跳过当前主体、治理者、连接版本和实时 grant/AU/model/revision；
只对严格确认的本地停止与原 interrupted/cancel_requested 允许历史读取。
原 ID/AU/digest 和事件范围仍校验，GET 不执行、不采用、不退款。

独立验证均使用准确 Git 导出的隔离副本：

- 24 项已有 HTTP、恢复和 profile 回归通过。
- [7 项额外 HTTP/SQLite 探针](http_probe.py)通过，覆盖原文本/预约重开、
  grant 身份/版本/撤销与不可用、原请求/事件错配、查询中登出/停用、私有参数隔离。
- 未改产品源码的 `e42fd823` 原父快照运行相同正常取消探针，确证 `403 != 200`
  的 RED；候选通过。不撤掉当前正常代码制造失败。
- [真实 Chrome 探针](browser_probe.cjs)与[隔离宿主](browser_host.py)的 7 项检查通过：
  正文与身份、刷新/重启、当前撤权清除、原请求/unknown 占用和限定能力说明。
  此浏览器夹具 fake 模型请求 1，观察浏览器 POST 0，真实调用 0。
- 准确候选类型检查及构建通过；全量 Python/npm/模型服务/浏览器由该 head 的
  14 项 CI 通过确认。本次没有再次执行真实模型验收。

源码、日志与探针摘要见 [verification.json](verification.json)。公开探针由本次
私有复核脚本移除宿主绝对路径后提供；原日志摘要保留，未提交原日志或业务数据。
运行方式（项目根目录，使用项目固定 Python/Node 与已安装的 Chromium）：

```sh
python evidence/U-075/go-deepseek-2026-11-10/duty-review/http_probe.py
npm run build:console
node evidence/U-075/go-deepseek-2026-11-10/duty-review/browser_probe.cjs
```

浏览器可用 `UNION_PYTHON`、`UNION_CHROMIUM_PATH` 指定实际安装，输出默认在
`.union/U-075-review/`。原父 RED 可在独立的父提交导出副本上设置
`UNION_U075_REVIEW_ROOT`，以 `UNION_U075_REVIEW_FIXTURES` 指向候选的
`tests/test_core_model_events.py`，只运行正常取消/重开的单个探针。

作者的 4 次真实调用、资料/工具上下文、1180/330 已知 token 小计与一次未知中断、
16 项真实浏览器记录已按公开报告和驱动审阅；本值守没有直接读到作者私有原库/日志。
上述独立 fake 检查不升级这些真实证据。Go 指定模型只有 Chat Completions；
Responses #52/#53/#54、长任务新输入、父 #28 完整验收和持续运行继续分别保留。
本次没有新真实推理、部署、迁移或监督配置变更。
