# S05 / U-069 前端独立复核

2026-11-05；评审者：Codex `/root/s05_ui_review`。建议性工程评审，不授予 U-069 完成、真实业务采用、发布或部署权限。

## Findings first：六项问题均已修复，前端范围复核通过

独立检查共发现 2 项 P1、4 项 P2，六项均已修复并独立复核，没有仍开放的 P1/P2。20:48 +08 的 15 项独立反例／有效控制和 20:49 的 92 项正式定向回归全部通过。最终实际浏览器结果为 **21:39:07 +08，50 项检查、45 次提交、21 种命令、零模型派发**；32 组／88 次文字测量全部通过，UI-06 最低对比度已提升至 7.127:1。建议在已声明的 S05 本地受控范围通过前端门禁；这不代替协调者的 G10 其他证据及任务验收。以下保留发现、真实失败和处置；浏览器由实施者独占协调，本评审未另起服务或真实模型。

### UI-01 · P1：提交后身份核验失败会丢弃已经生效的原请求

- 位置：`web/console/src/features/governance/GovernanceForm.tsx:164–181`；`GovernanceProvider.tsx:96–103`。
- 复现：治理 POST 返回 HTTP 200、匹配原请求的成功回执；紧随其后的 `record()` 身份 GET 抛出 `ApiError(401, not_authenticated)`。表单的同一个 catch 将后置核验错误视为命令入口已明确拒绝，调用 `forget(original)`。
- 实测结果：会话存储从含原请求变成 `[]`，界面保留输入并提供重新预览；服务器已经保存的请求缺少恢复入口，新 ID 重试可能重复修改。
- 有效控制：POST 本身明确 401 时保留可编辑草稿；POST 成功且当前主体不变时保留 resolved 原请求。这两项均通过。
- 建议：区分命令 POST 返回的明确未执行拒绝与 POST 后的身份／回执验证失败；后一类继续保留原 kind/ID，只可查询。
- 分类：Implementation Drift，scope: both；S05 §3/§6、G08/G10，R-02/R-05。
- 传输精度：初始反例注入带 `not_authenticated` 的客户端 ApiError；普通 `/api/session` 的实际 401 通常不带 code，未声称该精确形状做过浏览器复现。实际 `session_info` 可能因 AU 完整性异常经 `server.py:207` 返回 `409/incompatible_state`，同样经过原错误分支。修复以响应阶段划分，20:45 独立检查已覆盖后置 401 有／无码及 409/incompatible_state，三者均保留原请求。

### UI-05 · P1：已切换主体后，旧 AU 缓存可复活上一主体的内容

- 位置：`web/console/src/app/workspace.tsx:58–66`、`:169–188`；生产缓存设置见 `web/console/src/main.tsx:8`。
- 复现：A 读取 AU1；同一标签页已经通过新读取确认 B，当前页面为 B 的 AU2；返回 AU1 历史地址并延迟新的 session GET。按生产应用保留 React Query 缓存，原 query key 立即输出 A 的 session 和 AU1 内容。
- 实测结果：新读取尚未结束时出现“原账号私有内容”，此前已确认的 B 主体被旧缓存覆盖。现有多数测试的 `gcTime: 0` 不覆盖此条件。
- 有效控制：同一主体返回自己缓存的 AU，在新的完整读取前写按钮保持禁用，通过。
- 建议：工作台的当前可信身份不能从旧组织 query 缓存重新产生；在 principal/service 变化时隔离或清除旧投影及缓存，保留本人原回执。
- 分类：Implementation Drift，scope: both；S05 §6、G10、X-01(c)。这是多主体能力下必须闭合的原缓存边界，不声称全部代码由本片新增。
- 20:45 复核：跨 principal 的原反例已通过；同 principal 的 AU1 已从最新 `session.organizations` 撤掉、当前为仍有权的 AU2 时，返回 AU1 缓存仍显示原内容。缓存还需受当前服务端 AU 范围约束；相同身份但已撤 AU 权限不能视为有效旧投影。
- 20:48 复核：缓存投影增加与最新服务端 AU 列表的匹配；同主体撤 scope、跨主体及正常同主体缓存三个成对场景均通过。当前身份只由实际未取消的 session 读取更新，旧缓存不再生成当前主体。

