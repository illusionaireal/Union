# 094：待应用的在线卡更新载荷（网络恢复即可落地）

2026-11-08 13:09 整理。在线看板（`union-kanban.361102304.workers.dev`）在本机被 **DNS 污染 + SNI 级阻断**，多次尝试（直连、代理、5 个 Cloudflare IP、TLS 1.2/1.3、HTTP/1.1）全部失败，因此本文件把**恢复后要写的精确内容**准备好，避免届时重新组织措辞或猜 API 形状。

适用命令就是仓库既有适配器：

```js
import { fetchHostedBoard, findHostedTask, patchHostedTask, commentHostedTask } from './scripts/kanban-client.mjs'
const board = await fetchHostedBoard()
const task = findHostedTask(board, 'U-067')          // 先读实时 version 与负责人
```

写前必须：① 先读实时 `version`；② 带最新整数 `version`；③ 收到 HTTP 200 才确认；④ 409 先读回比较，不盲重试。

## #22 / U-067「输入一个目标，让 AI 交出第一份成果」

**建议 checklist（四段，与审查处置 P0-1 对应）**

```json
[
  {"done": true,  "text": "手工基础：目标→AI 成员/定义/绑定/Work/Mandate、授权资料目录、工具回执、成果采纳与下载（062–069、073–074）"},
  {"done": true,  "text": "自动循环：run_step / run_loop、未知即停、预算内轮次、用量与费用未知披露（079–083）"},
  {"done": false, "text": "真实有界验收：≤2 次调用、每次 ≤1024 输出 tokens、仅合成公开资料；需宿主 modeld 产物与凭据"},
  {"done": true,  "text": "中断 unknown：未知结果保留预约 + reconcile_step 核对，不自动重放（082–083）"}
]
```

**建议 patch**

```json
{"status": "review", "branch": "dsh/s03-work-runtime", "evidence": "evidence/086-s03-pr-readiness/README.md、evidence/092-s03-merged-verification/README.md、evidence/091-s03-modeld-contract/README.md"}
```

**建议评论**

```
自动执行链已交付并推送（分支 dsh/s03-work-runtime，27 提交，远端 5b8e54a）。
范围：run_step（模型回合 + 授权只读工具 + 回执 + 候选成果）、run_loop（未知即停、轮次=min(3, 剩余预算)、原请求重放返回原回执）、usage 与 cost_status=unknown、未知保留预约 + reconcile_step、modeld 通道适配器与宿主按需装配（UNION_MODELD_CONFIG）。
验证：Python 全量 647（8 平台跳过）、前端 206 + typecheck + build、浏览器 71 + 30、启动冒烟 5、适配器回环 HTTP 3、API 端到端 1；与集成分支 9fff477 真合并后 Python 662 通过、无冲突；modeld 源码逐项核对一致（包括其重启把在途请求标记 interrupted）。
未完成：真实有界验收（缺宿主 modeld 产物/凭据），因此不标 done。
```

## #32 / U-078「跨平台测试修复：Linux symlink / Windows junction」

**建议 patch**（先确认在线卡当时实际负责人与 version）

```json
{"status": "review", "evidence": "evidence/076-u078-link-helper/README.md"}
```

**建议评论**

```
共享测试准备函数 tests/links.py：POSIX 建 symlink；Windows 先试 symlink、失败回退 cmd /c mklink /J 目录 junction；都不可用抛 LinkUnavailable，测试 skipTest —— 平台准备失败与产品行为失败可区分；Linux 不再调用 cmd。
顺带修复真实产品缺陷：ai_union/workspace.py 的 validate_config 只用 is_symlink()，而 Windows junction 是 reparse point 会被放过；现改为 _linked()（symlink + reparse point）并要求 item.resolve() 仍在工作区目录内。
验证：test_workspace 12 项（3 个 Linux-only 跳过，原 WinError 1314 消失）、相关 61 项、Python 全量 618→647 项无错误；该修复已随 PR #15 线进入集成分支。
```

## 需要协调者处理的两件事

1. **#31/U-077、#32/U-078 在本地主账缺失**（`management/project.json` 只有 U-079/U-080），在线卡无法通过统一适配器认领/记录；请补账。
2. **PR 创建**（本机无 `gh`、无仓库 token）：
   `https://github.com/illusionaireal/Union/compare/rewrite/charter-v1...dsh/s03-work-runtime?expand=1`
   分支已通过临时克隆的真合并验证（对 `9fff477` 无冲突，合并后 Python 662 通过）。
