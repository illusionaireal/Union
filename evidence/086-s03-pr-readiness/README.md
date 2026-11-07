# 086：交付就绪清单（U-067 / S03 自动执行链，待网络恢复推送）

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
