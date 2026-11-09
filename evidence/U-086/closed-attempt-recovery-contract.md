# U-086：attempt 关闭后保留原运行查询

2026-11-09，codex-home 单一值守实施；输入 PR44 `c6c13f2`。
源码复查发现：U106 采用原成果会关闭原 attempt；WorkExecution 因此把下一命令
从 run_loop 切到 start_attempt，已确认的 run_loop 引用被隐藏，或被更早的准备
引用替代。本项为原请求恢复合同的 1–2 小时补漏，一个独立可验收结果；#40 的
DSH owner/progress 与父 #22 真实出口保留，不重新认领已完成的 #60。

在测试及行为修改前冻结：

- 原 run_loop 已确认后，attempt 关闭、成果采用、Work 交付与刷新均保留其
  原查询入口。更早的成功 start_attempt 不能替代原 run_loop ID。
- 存在尚未确认的执行引用时仍优先恢复它；成功准备后仍可显式运行一次。
  保持原 sessionStorage 结构，只存身份，不保存正文或新增命令。
- 查询仍核对当前主体、服务、AU、kind/ID 与原版本；无新操作资格时合法
  读取仍可用。失权清除旧内容，普通迟到错误不改写已发生事实。
- 只修页面引用选择与相关 DOM/真实 Chrome 夹具；不变更服务端事务、授权、
  attempt 收口、预约或模型循环。现有回执 GET 核对真实 HTTP/SQLite 原事实。
- 先观察完整 prepare→run→关闭状态转换及恢复引用的 DOM RED，并在现有
  U106 真实 HTTP 浏览器采用/交付流程中复现，再做最小 GREEN。
  全量 npm/Python、受影响浏览器与准确 head CI 后由另一工程角色复核。

全部模型为明确的有界替身，真实推理为 0；不迁移、切换业务服务或开放持续业务。
