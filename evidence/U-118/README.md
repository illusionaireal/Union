# U-118：旧开发控制器派发与采用退役

日期：2026-11-13。范围为仓库工程防回流；在线卡 #72 已由协调者成功认领。
实施者为受委派的工程子代理，在线成员为 `zbook-codex`，actor 为根协调会话。

## 实施前依据

- 契约：`specs/053-union-rewrite/plan.md` §13 和本次明确的文件责任。
- 基线：`codex/v1-correction-execution-20261113@d27d543e044a4111204c898130f9187c9e4770f7`，没有 upstream。
- TaskStartSnapshot：本任务文件初始无改动；协调者已有 `specs/053-union-rewrite/plan.md` 修改和 `docs/aegis/work/2026-11-13-v1-correction-execution/` 未跟踪目录。
- 实际工具链：`D:\Project\Union\.venv\Scripts\python.exe --version` 返回 Python 3.13.14；测试 cwd 为指定独立工作区，显式 UTF-8。
- 源码检查确认 `once`/`probe_models`/`invoke` 可创建运行和调用预约，`claim_task`/`finalize` 写本地主账，`once`/`finalize` 提交 Git；通用 `save`、`broker`、`git` 也提供直接绕行。

## 边界与方法

Change Necessity：文档或 `enabled=false` 不会消除可恢复的旧派发/写权，最小必要变更是收敛既有 Controller 的职责。新开发使用 `scripts/kanban-operations.mjs` 和任务分支 PR 到 `rewrite/charter-v1`。

TDD Route: strict，依据为用户 AGENTS 与冻结契约。先观察旧实现违反拒绝契约的行为 RED，再删除派发/采用实现、做 GREEN 与保留能力回归。原自动认领/完成/提交成功断言按 `expected-retirement` 更新，不删除正确源码制造 RED。

Anti-Entropy：`code-retirement` / `delete-first`。退役内部开发派发、本地任务所有权及自动采用；历史状态、暂停、已记录原 run/job 的显式核对仍有独立职责。没有持久数据删除、Schema 迁移或宿主部署；只允许原有核对观察元数据更新，不释放 unknown 预约。

Complexity Budget：源文件约 530 行，`once` 混合规划、派发、采用及任务/Git 写入；本片 `local-fix-without-new-responsibility`，原位删除这些职责，不另建调度器、存储或适配器。测试替换退役成功场景并保留有效安全/原请求用例，目标不超过 800 行；证据沿本目录集中记录。

验收覆盖：CLI 与直接 Controller 拒绝新开发和模型探测；旧配置不能恢复权力；状态/检查只读；暂停持久；核对仅查询原 job，未知/失败/退出仍保留预约及原始证据；本地主账和 Git 不被核对改写。另一工程角色复核与全量检查由协调者负责，仓库测试不证明已安装宿主副本生效或真实 AU 自治。

## Controller 严格 RED / GREEN 记录

