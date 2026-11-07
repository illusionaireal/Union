# 正式候选版安装、升级与回滚包

本目录是 U-054 的受控工程交付：它制作可追溯候选包，并将应用版本、宿主配置及可变组织数据分离。它不连接服务器、不启停 systemd、不导入凭据，也不构成真实目标环境发布验收。

## 构建和校验

从干净的 `dev` checkout 构建。版本由发布负责人分配；候选包记录完整 Git commit 和锁文件，拒绝从脏工作区构建。

```sh
python3 ops/release/release.py build --version 0.1.0-rc.1 --output dist
python3 ops/release/release.py verify \
  --archive dist/ai-union-0.1.0-rc.1.tar.gz \
  --checksum dist/ai-union-0.1.0-rc.1.sha256
```

候选包仅含应用源码、前端源码、锁文件、systemd 模板和启动脚本；不含 `.git`、`.union`、数据库、`board.key`、`.env` 或宿主配置。安装前仍须在目标主机按锁文件完成依赖安装与构建，并执行对应候选版的项目检查。

## 宿主配置与状态

复制 `host-config.example.json` 到目标主机的私有位置（例如 `/etc/union/release.json`），按实际值填写，并设为仅运维用户可读。该文件不进入 Git，不能包含模型 Key、登录票据、SSH 信息或私有部署路径以外的秘密。

候选工具要求 `organization_root`、`console_root`、`listen_host` 和 `listen_port` 四项齐全，且仅允许回环监听；任何一项缺失或不合法时，会在创建发行目录、切换 `current` 符号链接或写状态前失败。对外域名、TLS 和反向代理属于宿主单独变更，不能通过候选包隐式开启。

`install_root/releases/<version>/` 存放只读应用版本；`install_root/current` 是原子切换的当前版本；`organization_root` 与 `console_root` 是宿主维护的数据目录，不能置于 release 目录。凭据继续由宿主私有环境/受控身份提供。

## 受控演练流程

在隔离目录、使用模拟组织数据执行以下流程；真实环境另按正式变更单和发布门槛验证。每一步都先校验候选包及宿主配置，服务重启由运维人员在系统服务层完成。

```sh
RELEASE=0.1.0-rc.1
python3 ops/release/release.py stage \
  --archive "dist/ai-union-$RELEASE.tar.gz" \
  --install-root /opt/union --config /etc/union/release.json

# 在新 release 目录完成依赖、构建和不触发真实模型的检查后，才允许切换。
python3 ops/release/release.py backup \
  --state-root /var/lib/union --backup-root /var/backups/union --label before-$RELEASE
python3 ops/release/release.py activate \
  --install-root /opt/union --config /etc/union/release.json --version "$RELEASE"
```

升级前记录旧 `current` 目标和备份文件；升级失败时，用同一条 `activate` 命令指定此前已 stage 的版本恢复该符号链接，再由宿主按服务回执确认重启和数据读取。该操作不还原数据库：数据恢复仅从明确选择的本地备份执行，且必须先停止相关服务并单独核对版本兼容性。未知模型或外部动作仍遵循既有核对流程，不能因为应用回滚而重放。

## 当前证据边界

本包的自动测试验证候选内容/校验和、缺少配置时零写入、stage 幂等、原子激活/回退及状态备份权限。它不是 NAS、真实供应商、真实订阅、浏览器登录、服务重启、数据迁移或持久恢复的证据；这些仍分别受 U-002、U-005、U-008 和正式候选版发布门槛约束。
