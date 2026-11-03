# 候选包安装、升级与代码回滚

052接续048 A的安装工程。完整发布验收、真实NAS配置化、备份恢复和数据迁移仍属于U-054 / 048 D；此目录不采用历史脚本中的真实宿主地址。安装器不连接SSH，不部署公共网站，不授权模型支出。

## 构建可审查候选包

在开发机使用Node 24.19.0、Bun 1.4.2及固定Python依赖：

```sh
npm run check
python3 -X utf8 -m unittest discover -v
npm run build:model-service
python3 scripts/release_package.py pack --release-id candidate-001 --output .union/releases/candidate-001.zip
python3 scripts/release_package.py verify .union/releases/candidate-001.zip
```

ZIP包含Python源码、已构建React工作台、modeld可独立运行的构建、模型目录、Python依赖锁及OpenCode/目录许可。ZIP无需Git或npm便可运行；Python及Bun由宿主安装，Python环境需先按包内`requirements-harness.lock`安装全部固定依赖。依赖下载属于环境准备，此包尚非离线依赖镜像。

包内包含本说明、配置模板及`services/modeld/init.mjs`。首次安装且尚无modeld私有配置时，用固定Bun执行`bun services/modeld/init.mjs /path/to/private/union-modeld`；已有私有配置继续复用，初始化不覆盖原凭据。安装目录和两个私有目录的路径始终由宿主配置决定。

`manifest.json`记录Git基线、工作树修改、源文件摘要和发布文件摘要。开发工作树有改动时显示`working_tree`；只有干净源文件才显示`committed`。摘要可检验损坏，不能认证发布者。发版方应在可信渠道保存包摘要和实际构建/验证证据。本仓库未新增开源许可，第三方原许可随包保留。

## 显式宿主配置与安装

将[配置示例](deployment.example.json)复制到宿主私有目录，替换全部占位路径。Windows路径使用`C:/...`。安装目录、Console业务目录与modeld私有目录必须互不嵌套。使用已有`modeld.json`及分离的管理/执行凭据；首次准备方法见[模型服务说明](../../services/modeld/README.md)。配置文件和凭据留在宿主，访问权限沿用模型服务要求。

```sh
python3 scripts/release_package.py install candidate-001.zip --config /path/to/private/deployment.json
```

安装先检查全部文件，再写入新版本目录；当前版本不变。相同版本名拒绝覆盖，损坏/重复/路径逃逸/链接/额外文件拒绝。安装完成后可以从包内`scripts/release_package.py`继续操作，不需要开发仓库。固定Python与Bun必须存在，否则宿主配置在任何安装写入前拒绝。

## 首次采用与升级

先停止AU新派发并按现有协议核对已发出请求，等待在途写入结束，停止Console及modeld。备份业务数据必须遵守原请求与最新账本的恢复要求。安装器没有暂停、终止、备份或恢复进程的权限接口；`--services-stopped`记录操作者已经完成停机的确认，无法证明另一进程已经退出。

```sh
python3 scripts/release_package.py activate candidate-001 --config /path/to/private/deployment.json --services-stopped
python3 scripts/release_package.py status --config /path/to/private/deployment.json
python3 scripts/release_package.py run modeld --config /path/to/private/deployment.json
```

在另一个终端或由宿主服务管理器运行：

```sh
python3 scripts/release_package.py run console --config /path/to/private/deployment.json
```

启动为前台进程，工作台仍只监听回环、使用既有身份/Host/Origin与AU权限；未提供常驻服务管理或自动调用。启动不构建前端、不生成账号凭据、不调用模型。首次工作台账号设置保持原产品流程。停止/重启由宿主服务管理器或操作者负责。

采用前验证所有文件、Python全部固定依赖和实际导入来源、Bun版本及已有modeld私有配置，再原子替换`current.json`。Python进程显式使用UTF-8，隔离用户导入路径并禁用代码缓存。预检失败或原子替换失败保留原指针。升级：安装新候选包→停机/核对→采用新ID→按原私有配置启动。禁止在版本目录写运行日志或Python缓存，额外文件也会导致完整性检查失败。

## 代码回滚与故障

```sh
python3 scripts/release_package.py rollback candidate-001 --config /path/to/private/deployment.json --services-stopped
```

必须先停止两个服务并指定已安装的旧版本。回滚只切换代码，保留当前业务数据库、请求、调用占用、凭据及成果。不能用旧账本覆盖新执行来“恢复额度”。存在跨版本不兼容数据时先完成对应迁移/恢复评审；此切片没有自动数据库降级。

操作由`.operation.lock`互斥。崩溃遗留锁不自动抢占；先由运维核对锁内PID、所有安装进程及临时目录，再处理锁和残留暂存目录。安装失败的正常退出会清理本次暂存目录，不删除已安装版本。指针替换保证正常故障下不出现半个JSON；断电持久性和网络文件系统行为未做验收。

实际复制安装/启动/代码切换结果见[evidence/052](../../evidence/052-release-package/README.md)，其范围为新临时目录的受控工程验收，不代表目标NAS、真实账号或持续经营。
