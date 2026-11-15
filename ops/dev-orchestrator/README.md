# UNION 开发控制器：历史运维入口

2026-11-13，U-118：仓库中的旧控制器已退役新开发派发、本地主账认领/完成、模型探测与自动 Git 提交。新开发通过 [统一在线适配器](../../scripts/kanban-operations.mjs) 使用实际 owner/version，按当前任务分支提交 PR 到 `rewrite/charter-v1`。本工具是外部工程历史运维入口，不是 AU 成员或产品运行调度器。

本页描述仓库版本。已安装控制器、broker、service/timer 及宿主私有配置须由协调者另行核对版本；仓库交付不等于它们已经更新或停止。仓库安装器现只返回退役说明，不再读取私有配置、创建目录/服务/网络或启动进程。

## 保留的操作

配置使用 [config.example.json](config.example.json) 的三个宿主路径，指向已有仓库、历史 state 目录和原 broker socket。实际地址、认证和私有路径保留在宿主配置中。state 必须在目标仓库之外。

```sh
python3 union_dev.py --config /path/to/private-config.json status
python3 union_dev.py --config /path/to/private-config.json preflight
python3 union_dev.py --config /path/to/private-config.json once --dry-run
python3 union_dev.py --config /path/to/private-config.json pause
python3 union_dev.py --config /path/to/private-config.json inspect RUN_ID
python3 union_dev.py --config /path/to/private-config.json reconcile RUN_ID
# 原作业均已观察到退出后，显式归档为 blocked；预约和未采用代码仍保留
python3 union_dev.py --config /path/to/private-config.json reconcile RUN_ID --resolve blocked
```

- `status`、`preflight`、`once --dry-run`、`inspect` 不启动模型或容器，不初始化磁盘数据库、不创建运行或证据目录。历史数据库不存在时状态明确返回 `history_available=false`；未知 run ID 检查失败。
- `status.enabled` 恒为 false，`configured_enabled`、`max_calls` 仅显示旧配置；所有旧模型、分支、资源与能力标记均不能恢复派发权。
- `pause` 只在已有历史数据库保存暂停意图。它不取消或证明原远端作业已经停止；没有历史数据库时明确报错。
- `reconcile` 只能查询已经记录在原 run 下的 job ID。它保留运行原状态，仅保存观察元数据；不会执行下一阶段、重新派发、采用成果或写任务主账/Git。`--resolve blocked` 在原作业全部确认为 exited 后显式归档，不删除或释放任何调用预约。
- `once`、`once --trial`、`preflight --probe-models`、`resume` 返回 `decision=retired` 与现行入口说明，退出码 2；只读退役说明退出码 0。直接调用旧 Controller 的 invoke/probe/claim/finalize/save/git/resume 同样明确拒绝。
- `install.py` 返回 `decision=retired`，退出码 2，不进行安装或改变已有宿主服务。直接调用 Broker 的任何 start（含 setup/probe/validator/finalize）或 resolve_not_started 也明确拒绝，且不调用 Docker、不创建 job 或修改历史。

## 原请求与证据边界

沿用原 SQLite 的 settings/runs/calls 表及原 broker job.json，不迁移历史、不补造原请求。查询前校验 run/job ID、目录范围和原容器身份；Controller 通道与 Broker.request 都只接受已有 job 的 poll，拒绝 start、resolve_not_started 及其他动作。核对回执必须匹配原 job ID。一个容器当前不存在只说明结果 unknown，不能证明从未执行。

原始日志、调用回执文件、未采用 patch、失败测试和其他历史证据保留；核对只更新 calls 的当前观察、run 的核对元数据及对应 manifest/观察文件。调用预约计数在退出、unknown、显式 blocked 归档和重启后都保留。已有仓库锁继续串行化核对；数据库和文件更新不构成全局原子事务，磁盘/网络失败保留原 ID，下一次仍查询该 ID。

读不到原 broker 或回执不完整时明确失败；不能通过新模型调用、换 ID、清理记录或手工修改任务账本“恢复”。单行 broker JSON 仍有 16 MB 上限，未增加分块读取或宿主清理策略。

## 验证与历史

U-118 的严格 RED/GREEN、原请求保留回归和限制见 [本片证据](../../evidence/U-118/README.md)。定向执行：

```sh
python -m unittest tests.test_dev_orchestrator -v
```

测试使用临时仓库和数据库、受控 broker 替身，不调用真实模型或 Docker。现行在线适配器的准入与外部协作契约由 [Kanban 约定](../../management/KANBAN.md) 拥有，旧本地 project.json 不再作为任务调度源。

2026-11-01–02 的 NAS 安装、镜像、网络隔离及当时验证记录保留在 [030 历史证据](../../evidence/030-dev-orchestrator/README.md)。当时的默认关闭、模型认证/沙箱限制和“修正后可启用旧派发”操作口径属于历史；此版本删除了新派发实现，不能再通过配置重启它。历史失败和运行证据没有被本次退役改写。
