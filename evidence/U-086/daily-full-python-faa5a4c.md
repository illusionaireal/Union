# U-086：集成 head `faa5a4c` 上的全量 Python 回归

2026-11-10。执行者为开发会话 `dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`
（与在线成员 HOME-GOOSE / `cafeef64-ac40-4062-97c1-ac82ece0a379` 分别记录）。
本记录只陈述一次真实的、无模型调用的本地回归运行，不改变任何产品行为。

## 固定输入

- 集成 head：`faa5a4ca98331657a78546f9f1480734a959a01f`（PR77 采用后）。
- 工作树：`%TEMP%\union-consolidate` 的 `dsh/u086-page-cancel`，合并后与集成 head 一致，
  运行前 `git status --porcelain` 为空。
- 解释器：`.venv\Scripts\python.exe`，`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。

## 命令

```sh
python -m unittest discover -v
```

## 实际结果

- `Ran 812 tests in 494.027s`
- `OK (skipped=11)`
- 进程退出码 `0`。
- 完整日志为宿主私有文件（147231 字节，SHA256
  `c611ece4aec3c4bc4abaf9e4b12f18f4c4ec06187121684ab08a8bb76701b28f`），未提交，
  其中仅含测试名与本机临时路径。

本次运行**没有**出现历史上记录的环境性失败
`tests/test_workspace.py::test_host_binding_rejects_board_failure_and_private_directory_overlap`
（WinError 1314）；该用例当次正常通过，未为它改动任何产品代码。

## 适用范围与限制

- 这只证明该 head 的本地 Python 测试面全绿；不证明真实集成、用户验收、发布就绪或持续运行。
- 未执行真实模型调用、未部署、未迁移、未切换生产，也未写入其他人未提交的工作。
- Node 侧 `npm test -- exit22`（306/306）在同期同一 head 上另行通过。两者合计构成本 head
  的自动化面证据；真实出口仍按 `docs/FORMAL_DEVELOPMENT.md` 分级分别陈述。

## 追加：PR78 采用后的复跑（2026-11-10 20:14–20:23，分支 `408a4ab` 含集成 `7b018f3`）

集成采用 PR78（U-092 评审输入修复）后在同一 checkout 复跑，确认无回归：

- `python -m unittest discover` → **Ran 817 tests in 531.837s / OK (skipped=11) / exit 0**
  （= 原 812 + PR78 新增 5；私有日志 sha256 `85f8a9de…`，未提交）
- `npm test -- exit22` → **306/306 通过**
- `npm run management:render` PASS（15 模块 / 8 里程碑 / 80 任务）；`check:management` 37/37

本轮未执行真实模型调用，未部署或迁移；产品与标准测试字节等于集成 `7b018f3` 加本卡证据文档。


## 追加：集成 d27d543 合并后的全量（2026-11-11 07:0x–07:1x，分支 55bb137）

合并集成 `d27d543`（含 PR87/PR89 等）并叠加本卡 PR83-P2 修复后复跑：

- `python -m unittest discover` → **Ran 834 tests in 533.595s / OK (skipped=11) / exit 0**
- `npm test -- exit22` → **338/338**；`check:management` 37/37；`management:render` PASS（15 模块 / 8 里程碑 / 81 任务）
- 未执行真实模型调用；未部署或迁移；产品与标准测试字节等于集成 `d27d543` 加本卡驱动/证据改动。
## 追加：`npm run check` 全绿（head 1b94cae，2026-11-11 07:3x）

- `check:management` **37/37**；Node 全套 **341/341**；前端 **29 文件 / 363 项**全过（含 tsc + build）。
- 该 head 同时含：PR83-P2 修复、网络/JSON 中断结构化诊断、重启比较「计数未知」标注；Python 侧自 834/834 后无改动。
## 追加：`npm run check` 全绿（head c5bdc3b，2026-11-12 19:5x）

- `check:management` **37/37**；Node 全套 **348/348**（含 P2 续例的四反例 + 两合法控制）；前端 **29 文件 / 363 项**（tsc + build）。
- 该 head 含：P2 二次修复（后续严格校验失败保留四路安全 HTTP 诊断）+ 自检记录；Python 自 834/834 后无改动。
## 追加：`npm run check` 全绿（head 93b8628，2026-11-12 20:4x）

- `check:management` **37/37**；Node 全套 **352/352**（含 cancel-facts 4 项与校验诊断 6 项）；前端 **29 文件 / 363 项**（tsc + build）。
- 该 head 含：P2 两轮修复（`c4b95b7`、`a1d9957`）+ 复审包 + 文档增量；Python 自 834/834 后无改动。
## 日常全量（2026-11-12 21:3x，head dfd4dff）

`python -m unittest discover` → **Ran 834 tests in 573.043s / OK (skipped=11) / exit 0**。
产品源码该 head 与值守复验过的 `5545d4f` 逐字节相同，故结果与 11-11 一致；仅 JS 驱动/测试/证据变化。