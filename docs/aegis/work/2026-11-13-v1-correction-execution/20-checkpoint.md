# 续接检查点

## Current Checkpoint

- Current todo: U120最终验收、任务提交与远端采用
- Active slice: U-120
- Completed todos:
- U119已采用b4371d8，7项CI及原保护恢复实读，在线revision1255 done；U120已在revision1258认领
- U120 HTTP/SQLite与渲染严格RED/GREEN；独立复核发现并修复工具回执正文、直接/编辑后迟到拒读、服务重启原请求入口缺口；受影响58 Python/54 UI通过
- Evidence refs:
- specs/053-union-rewrite/u120-business-materials-contract.md
- Blocked on: none
- Next step: 完成最终浏览器/全量与独立复核读回；初次Python873唯一错误为临时console.lock清理WinError32，原用例单独通过、全量复跑中。最终候选通过后提交/推送/7CI/采用，在线完整验收才done。

## Recent Checkpoint History

## Checkpoint Update

- Current todo: 提交并远端验收U119资源准备
- Active slice: U-119
- Completed todos:
- U119严格RED/GREEN、npm412/Python863含9跳过/80浏览器/独立8+76通过，证据归集；生成vendor补丁精确核对后仅逆向本轮生成差异
- Evidence refs:
- evidence/U-119/verification.json
- evidence/U-119/browser-checks.json
- evidence/U-119/independent-review.md
- Blocked on: none
- Next step: 任务提交推送，准确SHA七项CI成功后按用户授权直接采用rewrite并恢复原保护；在线U119完整验收读回，U112不done
## Checkpoint Update

- Current todo: 实施U119同一组织模型与有限资源准备
- Active slice: U-119
- Completed todos:
- U125/U126/U111采用d48a121；原保护恢复，在线全部done
- Evidence refs:
- evidence/U-119/README.md
- Blocked on: none
- Next step: 渲染行为RED后最小GREEN；受影响真实浏览器、全量及独立权限复核
## Checkpoint Update

- Current todo: 准确最终候选CI通过后直接采用U126/U111
- Active slice: U-126
- Completed todos:
- 本机npm404/Python863含9跳过/创建44/入口116/独立25及四宽通过；消费者焦点等待修复后116复验通过，产品源码未变
- 窗口核对纠正：原67146窗口仍在且最小化，原GitHub规则标签页及登录均有效；Get-Process.MainWindowHandle只显示另一窗口，不能据此判断关闭；无需用户重新登录
- Evidence refs:
- evidence/U-126/verification.json
- evidence/U-126/ci-consumer-repair.md
- evidence/U-111/README.md
- Blocked on: none
- Next step: 推送当前续接事实纠正；准确最终SHA7项CI通过后，私有u126直接更新脚本使用原67146窗口快进rewrite并恢复全部原规则，在线验收读回。
## Checkpoint Update

- Current todo: 交付已验证U126/U111；复验修复候选CI并恢复GitHub网页登录能力
- Active slice: U-126
- Completed todos:
- U125已实际快进采用7756920；原保护恢复，在线done
- 本机npm404/Python863含9跳过/创建44/入口116/独立25和四宽通过；e791已推送，远端旧焦点驱动即时断言失败，产品不改，新增真实焦点条件等待后116复验通过
- Evidence refs:
- evidence/U-126/ci-consumer-repair.md
- evidence/U-126/verification.json
- evidence/U-111/README.md
- Blocked on: 原GitHub窗口关闭；新GitHub标签页未登录。已异步请求用户登录有仓库管理权的账户。CI修复可继续独立推进。
- Next step: 推送消费者修复及准确SHA CI；用户登录后实读账户/仓库规则再直接采用并恢复保护，按最新在线看板记录验收。
## Checkpoint Update

- Current todo: 交付已验证U126并贯通采用U111
- Active slice: U-126
- Completed todos:
- U125已实际快进采用7756920；7项CI与原保护恢复，在线done
- U126与U111本机完整受控：npm404、Python863/9跳过、创建44、入口116、独立25及四宽布局通过
- Evidence refs:
- evidence/U-125/direct-update-adoption.json
- evidence/U-126/verification.json
- evidence/U-111/README.md
- Blocked on: none
- Next step: 任务提交推送，准确SHA远端CI通过后，按用户授权桌面浏览器直接快进rewrite并恢复保护；在线验收记录读回

## DriftCheckDraft

- Scope status: U120候选实现、最终验收进行中；U119已采用，U112不关闭
- Compatibility status: 原S02/S05公开协议、事实写者、当前权限/修订/unknown恢复保留
- Retirement status: 新导入资料不回退宿主路径；原宿主和S02验证资料保留原用途，无双写/双派发/读取迁移
- New risk signals:
- 原资料命令只按principal/AU保留元数据候选，进程变化不恢复attempt；准确SHA七项CI必须全部通过后采用
- Advisory decision: continue
