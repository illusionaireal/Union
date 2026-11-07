# U-074 早期安装：Linux 虚拟环境选择

2026-11-08。NAS 隔离安装发现：release_package.read_config 对用户配置的 Python 可执行文件调用 resolve()。Linux venv 的 bin/python 是符号链接，因而实际启动了系统 Python；即使已离线安装全部锁定依赖，发布前检查仍报告缺 aiosqlite 元数据。

编码前合同：配置里的 Python/Bun 是宿主显式选择的可执行入口，已有规则允许其符号链接。保留其绝对调用路径，使解释器识别正确的 venv；安装目录、业务目录、私有配置的链接拒绝与包含关系检查保持原边界。不得跳过依赖锁验证、改系统 Python 或覆盖既有 NAS 服务。

新增回归通过真实 venv 和实际子进程，在与预检相同的 -I 模式下核对 sys.prefix。先在 NAS Linux 观察失败，再修复。原 NAS 试验的 noexec 挂载和缺依赖问题保留为宿主准备证据。
