# U-086：原运行与取消请求的页面续接修复候选

后续组合见[页面与作者回执修正](page-combination.md)：保留以下旧候选结果，
新组合对完整原回执一致性作强制断言，不再把此项仅作为已知差异记录。

2026-11-09。作者基线`22649f49000496ff6e298c6c4d1197975d45e14a`，包含
集成`2ff90f1`。分支`codex/u086-cancel-page-recovery`；产品实施者为当前单一
codex-home值守会话，在线成员`c18f0d21-1d63-4e37-af3e-2dbb78d75995`。
fresh revision501/评论146已HTTP200读回；后续revision502仍为原DSH owner/
progress。页面范围2–4小时，原卡、WIP及真实出口保持，未接管服务端事务。

[合同](page-recovery-contract.md)先于行为代码冻结，延续U084单轮原引用，
没有增加新一轮执行或取消重试。原运行与取消现在分别保存、分别显示查询
入口；运行POST在途不占取消的发送锁。取消无论成功或响应丢失，都保留原
ID，重复点击或刷新不能再生成取消ID。主体/服务/AU隔离、接纳校验、当前
权限重读和旧sessionStorage格式沿用；unknown不释放预约。

产品仅修改`WorkExecution.tsx`。服务端与作者22649f4逐字节一致；协助PR以
作者分支为目标，不将其未合格的服务端直接带入集成。页面实施者不再以自己
对作者旧源码的“独立评审”批准本修复，需前台或另一工程角色复核当前head。

验证与失败历史均见[结构化证据](page-recovery-verification.json)：

- 9项新DOM回归先观察4 FAIL/5 PASS：原运行引用阻断取消、成功取消刷新无
  原GET、POST仍在途不能取消、刷新后可再次生成取消ID。没有改坏产品制造
  RED。最小GREEN后新9项及原20项页面回归共29通过。
- npm首次因新测试文件未使用导入和可选ID类型错误失败，属于测试类型错误；
  修正后完整check通过：326前端、37管理、9动作检查。不是产品RED。
- 实际Chrome运行正常响应及取消POST落盘后丢失响应两种场景，每次10项通过。
  使用真实Core HTTP、SQLite和回环modeld替身，每次仅1个fake模型请求、
  1个取消POST；页面共run_loop/cancel_step两个POST。页面重开分别GET两个
  原命令、unknown保持1个预约；重启保留原取消记录，新service实例隔离旧
  浏览器引用；1440/390/320三宽度通过。
- 浏览器首轮在预约提交前刷新，未看到取消按钮，是夹具观察竞态；改为先读
  到reserved再刷新。第二轮错把loop父ID等同子步command_id，属于断言错误；
  改为分别验证持久loop父ID和`-t1`子命令。两轮失败保留，产品字节未因此改变。
- 新浏览器驱动明确记录作者现存服务端缺陷：取消POST的cancel_accepted=true，
  重启GET仍false。它只证明页面命令与原ID恢复，绝不把该矛盾当送达一致性
  通过；原六项服务端故障反例在PR42/评论145，仍由DSH接续。

完整Python验证：Ran 783 tests in 506.283s；OK (skipped=9)。该结果属于当前候选源码，
准确发布head的CI仍须另行读回。

复现（先构建console，使用项目锁定依赖；Windows启用UTF-8）：

```text
node node_modules/vitest/vitest.mjs run src/features/work/cancel-recovery.test.tsx src/features/work/page-execution.test.tsx --root web/console
node scripts/u086-cancel-recovery-browser.cjs
# UNION_U086_LOSE_CANCEL=1 再运行，验证取消响应丢失
python -m unittest discover -v
npm run check
```

浏览器需`UNION_PYTHON`与`UNION_CHROMIUM_PATH`；输出由`UNION_U086_EVIDENCE`
指定。临时凭据、数据库和日志不进入Git；公开JSON只记录计数/结果/hash。
真实计费模型调用0，NAS未切换、未迁移、未启动持续业务。#40及父#22不关闭。
