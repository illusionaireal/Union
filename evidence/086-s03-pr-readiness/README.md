# 086：交付就绪清单（U-067 / S03 自动执行链，待网络恢复推送）

> **2026-11-08 07:41 协调者更新，优先于下文历史就绪判断：** bdbc382 原 SHA 已由协调者发布为 [草稿 PR #17](https://github.com/illusionaireal/Union/pull/17)，不要重复建 PR；U-078 已随 PR #15 合并。离线独立复核有三个实际 RED：模型派发前没有持久化预约、工具正文未传给下一轮、已完成但撤权被记成未执行。见本地 [复核及可运行探针](../U-067/independent-review.md)。截至 dad454f，这三个核心实现文件没有变化，不能将“真实调用”称为唯一剩余缺口；请先修这三个工程问题。用户本轮 Go 的两次额度已由 U-075 用完，剩余 **0**，下文两次额度是历史授权，不能复用。真实调用 0 的 S03 记录仍保留。

2026-11-08 07:04–07:35。网络自 06:44 起持续中断（GitHub HTTPS 握手失败、看板 `fetch failed`/`no offline fallback`），本地已积累 **9 个提交**。本文件是恢复网络后的**一步到位操作清单**，避免届时再摸索。

## 1. 分支与提交（本地，均已在任务分支上）

任务分支：`dsh/s03-work-runtime`（未切换工作区；共享 checkout 中另有他人未提交文件，故只用指针，不动工作树）。
分叉点：`origin/rewrite/charter-v1` = `8368967`（协调者）。

| # | 提交 | 内容 |
| --- | --- | --- |
| 1 | `d5e779f` | U-078：跨平台目录链接准备 + Windows junction 越界修复（产品修复） |
| 2 | `29f2d5a` | S03.4d：执行绑定宿主实例；重启后陈旧执行不可继续动作 |
| 3 | `6bfb910` | S03.4d：每条执行尝试报告已产生的步进/工具回执数 |
| 4 | `c4dd401` | S03.2e：`run_step` 一次自动模型回合（授权工具 + 回执 + 候选成果） |
| 5 | `fa4e184` | S03.2e：`run_loop` 多回合驱动 + 重放安全 |
| 6 | `b16b1f3` | S03.2e：每次步进披露 usage，费用保持 unknown |
| 7 | `0b32f26` | S03.2e：未知结果保留预约 + `reconcile_step` |
| 8 | `3d08270` | S03.2e：未知即停 + 轮次跟随剩余预算 |
| 9 | `f5bcfed` | S03.2e：modeld 工作通道适配器 + 明确拒绝/未知分离 |

规模：69 文件、+2649/−29（含 8 个证据目录与 5 个新测试文件）。

## 2. 已完成验证（本地，全部通过）

| 检查 | 结果 |
| --- | --- |
| Python 全量 `-m unittest discover` | 见 `python-full.txt`（含新增 adapter 测试） |
| 定向回归（work/governance/models/console/workspace/documents/creation/isolation/adapter） | 132 项通过（3 个 Linux-only 跳过） |
| `npm run check` | 退出 0（前端 206 项 + 管理/计划/动作安全） |
| `npm run check:management` | 退出 0 |
| 真实模型调用 | **0** |

## 3. 网络恢复后的操作顺序

```powershell
# 1) 同步与推送（先 fetch 再推任务分支）
git fetch origin rewrite/charter-v1
git push origin dsh/s03-work-runtime

# 2) 开 PR（目标：rewrite/charter-v1；由协调者审阅）
gh pr create --base rewrite/charter-v1 --head dsh/s03-work-runtime \
  --title "S03 automatic execution loop (U-067) + U-078 cross-platform links" \
  --body-file .union/pr-s03-body.md   # 内容见下节

# 3) 看板同步（#22 四段 checklist + #32/U-078 的归属与完成）
node scripts/project-management.mjs board      # 先读实时 version/owner
node scripts/project-management.mjs record U-078 --actor "dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7" \
  --scope controlled --reviewer <协调者> --evidence evidence/076-u078-link-helper --note "…"
```

**#22 需要按审查处置补的四段 checklist**：① 手工基础（062–069 已交付）；② 自动循环（`run_step`/`run_loop`，079/080/083）；③ 真实有界验收（**待做**）；④ 中断 unknown（082/083，已受控验证）。

## 4. 真实有界验收（唯一实质缺口，需网络 + 宿主通道）

前置：modeld 运行且宿主私有配置就绪（回环地址 + 双令牌）；AU 内已有**已采用的默认连接**（`grant_ref/grant_revision/model/max_output_tokens`）；一次进行中的 attempt；资料目录已由宿主登记。

授权范围（用户已批准）：**≤2 次调用、每次 ≤1024 输出 tokens、仅合成公开测试资料**。

步骤：
1. 通过 `POST /api/v1/work/commands`（`start_work` → `start_attempt`）准备一张工作，`max_calls=2`；
2. `kind: run_loop`；预期 `turns ≤ 2`；
3. 记录：真实 `usage`（input/output tokens）、`cost_status=unknown`、产生的 `tool_calls` 回执（`sha256`）、候选成果摘要；
4. 若通道超时：确认回执 `model_outcome=unknown`、预约保留、`reconcile_step` 可核对；
5. 证据写入 `evidence/087-s03-real-bounded/`，并在 #22 评论里注明"真实有界验收"段落，同时说明费用未知项。

## 5. 已知限制（不得在验收时隐去）

- `ModeldWorkTransport` **未对运行中的 modeld 跑过**；事件与 `result` 字段形状取自既有 `ModelServiceTransport` 用法。
- 适配器目前**未在宿主自动装配**：需要显式把 `ModelServiceClient` + AU 连接配置注入 `WorkService.transport`（下一步的接线工作，或由宿主启动参数提供）。
- 本轮所有验证均为本机 Windows + 临时目录 + 测试替身；未部署、未迁移真实 AU、未花费真实额度。

## 更新（2026-11-08 07:19，网络仍不可达）

本地提交增至 **12 个**，在 086 之后续加了三个（均属 S03.2e 通道接线，不是新功能面）：

| # | 提交 | 内容 |
| --- | --- | --- |
| 10 | `f5bcfed` 之后 | 见 085：modeld 工作通道适配器（明确拒绝 / 结果未知分离） |
| 11 | 087 | 宿主可通过 `transport_factory` 装配通道；`step_plan` 带出该工作的模型连接；`modeld_factory` 便利装配 |
| 12 | 088 | `Console` 仅在宿主设置 `UNION_MODELD_CONFIG` 时装配通道；未配置保持"无通道"拒绝 |

至此 **S03 自动执行链的代码侧已闭环**：目标 → 工作/授权/预算 → 通道（宿主按需装配）→ 模型回合 + 授权工具执行 → 回执/候选成果 → 用量披露（费用 unknown）→ 未知保留预约 + `reconcile_step` → 循环（未知即停、预算内轮次）。

**唯一剩余缺口 = 真实有界验收**（≤2 次调用、≤1024 输出 tokens、仅合成公开资料），需要：网络恢复 + modeld 运行 + 宿主设置 `UNION_MODELD_CONFIG` + AU 内已采用默认连接。

因此后续轮次在没有网络时不建议再新增功能代码，只做复核与交接维护；恢复后按本文件 §3 的命令推送/开 PR，再按 §4 做真实验收。

## 追加验证（2026-11-08 07:34，离线启动冒烟）

网络仍不可达，但在本机跑了真实启动冒烟：`python scripts/check_console_start.py --output …`

**5 项全部通过**（`startup-smoke.json` / `startup-smoke.txt`）：

1. `npm start` 能构建并服务深层 SPA 路由；
2. 同源 CSP 存在；
3. 构建后的 JS 资源可被服务；
4. 私有一次性会话可连接，且**不创建、不运行组织**；
5. 未知资源不会返回 SPA 外壳。

真实模型调用 0。这补上了"产品能真正启动并服务前端"的离线证据（此前只有单元/集成测试与浏览器脚本历史记录）。

## 追加验证（2026-11-08 07:39，真实 Chromium 浏览器门槛）

网络仍不可用，但两个实际浏览器验收在本机通过（Chrome，临时目录 + 回环替身，真实模型调用 0）：

| 检查 | 结果 | 日志 |
| --- | --- | --- |
| `npm run test:workspace`（React 工作台，含我新增的 V1 工作面板/操作） | **71 项通过** | `browser-workspace.txt` |
| `node scripts/check_core_creation.cjs`（S01 创建/重开门槛） | **30 项通过** | `browser-core-creation.txt` |

这两项此前记录于 S01/workspace 证据，本轮是在**含 15 个本地提交的当前树**上复跑，确认新增的自动执行与通道装配没有破坏既有用户流程（创建、重开、模型配置、工作页）。


2026-11-08 07:41 协调者复验：已从固定提交 dad454f81e242883cdca98246cd9e53ea847bbd6 导出独立源码，重跑 evidence/U-067/independent-review-probes.py，结果仍为 3 tests / 3 failures / 0 errors（2.841 秒）。失败位置与首次复核相同；无真实模型调用。

## 合并安全检查（2026-11-08 08:00）

对比本分支**全部改动文件（103 个）**与协调者当前**未提交的 17 个文件**（`AGENTS.md`、`HANDOFF.md`、`PROJECT.md`、`TASKS.md`、`management/*`、`ops/automation/*`、`scripts/kanban-client.mjs`、`scripts/project-management.mjs`、`scripts/union-board-mcp.mjs`、`package.json`、`specs/053-union-rewrite/plan.md`、`tests/union-board.test.mjs`、`.gitignore`）：

**重叠文件数 = 0**。因此按顺序先由协调者提交其运行态统一改动、再合入本分支时，不会产生文本冲突；本分支不修改主账/看板适配器/ops 脚本。

（注意：如果协调者的 `project.json` 或生成视图在我推送前又被改动，仍以实时文件为准；本分支没有触碰这些路径。）

## 推送成功与新根因（2026-11-08 08:10）

**20 个提交已推送**到 `origin/dsh/s03-work-runtime`，远端 SHA 经 GitHub API 读回为 `bb1b417774ffc080a54fc939fd31984df2be2f05`。

**断网根因已定位**：并非主机断网，而是**代理变量指向坏代理**。排查证据：

| 探测 | 结果 |
| --- | --- |
| `curl` 直连 `https://github.com` | **HTTP 200**（0.54s） |
| `curl -x http://127.0.0.1:7897` 同址 | `schannel: failed to receive handshake` |
| `GIT_TRACE_CURL` 抓取 | git 实际在连 `127.0.0.1:7897`（`Trying 127.0.0.1:7897`） |
| 清除 `ALL_PROXY`/`*_PROXY` 后 `git push` | **成功**（`bdbc382..bb1b417`） |

结论：`gateways`/代理进程不可用或对 TLS 处理异常；`git` 通过环境代理变量走了它。**推送时必须清空代理变量**。

残留问题（仍影响自动化）：清除代理后 `git fetch`/`ls-remote` 仍**间歇性** schannel 握手失败（重试 3–5 次仍失败，但 push 与 GitHub API 正常）；在线看板（Cloudflare Worker `union-kanban.361102304.workers.dev`）**直连与代理都超时**，因此看板同步仍无法进行。

## 待协调者执行（网络通道具备时）

1. **开 PR**：`https://github.com/illusionaireal/Union/compare/rewrite/charter-v1...dsh/s03-work-runtime?expand=1`（本机无 `gh`，也无仓库 token，无法代开）。
2. 审阅并合入；合并前建议先提交协调者自己的运行态统一改动（已确认与其 17 个未提交文件**零重叠**）。
3. 看板 #22/#32 的状态同步需等 Cloudflare Worker 端可达后补。

## 进一步定位：全局 gitconfig 里的按 URL 代理（2026-11-08 08:25）

`git config --show-origin --get-regexp proxy` 显示：

```
file:C:/Users/Benedict/.gitconfig   http.https://github.com.proxy   http://127.0.0.1:7897
```

这解释了为什么清空 `*_PROXY` 环境变量后 git 仍打印 `Trying 127.0.0.1:7897` / `CONNECT: no ALPN negotiated`：git 对 `github.com` 单独配置了代理，而该代理的 TLS 已损坏。

- **唯一一次成功推送**（`bdbc382..bb1b417`）发生在设置了 `NO_PROXY=github.com` 的那次调用——`NO_PROXY` 覆盖了按 URL 的代理配置。
- 用 `git -c "http.https://github.com.proxy="` 强制直连后再试，得到 `Failed to connect to github.com:443 after 21085 ms`：直连 TCP 本身**间歇不可用**（同一时刻 `curl` 直连同一端点返回 HTTP 200），说明是进程级/路由级的不稳定，而非纯配置问题。

**建议（需要用户或协调者执行，我不改用户全局 git 配置）**：

1. 修复 `127.0.0.1:7897` 的代理，或从 `C:\Users\Benedict\.gitconfig` 移除/替换该 `http.https://github.com.proxy` 行；
2. 或在每条命令上临时覆盖：`git -c "http.https://github.com.proxy=" push …` 并配合 `$env:NO_PROXY='github.com'`；
3. 看板（Cloudflare Worker）另有一层不可达（`cloudflare.com` 可达、该 Worker 超时），需要单独排查。

**当前远端状态**：`origin/dsh/s03-work-runtime` = `bb1b417`（20 个提交，含全部产品代码与证据）；本地另有 1 个仅文档提交 `abd9f35` 未推送。
