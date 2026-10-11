# 本轮实际验证证据

运行日期以 `validation.json` 的北京时间为准；代码基线为 `24845e3eb3709645356aa835564c67ed60b628bb`，变更尚未提交到远端。该文件还保存测试当时的代码文件 SHA-256。

- `tests.log`：25 项机制及接口测试，全部通过，无跳过。最初先写测试，因 `ai_union.engine` 尚未实现而失败；随后实现机制并进行回归。
- `fixture-run.log`、`events.json`、`decisions.json`：实际测试程序的状态、事件、决定与派发记录，执行器始终为 fixture。
- `source.md`、`dependent.md`、`followup.md`：从实际资产目录读取并经 SHA-256 复核的三份模拟成果。
- `followup-context.log`：后续工作的规则、任职、依赖、资料与版本清单。
- `fixture-evaluation.json`：E1/E2 的工程闭环检查通过，但明确 `status=simulated` 和 `real_agent_verified=false`。
- `restart-wait.log`：新进程恢复已有状态，进入等待，没有新增执行调用。
- `wheel-validation.json`：无网络、无依赖下载的 wheel 构建与隔离虚拟环境安装；从独立目录运行安装后的 `ai-union` 命令完成模拟闭环。

执行器 subprocess 替身测试不是 Codex 模型调用。真实模型调用数为 **0**；费用未知，未消耗可确认的模型预算。真实组织能力、外部发布与市场反馈未验证。GitHub CI 工作流已添加，其命令已在本机验证，远端 CI 未运行。

复现：仓库根目录执行 `python3 scripts/validate.py --root .union/new-validation`。根目录必须不存在，避免覆盖原证据和组织状态。返回码 0 表示机制与模拟场景通过；脚本保留 CLI evaluate 的实际退出码 3，不伪装成真实评测通过。

本地数据库、董事会凭据和私有执行日志位于被忽略的 `.union/`，不包含在本证据目录中。
