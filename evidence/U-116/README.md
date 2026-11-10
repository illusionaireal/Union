# U-116 / #70：modeld 固定补丁比较

2026-11-11。准确基线 `cb3fa500847f8dc3ce75488f85fd40d49e69082c`。
PR87 的两个当前 Linux 作业在补丁比较处失败，Windows 作业随矩阵取消；
本机实际 Git diff 与记录补丁的唯一差异为 index 行 SHA 自动缩写长度。
该构建缺陷与 U-101 客户端的 7 项已通过行为验收分开记录。

[冻结合同](contract.md)下，将原完整比较提取为
[verify-upstream.mjs](../../services/modeld/verify-upstream.mjs)，显式选择记录
补丁使用的 `--abbrev=7`，不更改全局 Git 设置，不删除 index、hunk 或正文。
[prepare.mjs](../../services/modeld/prepare.mjs)仍拒绝记录外的已跟踪源码变更。
发布器显式将新 helper 纳入 `source_hashes`；vendor pin、原补丁、依赖锁和
模型运行时均未改变。

[真实 Git 回归](../../tests/modeld-upstream-patch.test.ts)先观察 **2 失败 / 2 通过**：
`core.abbrev=12/40` 使相同内容被原比较拒绝。最小修改后 **4/4 通过**，包含
额外源码拒绝、CRLF/LF 规范化及保留 index 验证。没有破坏产品正常代码制造 RED。

```powershell
node --test tests/modeld-upstream-patch.test.ts
node services/modeld/prepare.mjs
bun test --timeout 30000 services/modeld/test
python scripts/check_model_service_install.py --output <new-private-result.json>
```

使用项目固定 Node 24.19.0、Bun 1.4.2 和 Python 环境。后两项为受控 SDK/
安装检查，不是真实模型或 NAS 部署。Windows 使用正常较短的独立 checkout，
不要为了运行准备脚本而向其他作者的 vendor/依赖目录写入。

本机 npm check（37 管理、310 Node、363 前端）、89 项 modeld 测试、真实
独立目录的完整 prepare 和安装检查均通过。新目录从固定 pin 建立，没有复用
之前失败的依赖安装树；其实际源码/锁/补丁与候选绑定。发布清单复算也确认：
旧收集规则未包含 helper，新规则增加准确 helper 摘要（221→222 构建输入）。
Python 全量 **817 项、8 跳过、0 失败/错误**，最终管理/计划检查通过；
详细结果与摘要见 [validation.json](validation.json)。准确候选 CI 与采用另查线上。
PR87 另有 U-108 浏览器按钮等待超时（作业 130143448789），与此补丁比较问题
分开核对；本卡不声称修复了该浏览器失败。

原 CI 日志、本机 RED/GREEN 和早期环境准备失败保留在宿主，仅提交摘要。
不重跑旧失败来掩盖根因、不把本机通过升级为当前 CI 已采用。此卡只解除
构建比较阻塞；#55 仍须完整 CI 和非实施角色的身份/权限复核，父卡状态不变。

实施 actor：Codex CI duty session `01a1c746-eb38-7711-ad90-290392a05d89`；
online member `codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`，
不是产品 AU 成员。此实现尚未独立评审或采用。

2026-11-11 后续采用：[14/14 当前 head CI 与合并读回](adoption.json)确认 PR88
合并为 `81a0b833fcb3f4318f35cc7a7b329d82a962248d`，tree 与候选相同。
这是构建修复的实施自检与CI采用，不称独立工程评审；U101权限验收仍待非实施角色。
上方候选及失败记录是采用前的历史，不覆盖其当时状态。
