# 048 A 续接：跨平台退出修复与工程审查

2026-11-03，用户确认继续正式模型接入 / Go 接入 AU。续接分支为 `feat/production-model-access`，原工程提交为 `f46700a`。实际实施者是外部工程代理，不计作 AU 自主交付。

原提交的 GitHub push 检查共 7 项通过：Linux / Windows 工程检查、Python 机制、固定模型服务构建及安装，以及 Chromium 流程。记录见 [remote-baseline.json](remote-baseline.json)。这补充 050 的远端证据，不升级真实账号、实际业务或发布验收。

本轮重新执行本地回归，发现 Windows CLI 超时后遗留子进程：启动器退出，但继承日志句柄的工作进程仍存活，临时目录清理报 `WinError 32`。首次全量 414 项中有 1 项错误、5 项平台跳过，原始日志保存在 [python-tests.log](python-tests.log)。单跑旧超时用例通过，说明旧测试没有稳定等待子进程启动；该结果保存在 [timeout-reproduction.log](timeout-reproduction.log)。

新增真实本地子进程测试，等待工作进程监听回环端口后取消，并验证工作进程退出、日志可重命名及结果仍为 unknown。旧实现稳定失败，见 [cancel-red.log](cancel-red.log)。修复在 Windows 先按原 PID 终止进程树，再等待启动器退出；POSIX 继续使用原进程组终止。启动失败和取消共享该清理路径，日志句柄在 finally 中释放。本地终止不能证明供应商已取消，不改变调用预约、费用未知或禁止重放的规则。

定向 4 项通过，见 [cancel-green.log](cancel-green.log)。修复后全量 Python 415 项运行成功，其中 5 项平台跳过，见 [python-tests-final.log](python-tests-final.log)。`npm run check` 包含管理、历史计划、离线机制、53 项前端、类型检查及构建，见 [npm-check-final.log](npm-check-final.log)。Node 检查使用仓库要求的 24.19.0；Python 为项目虚拟环境的 3.13.14。此修复由实施者自检，不新增权限或费用机制，也不冒充独立评审。

仍需实际宿主模型服务配置位置、目标 AU 和明确调用 / 费用额度，才能执行 Go 账号至原 AU 成果及反馈验收。已在本次会话请求这些条件；没有进行模型调用或实际部署，048 A / U-060、U-002、U-062、U-054 不收口。
