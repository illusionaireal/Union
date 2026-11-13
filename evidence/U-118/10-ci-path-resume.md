# U-118 Windows CI 路径断言与交付续接

2026-11-13。续接提交 `756dc8196504d58a77c1568620b552410318a339`；
原分支已推送，但原会话因 GitHub PR 权限中断。当前工程 actor 为 Codex
续接会话，在线成员仍为原 `zbook-codex`（实际 user.id
`363a9919-cc7e-4dbd-8e49-a104a4f0f5ed`），两者分别记录。

## 真实失败及最小修正

[原 Windows CI](https://github.com/illusionaireal/Union/actions/runs/43358646915/job/131666624197)
执行 847 项，9 跳过，唯一失败为
`HistoryTests.test_status_and_inspect_preserve_history_bytes_without_broker`。
Windows TEMP 使用 8.3 短路径，Controller 合法解析为对应长路径；测试直接比较
两种字符串路径，错误判为不同证据目录。其他六项远端检查通过，不能因此忽略此失败。

本机在未改测试或生产代码时，用 `GetShortPathNameW` 取得真实临时目录短名，
令该测试的 TEMP/TMP 和 `tempfile.tempdir` 使用此别名。原用例在 0.569 秒内
复现同一 FAIL（1 项、1 失败）。没有撤掉正常代码或伪造生产返回值。

修正仅将预期目录 `(self.state / rid)` 解析为 `.resolve()` 后比较。
返回目录必须仍等于预期的规范路径；原 run ID、失败依据、保留预约、数据库记录、
仓库文件及历史文件逐字节不变断言全部保留。生产 Controller/Broker/installer 不变。

同一真实短路径条件下执行整个 `tests.test_dev_orchestrator`：42 项，39 通过，
3 跳过，9.407 秒；两项需要本机没有的符号链接权限，一项为 POSIX flock。
这不是对跳过边界的验证，也不替代 Linux/Windows 当前提交的 CI。

## 当前验证与交付

- Node 24.19.0 的 `npm run check` 通过，含管理、动作安全、363 项前端、类型和构建。
  原大于 500 kB 构建块提示仍在；本次不修改前端实现。
- `node evidence/U-110/check-design.mjs` 通过：Main Charter 原哈希、40 条规范、
  10 个旅程、10 个整体验收、47 个链接及历史附录字节保持。
- 新独立 checkout 使用 `.venv`、固定依赖和 CI 相同的 Python 3.12.10 进行全量检查；
  原会话 Python 3.13.14 的结果保留在原证据，不混称为本机运行。
- [PR #90](https://github.com/illusionaireal/Union/pull/90) 已创建，目标为
  `rewrite/charter-v1`。最新原成员/卡片版本确认后，U-110/#64、U-118/#72
  分别 HTTP 200 写入 PR 链接，读回为 review / version 5 和 6；此为历史读回，
  不作为后续操作状态源。当前提交的全量与 CI 结论在 PR/在线交付读回记录。

## 迁移包与现场

用户提供的未提交包基于更早的 `8eb3b74`，不直接覆盖当前源码。
包中 69 个未跟踪文件在原同步目录均存在：66 个逐字节相同，3 个在线适配器/
测试文件已有不同内容。原同步目录的修改、索引、冲突副本和两个压缩包全部保留；
本次只在独立 checkout 接续已推送任务分支。

本次修正不新增模型调用，不操作宿主服务或真实数据；U-111 新入口、完整产品、
真实业务和持续验收仍按各自在线任务执行。原独立规格、代码质量和设计复核见
[coordinator-review.md](coordinator-review.md) 与 [U-110](../U-110/README.md)。
