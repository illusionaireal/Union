# 052 候选包、复制安装与代码回滚

2026-11-03。查阅用户指定的本日session后，接续`feat/production-model-access` / `dd431e5`。上一轮已经交付048 A工程及Windows子进程修复；本轮由外部工程代理实现其可安装交付切片，不计作AU自主成果。

## 交付

`scripts/release_package.py`提供白名单打包、ZIP/安装目录逐文件完整性验证、安装不覆盖、操作互斥、显式宿主配置、依赖/私有modeld配置预检、原子代码指针、明确目标回滚与前台启动。包包含实际Python源码、React构建、模型目录及许可、固定modeld构建与第三方许可、依赖锁、运维说明/配置模板与原有私有凭据初始化脚本。开发环境以外运行不需要Git/npm/上游源码；宿主仍须准备固定Python依赖和Bun。

工作树来源与实际源文件/发布文件摘要都保留，工具链字段是版本要求，不伪称未提交文件属于Git基线。摘要用于完整性检查，没有新增包签名或仓库许可证。发布文件不收集未跟踪的历史残留、独立HTML演示、业务数据库或凭据。

代码和两个私有状态目录必须隔离。安装、采用、回滚不写业务账本或账号凭据，不调用供应商，不自动停止服务。`--services-stopped`是操作者停机确认，不是运行进程检测。进程退出/未知核对仍由原运行协议负责；版本切换不证明远端取消。

## 验证与失败保留

- [unit-red.log](unit-red.log)：初版错误地把Python双下划线文件名当作版本ID拒绝，9项中5项错误；已分离路径与版本名验证。
- [unit-final.log](unit-final.log)：9项行为检查通过，覆盖损坏、路径逃逸、链接、重复/额外文件、安装失败清理、坏目标不采用、原子指针失败、操作互斥、回滚保留最新业务字节。
- [modeld-build.log](modeld-build.log)与[console-build.log](console-build.log)：实际固定构建。初次指定另一套Bun被版本门禁拒绝；改用1.4.2后构建通过。
- [install-checks.log](install-checks.log)：错误Bun导致采用预检拒绝，未切换。
- [install-checks-final.log](install-checks-final.log)：验证脚本的HTTP函数名覆盖模块引用导致失败，已修复。
- [install-debug.log.gz](install-debug.log.gz)：验证脚本从安装目录导入客户端时生成Python缓存，完整性门禁拒绝额外文件；验证脚本与运行入口显式禁用缓存，继续保持严格完整性检查。原始日志逐字节保存在gzip中，避免把原始末尾空白误当源码格式错误。
- [install-checks.json](install-checks.json)与[install-final.log](install-final.log)：5项实际复制安装检查通过。两个candidate ID使用同一份源码；首次启动两个服务/测试账号设置、新代码ID启动后同账号登录、旧ID回滚后同账号登录、空modeld账号库可重开、最新测试账本字节及凭据未替换。没有执行数据库schema迁移。
- [python-tests.log](python-tests.log)：首次424项有1失败18错误，未设置上一会话使用的`PYTHONUTF8=1`，隐式文件读取与网关子进程输出按GBK解码。原始结果保留；安装运行入口已显式采用`-X utf8`。
- [install-utf8.log.gz](install-utf8.log.gz)：并行复验有一次Console无诊断提前退出，原因未确定；原始日志逐字节gzip保存。验证脚本增加退出码与输出诊断，[install-checks-utf8-final.json](install-checks-utf8-final.json)与[install-utf8-final.log](install-utf8-final.log)随后同配置5项通过。该局部通过不建立持续运行稳定性结论。
- [install-checks-final-source.json](install-checks-final-source.json)与[install-final-source.log](install-final-source.log)：最终源码包含运维文档/模板/初始化脚本，65个发布文件；在全量Python完成后串行复制安装/启动/代码切换/回滚5项通过。
- 完整Node、模型服务与UTF-8 Python结果分别保存在[npm-check.log](npm-check.log)、[modeld-tests.log](modeld-tests.log)、[python-tests-utf8.log](python-tests-utf8.log)：npm全部检查含53项前端通过，modeld 8项通过，Python 424项成功（5平台跳过）。主账调整另由[management-final.log](management-final.log)验证，状态和在制不升级。

验证全部使用新临时目录和临时本地凭据。真实供应商账号0、真实模型调用0、实际NAS/公共部署0；原始配置、密码、token和数据库不保存到公开证据中。实施者自检，无新增资金或权限机制，不冒充独立工程复核。

## 未通过范围

本轮不关闭U-060/048 A的真实Go账号→原AU任务→成果→反馈出口，不关闭U-002或U-054。B其他profiles、C完整持续恢复/凭据池和D正式发布仍未完成。U-054剩余真实宿主脚本配置化、安装环境依赖、跨版本迁移/备份恢复、停机与目标主机演练及必要独立复核仍须另行验收。

新工具不采用既有部署脚本中的宿主硬编码；本轮没有改写那些历史脚本、Git历史或真实部署。使用步骤见[ops/release/README.md](../../ops/release/README.md)。
