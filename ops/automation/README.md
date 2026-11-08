# 自动开发调度

## 2026-11-08 生效的交接规则

当前运行态只以在线看板为准。pick-next 与 CLI/MCP 共用客户端；只续做实际 user.id 自己的 progress/review，ready 候选必须无人认领、前置完成，blocked 计入 WIP。无在线配置就明确失败。

开发写入必须在独立 checkout 的任务分支，通过 PR、当前 head CI 和必要的独立复核交付；协调者合并。共享 Synology checkout 不再作为新的自动写入目标。未完成 checkout/账号/调度交接的旧轮次先保留现场，不能删除他人改动。

仓库 recipe 已更新；宿主已注册的副本/DSH 任务是否采用新规则必须逐一读回核实，不把修改 YAML 当成运行配置已切换。五分钟 Union-Deployment-Watch 保持只读巡检；当前没有启用新的自动 Codex 写入，不与开发调度争抢文件。恢复自动写入前由协调者记录唯一写入执行者与运行互斥。

以下为安装与早期运行历史，其中共享路径、直接推集成分支、环境 WIP 等旧行为不再适用于新轮次。

## 初始调度记录

用户 2026-11-07 要求：了解在线 Kanban 后建立**定时任务**持续推动开发直到全部任务完成，并及时同步 Kanban。
实现方式为 **goose 自带调度器**（`goose schedule`），不依赖 Windows 计划任务。

正式事实仍只有一份：`management/project.json` + 在线 UNION Kanban（见 [management/KANBAN.md](../../management/KANBAN.md)）。本目录只提供选卡与调度层。

## 组成

| 文件 | 作用 |
| --- | --- |
| `pick-next.mjs` | 只读在线 `GET /api/board`，输出 JSON：`resume`（在制卡，优先续做）、`ready`（依赖已 done 的 backlog/ready）、`blocked`、`done`、`next`、`all_v1_done`。 |
| `team-feed.mjs` | 只读“团队动态”（活动流 + 留言板），列出未回复的求助与阻塞卡；`--ask` 在留言板发求助、`--reply` 回复指定留言。 |
| `union-autodev.yaml` | goose recipe：一轮推进一张卡的一个可验证子步骤（严格 TDD），提交推送并**即时**同步在线卡与主账。 |

## 每轮先看团队动态（2026-11-08）

用户要求：定时任务**启动时先检查团队动态**，能帮就帮；自己遇到问题也在团队动态求助。在线看板的“团队动态”是本项目的团队协作面（`data-view="activity"`：评论、留言、建/改卡等），留言板是 `POST /api/messages`，两者都会出现在动态里。

```sh
node ops/automation/team-feed.mjs              # 团队动态 + 未回复求助(asks) + 阻塞卡(blocked)
node ops/automation/team-feed.mjs --limit 15   # 只看最近 15 条
node ops/automation/team-feed.mjs --ask "【求助｜U-0xx】现象/已尝试/需要谁做什么"
node ops/automation/team-feed.mjs --ask "补充说明" --reply 4
```

- 每轮先把 `asks`（未回复留言）与 `blocked` 过一遍：能本轮解决的（读证据、定位、给最小修复或明确归属）就做，并在留言板回复结论；解决不了的说明限制与所需信息，不装懂、不重复刷同样求助。
- 自己卡住（缺凭据/需他人判断/环境问题/反复失败）：用 `--ask` 发一条求助，写清 U 卡、现象、已尝试、需要谁做什么；同时在当前卡评论引用该留言编号。
- 求助与回复都会进入团队动态，别人（或下一轮）能看到；不贴密钥、邀请片段、私有主机信息。
- 不因“帮别人”抢占对方在制卡或越过对方授权范围；帮的是诊断、证据、回复与明确责任。

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
