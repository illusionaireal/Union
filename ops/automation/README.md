# 自动推进（goose 内置定时调度）

用户 2026-11-07 要求：了解在线 Kanban 后建立**定时任务**持续推动开发直到全部任务完成，并及时同步 Kanban。
实现方式为 **goose 自带调度器**（`goose schedule`），不依赖 Windows 计划任务。

正式事实仍只有一份：`management/project.json` + 在线 UNION Kanban（见 [management/KANBAN.md](../../management/KANBAN.md)）。本目录只提供选卡与调度层。

## 组成

| 文件 | 作用 |
| --- | --- |
| `pick-next.mjs` | 只读在线 `GET /api/board`，输出 JSON：`resume`（在制卡，优先续做）、`ready`（依赖已 done 的 backlog/ready）、`blocked`、`done`、`next`、`all_v1_done`。 |
| `union-autodev.yaml` | goose recipe：一轮推进一张卡的一个可验证子步骤（严格 TDD），提交推送并**即时**同步在线卡与主账。 |

## 调度注册

```bash
goose schedule add --schedule-id union-autodev \
  --cron "0 */2 * * *" \
  --recipe-source "D:\SynologyDrive\project\Union\ops\automation\union-autodev.yaml"

goose schedule list                                  # 状态/上次运行
goose schedule sessions --schedule-id union-autodev  # 每次运行的会话
goose schedule run-now --schedule-id union-autodev   # 立刻跑一轮（前台，可中断）
goose schedule remove --schedule-id union-autodev    # 停止自动推进
```

- 当前 cron：`0 */2 * * *`（每两小时整点）。改频率 = `remove` 后重新 `add`。
- 调度器运行在 goose 进程内，需要 goose 保持运行（桌面端启动时已带 `--enable-scheduler`）。goose 关闭时不会触发。
- `add` 会把 recipe 复制到 goose 的 `data\scheduled_recipes\` 存储；**修改仓库里的 yaml 后需重新 `add`** 才生效。

## 每轮行为

1. `node ops/automation/pick-next.mjs` 选卡：`all_v1_done` → 直接结束；`next=null` → 空转结束（不写任何东西）；否则取 `next`。
2. 在制卡（`progress`/`review`）优先续做，避免边做边开新卡推高在制数。
3. 读卡要求 → RED→GREEN→重构 → 跑测试与 `check:management` → 提交推送 `rewrite/charter-v1`。
4. 即时同步：卡片评论、`claim`/`move`/`record`（每次写前读回最新 `version`，HTTP 200 才确认）、`management:render`。

## 边界

允许：读代码文档、写测试与实现、跑本地测试、提交推送 `rewrite/charter-v1`、更新主账/在线卡/视图。

禁止：部署、真实资金、生产数据迁移、改 `main`/`dev`、`git add -A`（工作区有历史未跟踪文件）、覆盖他人未提交工作、伪造证据、把密钥写入仓库/卡片/日志。真实验收按 `docs/FORMAL_DEVELOPMENT.md` 分级，不因自动提交而升级。

## 凭据与代理

`UNION_KANBAN_URL` / `UNION_KANBAN_KEY` 只在 `%USERPROFILE%\.union-kanban.env`；Node 走宿主代理需 `NODE_OPTIONS=--use-env-proxy` 与 `HTTPS_PROXY`（recipe 内已写明）。凭据不进仓库、日志、卡片或提交信息。

## 相关记录

- 2026-11-07 首次启用时，本地分支落后远端 4 个提交（S02 交付），主账 `check` 因缺 `evidence/058-.../finish/*` 失败；已逐文件比对后快进到 `8eb3b74`，本地较新的 `scripts/project-management.mjs`（在线适配器）与 `management/KANBAN.md` 保留，其余未提交副本备份在 `%LOCALAPPDATA%\union-autodev\backups\20261107-0420\`。
- 同日改为 goose 内置调度（原 Windows 计划任务 `Union-Dev-AutoTick` 已删除）；04:27–07:23 两轮在此前实现下完成了 S03 起步（`9d2c3ea`）与 S09 profile 能力声明（`7d32388`）。

## 2026-11-07 22:45：DSH 接手（goose 调度器停止期间）

用户要求由 DSH 接手看板里 goose 名下的任务。本机已无 goose 进程，`union-autodev`（`0 */2 * * *`）不再触发；改为 **DSH 每小时定时任务**（schedule `1b7fe32e`，`FREQ=HOURLY`）按本目录同一套规则推进：

- 选卡仍用 `node ops/automation/pick-next.mjs`（只读在线板），在制卡优先。
- 写回仍走统一适配器；在线卡 PATCH/评论前读回最新 `version`，HTTP 200 才确认。
- 防重复驱动：每轮先看 `git log -1`，若 50 分钟内已有他人/他机提交则只核对不写。

goose 若重新启动，请只保留一条驱动线（二选一），避免两套 tick 同时认领。用户 2026-11-07 已明确由 DSH 接手。
