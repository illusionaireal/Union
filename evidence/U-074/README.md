# U-074 早期安装：Linux 虚拟环境选择

2026-11-08。NAS 隔离安装发现：release_package.read_config 对用户配置的 Python 可执行文件调用 resolve()。Linux venv 的 bin/python 是符号链接，因而实际启动了系统 Python；即使已离线安装全部锁定依赖，发布前检查仍报告缺 aiosqlite 元数据。

编码前合同：配置里的 Python/Bun 是宿主显式选择的可执行入口，已有规则允许其符号链接。保留其绝对调用路径，使解释器识别正确的 venv；安装目录、业务目录、私有配置的链接拒绝与包含关系检查保持原边界。不得跳过依赖锁验证、改系统 Python 或覆盖既有 NAS 服务。

新增回归通过真实 venv 和实际子进程，在与预检相同的 -I 模式下核对 sys.prefix。先在 NAS Linux 观察失败，再修复。原 NAS 试验的 noexec 挂载和缺依赖问题保留为宿主准备证据。

验证结果：NAS Linux 真实 venv 回归先失败（sys.prefix 为 /usr），修复后通过；Windows 的发布包/venv 共 10 项通过。NAS 重新安装含本次补丁的 90 文件候选，Bun 1.4.2 和 Python 3.13.5 的锁定依赖均经过实际预检；Console、modeld 成功启动，正常账号重启登录保持，包哈希再验通过。见 nas-install.json。候选基于 4b2d700 加明确列出的发布脚本补丁，未标为纯提交源码。

隔离容器没有外部网络，未调用真实模型，也未切换已有 NAS 服务、迁移旧 AU 数据或启动持续业务。早期安装子项通过，S08 的持续使用/升级恢复与最终发布仍保持单独验收。