所有命令的 cwd 为指定独立工作区；测试自行创建临时 Git 仓库与 SQLite，目标工作区 Git、真实任务账本、模型与宿主服务没有被测试改写。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
& 'D:\Project\Union\.venv\Scripts\python.exe' -m unittest tests.test_dev_orchestrator.RetirementTests tests.test_dev_orchestrator.HistoryTests -v
```

| 记录 | 实际结果 | 说明 |
| --- | --- | --- |
| [01-red.log](01-red.log) | exit 1；23 tests，36 failures，24 errors，1 skip；25.480s | 首轮原始日志保留。预期退役失败之外，夹具未显式关闭建表连接，导致 Windows 临时文件清理错误；Windows Python 没有 AF_UNIX，socket 替身也需显式声明该常量。这些脚手架问题没有修改生产源码。 |
| [02-red.log](02-red.log) | exit 1；28 tests，45 failures，0 errors，1 skip；27.283s | 修正隔离并补充路径/证据反例后，旧实现真实失败；源码尚未修改。包括真正子进程 CLI、新 run/call、直接 Git/采用入口、原 ID 和证据范围反例。 |
| [03-green.log](03-green.log) | exit 0；28 tests，0 failures，1 skip；24.608s | 只在有效 RED 后删除派发/采用实现，保留能力与拒绝契约通过。 |
| [04-targeted.log](04-targeted.log) | exit 0；30 tests，0 failures，1 skip；23.626s | 更新 expected-retirement 测试后执行整个模块，包含原 Broker 两项安全回归。 |

整个模块的命令是同一 Python/UTF-8 环境下 `-m unittest tests.test_dev_orchestrator -v`。唯一跳过是 POSIX flock 互斥用例；此 Windows 环境的 broker 传输正向验证使用受控 socket 替身，不宣称真实 Unix socket、Docker 或 Linux 宿主已经验收。

## Controller 阶段契约与保留行为映射

| 契约 | 对应测试与证据 |
| --- | --- |
| 即使旧 enabled/trial/能力标记全满足，也不派发/建 run/预约 | `test_once_retires_before_run_reservation_or_broker_even_with_all_gates_open`、`test_real_cli_rejects_once_trial_probe_and_resume_without_side_effects`、`test_direct_invocation_of_every_role_is_retired_before_any_reservation`、`test_direct_probe_cannot_create_run_or_call` |
| 旧本地主账与 Git 写权完全退役 | `test_claim_and_finalize_cannot_write_ledger_report_or_git`、`test_generic_save_cannot_create_run_or_adopt_existing_run`、`test_generic_git_cannot_commit_even_when_directly_called`；比较 journal、仓库文件和 Git 元数据字节 |
| 资源/权限/失败证据不构成重新启用理由 | `test_budget_sandbox_authority_and_expired_run_never_restore_dispatch`、`test_tampered_or_failed_evidence_never_reenables_adoption`、`test_pause_cannot_be_cleared_to_restore_old_dispatch` |
| 状态/检查不初始化状态、不创建假运行 | `test_cli_dry_run_and_preflight_are_read_only_retirement_reports`、`test_status_and_inspect_preserve_history_bytes_without_broker`、`test_read_commands_do_not_initialize_missing_state`、`test_inspect_missing_run_does_not_create_evidence_directory` |
| 暂停持久且不冒充远端取消 | `test_pause_is_durable_and_never_claims_remote_cancellation`；原 run/call 保持，重启仍读到暂停意图 |
| 原请求核对不重放、不采用、不写任务/Git | `test_reconcile_observes_original_without_replay_adoption_or_task_writes`；每个请求只有原 ID 的 poll，原始日志/patch 字节与调用预约保留 |
| 容器缺失/读取失败仍保留 unknown 和预算 | `test_missing_container_remains_unknown_and_keeps_reservation_after_restart`、`test_reconcile_failure_preserves_original_call_and_history`、`test_explicit_resolution_requires_observed_exit_and_never_releases_calls` |
| 保留路径、原身份及 broker 权限边界 | `test_state_directory_still_cannot_be_inside_repository`、`test_missing_and_unsafe_run_ids_do_not_create_evidence`、`test_malformed_stored_job_cannot_escape_evidence_directory`、`test_evidence_directory_symlink_cannot_escape_state`、`test_unknown_job_id_cannot_be_polled_even_directly`、`test_wrong_job_receipt_cannot_replace_original_observation`、`test_broker_start_and_not_started_resolution_are_not_exposed` |
| 原 Broker 的容器/验证安全回归 | `test_running_original_blocks_second_container`、`test_validator_mounts_no_credentials_or_socket_and_fixes_argv`；只用 Docker 替身，broker.py 字节未改 |

Controller 已删除规划、worker/validator/reviewer 循环、快照/采用门禁和本地主账/提交实现；旧入口只提供明确拒绝。`plan_valid`/`snapshot`/`seal`/`gates` 的自动采用用途不再有所有者，相关成功断言按 expected-retirement 替换。失败日志和历史验收记录没有删除，U-037/U-041 优先提示不再存在于可执行控制器。

结构检查与候选文件 SHA-256 见 [05-controller-structure.json](05-controller-structure.json)：AST 解析、旧 owner 移除、无 runs/calls INSERT、无 Git subprocess、无旧优先级/本地主账输入、配置范围、README 引用与 `git diff --check` 全部通过。该记录只证明所列结构，不替代行为和独立复核。

保留的 SQLite 写入仅为已有 journal 的暂停意图、原 calls 当前观察与原 run 核对元数据；不存在新 run/call 的写路径。每项元数据使用原 ID，文件通过临时文件替换保存。数据库与文件不是全局事务，网络/文件失败不能据此推断远端未执行；再次操作仍只能显式查询原 ID。当前未引入新 Schema、任务源或调度器。

Complexity Closure：Controller 从原先约 530 行减少到 240 行，职责缩为退役答复和历史运维；测试为 475 行，原 Broker 安全用例保留。减少的是规划/派发/采用/账本/Git 依赖与分支，不以压缩排版充当简化。当前均在复杂度预算内。

## Controller 阶段冻结历史

2026-11-13：协调者确认 `install.py` 仍会在缺少宿主 config 时复制示例、生成 broker 配置及注册/启动旧服务。Controller 阶段结束后先冻结候选，等待在线 #72 与 §13 补齐安装器/底层 broker 责任；该时点没有修改这两个文件。后续明确授权与实际实现见下一节，原冻结记录不作为当前未完成原因。

独立规格/工程角色复核及项目全量检查仍由协调者负责。真实模型调用、Docker/Unix socket/部署、AU 自治与持续运营均不在上述证据范围；仓库退役也不证明已安装旧副本和 timer 已实际采用。

## 安装器与 Broker 补充退役

协调者先完成 #72 v2→v3 HTTP 200、revision 1162 并更新 §13，再明确授权本子任务写 `install.py` 与 `broker.py`。本片复评为 6–8 小时，同一个防回流结果；不涉及宿主服务采用。Change Necessity：只阻断 Controller 仍允许直接 Broker.start 和旧安装器创建派单服务，须在各自所有者删除实现。没有新增调度器或安装替代流程。

TDD Route 继续 strict。旧安装器仅通过 runpy 执行到被完全隔离的 Path/宿主方法替身；mkdir、复制、chmod/chown 和子进程均被替身截断，没有实际安装。先观察拒绝契约失败，才改成只打印退役 JSON 和 exit 2。真实子进程 CLI 用例只在隔离 GREEN 已证明候选安全后加入，目标参数也是临时目录。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
& 'D:\Project\Union\.venv\Scripts\python.exe' -m unittest tests.test_dev_orchestrator.BrokerRetirementTests tests.test_dev_orchestrator.InstallerIsolationTests -v
```