### UI-02 · P2：明确会话失效没有触发 AU 投影清除

- 位置：`web/console/src/app/workspace.tsx:65`。
- 复现：当前 AU 已读取，随后 `/api/session` 明确返回 401；该调用位于处理身份变化／403 的 try 之外。
- 实测结果：界面仍保留原 AU 投影，仅设置 disconnected；与 AU GET 403 时的清除行为不一致。
- 有效控制：普通网络中断仍保留标为过期的最后快照且禁止写操作，通过。
- 建议：认证失效与暂时断网分开处理，清除前者的 AU 内容并恢复登录入口；不要为此删除本人待核对请求。
- 分类：Implementation Drift，scope: requirements；S05 §6、G10；此失败路径部分继承 S01。
- 20:45 独立复核：使用实际无 code 的 `ApiError(401)`，旧 AU 已清除；网络中断保留过期快照的控制继续通过。

### UI-03 · P2：采用治理后失去创建另一个 AU 的入口

- 位置：`web/console/src/app/Layout.tsx:278`；`features/governance/GovernanceWorkspace.tsx`；原入口为 `pages/PreparedAU.tsx:69`。
- 复现：账号只有一个 AU；schema 1 准备态显示“创建另一个 AU”，明确采用变为 schema 2 后，Layout 整体替换为 GovernanceWorkspace，其三个页面均没有 `create_v1` 入口，选择器只列已有 AU。
- 实测结果：schema 1 可创建的控制通过；schema 2 中找不到创建按钮。
- 建议：复用已有账号级创建命令入口，保留在治理工作台；该权能不应依赖当前 AU 的治理职权。
- 分类：Implementation Drift，scope: requirements；S01 兼容、S05 §2/§6、F01/P15。
- 20:45 独立复核：治理态工作台已重新提供可用的公共创建入口，准备态控制继续通过。

### UI-04 · P2：登记响应晚于认证轮询时丢失一次性恢复码

- 位置：`web/console/src/pages/Identity.tsx:26–29`、`:77–83`。
- 复现：登记响应 headers 已设置 cookie，JSON body 仍延迟；认证轮询先观察 `authenticated=true`，IdentityBoundary 卸载正在提交的 IdentityForm。随后包含恢复码的 body 到达，恢复码只进入已卸载表单；父级回调设置 completedMode 后重新显示空登记表。
- 实测结果：恢复码控件不存在，表单为空且没有正常返回入口。正文先于认证轮询到达的有效控制通过。
- 建议：从认证请求进行中到恢复码明确确认，保持该表单实例及结果展示责任；只在取得恢复码以后设置 completedMode 不足以覆盖竞态。
- 分类：Implementation Drift，scope: requirements；G01/G10、N02，固定登录与恢复流程。
- 20:45 复核：原“同一 query key 的认证 poll 先到”反例已通过；登记 pending 期间 workspace 实际 session 读取先获得新 principal，造成 identity query key 改变并进入 loading，`!status.data` 提前返回仍卸载原表单。完整 WorkspaceProvider 接缝反例继续失败，恢复码缺失。
- 20:48 复核：pending/completed 表单优先于新身份 query key 的 loading 分支，完整 WorkspaceProvider 反例与正文先到／轮询先到三个场景均通过，恢复码仍由原表单展示。

### UI-06 · P2：治理预览及状态文字对比度不足

