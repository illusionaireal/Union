# 自动推进 tick（定时任务）

用户于 2026-11-07 要求：了解在线 Kanban 后建立定时任务，持续推动开发直到所有开发任务完成，并及时同步 Kanban。

本目录是该自动化在**宿主**上的实现。它不改变产品契约、不新增第二份任务状态：正式事实仍是 `management/project.json` 与在线 UNION Kanban（见 [management/KANBAN.md](../../management/KANBAN.md)）。

## 组成

| 文件 | 作用 |
| --- | --- |
| `pick-next.mjs` | 只读在线 `GET /api/board`，按“未归档 + 依赖已 done + 状态为 backlog/ready + WIP 限额”算出可开工的 V1 卡，输出 JSON（含 `next`、`ready`、`blocked`、`all_v1_done`）。 |
| `union-slice-tick.yaml` | goose recipe：一轮只推进一张卡的一个可验证子步骤，严格 TDD，提交推送，并**立即**同步在线卡与主账。 |
| `union-dev-tick.ps1` | 运行器：加锁 → 载入宿主凭据 → `git fetch`（工作区干净时快进到 `origin/rewrite/charter-v1`）→ 主账 `check` 门禁 → 选卡 → 调 goose → 本轮结束后再读看板核对同步。 |
| `register-schedule.ps1` | 注册 Windows 计划任务（等价于已执行的 `schtasks /create`，供重装/迁移时复用）。 |

## 当前注册的计划任务

- 名称：`Union-Dev-AutoTick`，每 **90 分钟** 一次（登录后重复，仅当前用户交互式运行）。
- 动作：`powershell -NoProfile -ExecutionPolicy Bypass -File ops\automation\union-dev-tick.ps1 -GoosePath D:\goose\resources\bin\goose.exe`
- 单次上限：goose `--max-turns 70`；运行器用 `tick.lock` 防重入（超过 4 小时的锁视为残留）。
- 无模型成本保护：若无满足依赖的卡，或全部 V1 卡已完成，运行器**不调用模型**直接退出；全部完成时写 `%LOCALAPPDATA%\union-autodev\ALL_V1_DONE`。

手工操作：

```powershell
schtasks /query /tn Union-Dev-AutoTick /v /fo list    # 查看状态与下次运行时间
schtasks /run   /tn Union-Dev-AutoTick                # 立刻跑一轮
schtasks /end   /tn Union-Dev-AutoTick                # 中止正在跑的一轮
schtasks /change /tn Union-Dev-AutoTick /disable      # 暂停自动推进
schtasks /change /tn Union-Dev-AutoTick /enable       # 恢复
schtasks /delete /tn Union-Dev-AutoTick /f            # 彻底移除
powershell -NoProfile -File ops\automation\union-dev-tick.ps1 -DryRun   # 只做选卡与门禁检查
```

## 凭据与代理

- `UNION_KANBAN_URL` / `UNION_KANBAN_KEY` 只放在宿主的 `%USERPROFILE%\.union-kanban.env`（运行器启动时读入进程环境），不进入仓库、日志、卡片或提交信息。
- 该环境的 `workers.dev` 需要宿主代理：运行器设置 `HTTPS_PROXY` 与 `NODE_OPTIONS=--use-env-proxy`（Node 24 会把 fetch 走代理），`curl` 侧用 `--proxy`。
- 读取失败（HTTP 非 200 或网络不可达）时运行器**不猜状态**、不推进，只记录原因并退出。

## 每轮的行为边界

允许：读代码与文档、写测试与实现、跑本地测试、提交并推送 `rewrite/charter-v1`、更新主账/在线卡/生成视图。

禁止：部署、真实资金或生产数据迁移、修改 `main`/`dev`、双写或另建状态表、`git add -A`（工作区存在历史未跟踪文件）、覆盖他人未提交工作、伪造证据、把密钥写入任何仓库文件。

## 证据与日志

- 运行日志：`%LOCALAPPDATA%\union-autodev\logs\tick-<时间>.log`（含 `TICK_RESULT:` 结果行）。
- 选卡快照：`%LOCALAPPDATA%\union-autodev\selection.json`。
- 一次性对齐备份：`%LOCALAPPDATA%\union-autodev\backups\20261107-0420\`（本地与远端 S02 交付对齐前的全部未提交文件与清单）。

## 已知前置与限制

- 2026-11-07 首次运行时：本地分支落后远端 4 个提交（S02 交付 `41ae2da`、`8eb3b74`），已按文件逐一比对后快进到 `8eb3b74`，只保留两份确实更新于远端的本地文件（`scripts/project-management.mjs` 在线适配器、`management/KANBAN.md` 适配器章节），其余未提交副本已进备份。
- 自动化只推进**正式主账中存在且依赖满足**的卡片；用户验收、真实供应商/浏览器/部署证据仍需按 `docs/FORMAL_DEVELOPMENT.md` 分级取证，不由定时任务自行升级。