| 记录 | 实际结果 | 证明范围 |
| --- | --- | --- |
| [06-broker-installer-red.log](06-broker-installer-red.log) | exit 1；12 tests，15 failures，0 errors；0.142s | 旧安装器访问宿主路径，Broker 接受新 role/start 和未开始处置；原始失败保留。 |
| [06b-broker-installer-red.log](06b-broker-installer-red.log) | exit 1；12 tests，15 failures，0 errors；0.132s | 同一旧源码下，安装器断言进一步明确捕获 `host mkdir attempted`；未撤掉正确实现制造 RED。 |
| [07-broker-installer-green.log](07-broker-installer-green.log) | exit 0；12 tests，0 failures，0 skips；0.065s | 删除宿主安装动作、全部 start/resolve_not_started 后，对应新拒绝和原 job 正常/异常核对通过。 |
| [08-final-targeted.log](08-final-targeted.log) | exit 0；42 tests，0 failures，1 skip；27.347s | 整个 `tests.test_dev_orchestrator`，含 Controller→Broker 原 ID 联调和安全候选的实际安装器 CLI 拒绝。 |

最终整模块命令仍为上述 Python/UTF-8 环境下 `-m unittest tests.test_dev_orchestrator -v`。POSIX flock 是唯一 Windows 跳过项；没有新增真实模型、Docker、Unix socket 或宿主部署证据。

补充范围的保留/退役证据：

- `test_all_new_roles_refused_before_docker_or_job_creation` 覆盖 planner/worker/reviewer/probe/validator/finalize/setup/chromium，所有旧能力标记满足也不调用 Docker、不创建 job。`test_existing_running_or_reserved_job_cannot_enable_start` 保留原在途/预约保障；`test_not_started_resolution_refused_without_docker_or_history_writes` 保留未知记录。
- 原成功 validator 启动及运行中阻止第二容器的旧断言，改为无启动实现后的等价拒绝保障；不再保留镜像挂载、网络、argv 构造等已经失去责任的派发代码。阶段 04 的历史两项结果保留，但不作为最终测试名。
- 正常 running/失败 exited、容器缺失 unknown、未知/恶意 ID、原记录身份不符、容器 label 不符及 symlink 路径均有 poll 反例；Docker 调用仅限原具名容器的 inspect/logs。已退出只更新原 job 的 phase，不删除记录/预约；容器缺失不改原 job.json 字节。
- `test_controller_and_retired_broker_share_original_unknown_identity` 通过两层真实实现核对同一原请求：只发生原容器 inspect，两个存储中的原身份、预约、unknown 与仓库字节保留。
- `test_installer_refuses_before_private_paths_or_host_side_effects` 与 `test_retired_installer_cli_leaves_supplied_directory_untouched` 证明安装器不读取配置、不写路径/服务/网络、不启动进程，真实 CLI 返回清晰的退役原因与现行开发入口。

最终六个交付文件和 SHA-256 见 [09-final-structure.json](09-final-structure.json)。AST、无 Controller run/call INSERT、无 Git subprocess、Broker 仅 inspect/logs、安装器仅 JSON 输出、配置/链接与 diff 检查均通过。Controller/安装器/示例均不再消费本地主账或注册新开发；现有线上 adapter 的语义没有修改。

最终复杂度：Controller 240 行、Broker 94 行、安装器 19 行；测试在 800 行预算内。移除的是失去职责的代码、依赖与宿主启动路径，历史核对保留在原所有者。最终核对时以 09 记录的精确行数/字节为准。

本子任务已交付仓库工程候选及定向证据，等待协调者的规格→质量独立复核和项目全量检查后采用。已安装旧副本、service/timer、私有配置和真实数据完全没有操作；本片不宣称实际部署、AU 自治或持续运行完成。