- 位置：`features/governance/GovernancePreview.tsx:55`，继承 `components/dialog.css:119`；治理页面的 `.quiet-pill` 继承 `workspace.css:438`。没有建议修改整个旧主题。
- 复现与观察：实际原图已保存在 `ui-browser/before-contrast-preview-320.png`；确认前的执行影响、AU 与基准版本等段落字号为 11px，文字很浅。原样式 `#a58bae` 在 `#f6f8fc` 背景上的独立计算对比度为 **2.861:1**，低于普通文字 4.5:1；这些文字用于判断即将采用的行为，不能视为装饰。
- 同类核查：预览 `.form-note` 受全局 `!important` 固定为 `#806b8c`，在同一背景为 **4.489:1**；预览 `dt` 的 `#68748a` 为 **4.435:1**。治理页面状态 `.quiet-pill` 的 `#69798e`／`#f6f8fc` 为 **4.179:1**，移动端为 9px。普通白底 `.card p` 为 5.236:1、白底 `.form-note` 为 4.773:1、`summary` 为 5.307:1，未将本项扩为全站主题重构。
- 建议：在现有治理样式所有者内，改善预览正文／说明／标签及治理状态文字的字号与颜色；以实际浏览器 computed style 和 320px 原图验证，覆盖所有上述关键文字，保留修改前证据。
- 分类：Implementation Drift，scope: requirements；S05 §6/G10、FRONTEND 可读性。只是本范围的可读性检查，不是全站 WCAG 合规认证。
- 21:16 +08 实际浏览器 RED 已独立复核：32 组、88 次文字测量，四宽度的 computed color／background／font-size 与上述发现一致，追加可读性断言明确失败。预览 `dd` 对比度 9.269:1 是正确控制；检查并非 CSS 字面值镜像。
- 最终处置：只在 `web/console/src/features/governance/governance.css` 增加局部覆盖，未改旧主题。21:39:07 +08 的同一可读性断言通过；本评审独立重算核对 32 组／88 次测量，预览正文／标签／说明／summary 均为 14px，标题 15.75px，治理状态 12.25px，四种宽度一致，最低对比度为 **7.127:1**。最终 `preview-320-dialog.png` 与 `preview-320-confirm.png` 已按原始像素查看，说明及确认按钮清晰、无裁切。UI-06 已关闭。
- 原始证据保存在 `readability-before-contrast.json`、`failure-preview-contrast.json` 和 `before-contrast-preview-320*.png`；最终通过使用当前 `readability.json`／`checks.json`，未用旧 45 项通过冒充本次修复证据。

## 范围、权威与兼容

- Git：`working-tree`；BASE `d9ff5ad23201ee0813707a00f65a0b0d9012a3ee`；HEAD `WORKTREE`；实际分支 `rewrite/charter-v1`。包括协调者明确指定的 governance 未跟踪目录／core-boundary／工作台测试／浏览器脚本，不扩及其他既有脏文件。
- 产品依据：Main Chapter V1 原文及采用记录，`CONTEXT.md`，PRD F01/F03/F07/F09/F20/P15、N02/N04；`specs/053-union-rewrite/s05-contract.md` G01–G10，尤其 §6；S01 兼容契约。
- 架构依据：`docs/ARCHITECTURE.md`、ADR-0006、053 plan §9；界面依据为 product-design 与 FRONTEND 的当前条目。初始根与当前治理者、登录 principal 与 Member、human local_submission 与 AI Execution 分别表达。
- S05 只验收本地受控治理及人类内部文字责任闭环。AI 执行、模型／工具派发、真实资源、外部承诺、自治业务、实体设备、屏幕阅读器和真实用户研究不由本评审证明。
- 工作台只消费服务端 schema 2 `access.commands`；表单的 record 选择及影响预览不承担第二套治理规则。schema 1 采用继续使用受信初始主体边界。
- 旧 CommandProvider 保留 S01 创建及 legacy 协议；新 GovernanceProvider 独立拥有治理命令／回执流程。两个协议不双写同一个 AU 事实。legacy 退役需后续实际调用者迁移及独立授权，本片不能据重复外观直接删除。
- 本次发现的修复应留在既有工作台身份／投影、治理提交流程、Identity 表单和公共创建入口所有者。没有理由增加另一认证源、前端治理授权源或通用恢复服务。

## 独立执行与复核的证据

固定 Node `24.19.0`：`.union/tools/node.exe`；Vitest `3.2.7`。本轮未调用模型或外部业务服务。

1. 定向正式测试：

   ```powershell
   & '.union/tools/node.exe' 'C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js' --workspace web/console test -- src/features/governance/Governance.test.tsx src/app/governance-workspace.test.tsx src/features/commands/core-boundaries.test.tsx src/pages/Identity.test.tsx
   ```

   2026-11-05 20:30 +08，4 files / 71 tests，exit 0。覆盖已有 21 种命令表单、原回执匹配、取消预检、版本冲突、principal/service 变化、unknown、readiness_gaps、核心角色及正常身份登记路径。此结果没有覆盖上述新增反例。

2. 独立临时反例位于忽略目录 `.union/s05-ui-review/`，未改实施者测试：

   ```powershell
   & '.union/tools/node.exe' 'node_modules/vitest/vitest.mjs' run --config '.union/s05-ui-review/vitest.config.mts' --reporter=verbose
   ```

   初次分次结果：`initial-recovery-results.txt` 3 controls pass / 2 fail；`create-entry-results.txt` 1 control pass / 1 fail；`registration-results.txt` 1 control pass / 1 fail；`cache-scope-results.txt` 1 control pass / 1 fail。正式报告保留了全部反例条件和观察值，临时文件不是任务主账或正式能力证据源。

   20:45 +08 `recheck-first-fixes.txt`：15 tests / 13 pass / 2 fail，exit 1。失败是 UI-04 身份 query key loading 与 UI-05 同主体 AU scope 撤销；其余原反例和正确控制均通过。

   20:48 +08 `recheck-complete.txt`：3 files / 15 tests 全部通过，exit 0。该次修复闭合 UI-04/05 扩展边界。

   20:49 +08 `formal-final-tests.txt`：原定向命令再加入 `src/app/workspace.test.tsx`，5 files / 92 tests 全部通过，exit 0；覆盖修复后的 53 项治理、11 项当前权限投影、14 项身份、10 项核心创建权限及 4 项原工作台回归。

3. 实际浏览器由实施者执行；本评审独立读取 `ui-browser/checks.json`、`readability.json` 和脚本、核对失败诊断。修正前查看了全部 9 张原始截图：治理与责任页面各 1440／1024／390／320px，以及 320px 提交预览。责任页 390px 的顶部、长 Work 与授权段另外按原始像素裁切查看；临时裁切只在忽略目录中。最终样式补验后，另查看更新的治理 1440／320px 及 320px 预览顶部／底部两张原图。

   - 环境为 Node `24.19.0`、Chromium `156.0.8078.80`。21:03 的旧结果是 45 项检查，保存在 `checks-before-preview-contrast.json`；21:16 追加可读性断言得到真实 RED；最终 `checks.json` 的 `observed_at=2026-11-05T13:39:07.267Z`，为 **50 项检查、45 次命令提交、全部 21 种命令**，零模型或旧执行派发。真实 React／HTTP／SQLite 流程覆盖独立账号、有限再委托及撤销、保留原 Work 的责任交接、治理接任、响应丢失后重启查询原回执、密码恢复、到期后继及明确退出。
   - 合法 200 字 AU／成员名和不含断词空格的 Work 名均换行，最终页面、表单及确认预览在四种宽度均无横向溢出。目视范围内操作按钮可见且未互相覆盖。长名称会使页面变长；没有据此推断实体设备或真实用户可用性。截图发现的关键说明可读性问题已按 UI-06 修复。
   - 实际键盘证据包括后台轮询不丢草稿与焦点、身份预检中 Escape 取消无 POST、焦点返回原操作入口。没有执行屏幕阅读器验证。
   - 初次“保存后版本未刷新”诊断为脚本读取已折叠 `<details>` 的 `innerText`：回执 version 1、真实 GET 200/version 1，DOM `textContent` 含状态 v1，`expanded=false`。脚本明确展开数据详情后再验证可见版本；未修改产品状态刷新逻辑来迎合测试。原失败文件 `failure-initial-version-check.json`、`failure-collapsed-metadata.json` 均保留。
   - 21:27 的样式补验又在交接后选择授权处超时。原错误保存在 `failure-refresh-timeout.json`；带 600ms 延迟的 `failure-refresh-reproduced.json` 给出可核查原因：脚本只等待身份响应及仍存在的“已连接”文本，打开表单时投影仍为 v27；之后页面和真实 GET 为 v31，目标授权 active、责任绑定 active v1、Work open v3，但已冻结的草稿仍只包含旧授权选项。原超时没有这些完整上下文，不能把后来复现的数据冒充原失败抓取。
   - 最终脚本等待本次新发起的 session 与目标 AU GET、再等对应 AU/version 进入投影元数据；保留的 600ms 慢 AU 读取回归已通过。该处读取 `textContent` 用于投影同步，`runCommand` 仍展开详情后另核对可见回执版本。没有因此改变产品的草稿保留、后台轮询或治理规则；原脚本 `before-refresh-fix.cjs`、失败及最终通过分别保存。

## 基线与证据边界

20:39 +08 已读到 ADR-0006 的 S05 实施决定，以及 ARCHITECTURE、PRD、FRONTEND、product-design 同步条目。它们保留受控工程与自治／真实业务的差别，没有发现需要另立一份 ADR 的新产品决定。057 浏览器结果已有实际文件；安装／发布与任务最终验收由协调者分别核验，本 UI 评审不代替这些门禁。

初次源文件快照（20:39 +08）完整清单位于临时 `manifest-initial.json`；下表文件名均相对于 `web/console/src/`，关键 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| app/workspace.tsx | `c074229c022629ad0606df9e159da94b519a29cee57f4fbfd0f679507dfeca16` |
| app/Layout.tsx | `0378d7853e7c9dac8c8b968700df5e0bb37fa27a04fe135012e9816fb385d3c4` |
| features/governance/GovernanceForm.tsx | `579b2704230c1e485eb910233e4ad9145553edba51aab3ddcc10dba86e4d23ad` |
| features/governance/GovernanceProvider.tsx | `185ef9d4c4f7d21d423754f786c2c6fa3f8d0709b6f93c18ea5c80d26030a5df` |
| features/governance/GovernanceWorkspace.tsx | `1695201a7c6c8a5938d58186302d296220ee6e8bbe829532a749aa61799f50f4` |
| pages/Identity.tsx | `d69b239c0dfdecd9063c1ff301805f8e8228af178ae8f45c6904e0c304c4ee1d` |

最终源文件清单位于临时 `.union/s05-ui-review/manifest-final.json`。与 20:48 功能修复后清单比较，只有治理 CSS 与浏览器脚本变化；已稳定的 15／92 项行为测试未为此重复执行。定向 `git diff --check` 通过。下表为完整仓库相对路径及最终 SHA-256，供协调者与暂存／候选包绑定：

| 文件 | 最终 SHA-256 |
| --- | --- |
| web/console/src/app/Layout.tsx | `86b7eb832eea3dc15912365082ae5fdf90655618920b47abeb80990343eba0b2` |
| web/console/src/app/workspace.tsx | `2d39309f863c15a9e31c34c7498d9166f15e489ad4725355b2a71ce582a58409` |
| web/console/src/features/governance/GovernanceForm.tsx | `dc2e06c758d1627df5d3530d22e1079903202ac5d8962043504fb7fa5366bd0c` |
| web/console/src/features/governance/GovernanceProvider.tsx | `185ef9d4c4f7d21d423754f786c2c6fa3f8d0709b6f93c18ea5c80d26030a5df` |
| web/console/src/features/governance/GovernanceWorkspace.tsx | `1695201a7c6c8a5938d58186302d296220ee6e8bbe829532a749aa61799f50f4` |
| web/console/src/features/governance/governance.css | `c867d58b26d0f1c83e2347a3a7c027926a2d53396856a8892316ad39406b42c7` |
| web/console/src/pages/Identity.tsx | `071219a7fa0211ef33422d792694c2d79a31d10a59276cbc21407a82d34d54d9` |
| scripts/s05-governance-browser.cjs | `21a2d76e5e3d1b91ea6b55a88788b892c5d23bf5dcca69234234c121ec0042da` |

本评审另读回构建产物，确认与最终浏览器记录完全相同：

| 文件 | SHA-256 |
| --- | --- |
| web/console/dist/assets/index-CFPcT5Rn.js | `f0454f38bbd09e8dd920e509556b7e10831c76c69f0e89ab4222539185a4d8ff` |
| web/console/dist/assets/index-CVEbdme-.css | `393612f4cbac24d77a0a56923006bafbc137999060c009f2703d79e1928415bd` |

最终建议：六项发现已关闭，可在上述源码、构建及受控证据范围内采纳本前端评审。未开展屏幕阅读器、实体设备、真实用户研究、自治运行或真实模型验证；工程评审不授予发布、部署、资源使用或后续切片权限。
