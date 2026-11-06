# U-075 / S09.1：接入方式（profile）能力范围与单一所有权

日期：2026-11-07（Asia/Shanghai）。分支：`rewrite/charter-v1`。在线卡：#28。
范围级别：**controlled**（受控工程验证）。本轮不宣布任何新的真实供应商验收。

## 本轮交付的用户可见结果

1. 模型页新增「各接入方式的能力范围」：每种接入方式（`openai_compatible`、`modeld_grant`）逐项列出
   文字回答、工具往返、用量记录、边生成边显示、长任务期间新输入、取消与中断后查询六项能力，
   每项标明 **真实已验证 / 仅受控验证 / 不支持**，并附该条声明的证据路径与说明。
2. 一份成功不再外推：`modeld_grant` 的文字回答只标「仅受控验证」，`openai_compatible` 的流式与
   长任务新输入明确写「不支持」，页面上不会把一种接入方式的能力说成通用能力。
3. 服务端成为 profile 的唯一所有者：`ai_union/domain/model_profiles.py` 定义支持的 profile、认证方式、
   私有字段与逐项能力声明；保存连接命令、状态校验、工作定义校验、modeld API 连接分支都改为读同一注册表，
   不再各自维护 `("openai_compatible", "modeld_grant")` 字面量副本。

## 本轮**没有**做的（如实记录）

- 没有接入任何新的真实模型供应商，也没有为某个 profile 重跑真实推理；`openai_compatible` 的
  「真实已验证」仍只来自 U-072 那两次真实请求（`evidence/058-s02-model-tools/README.md`）。
- 流式输出（边生成边显示）、长任务执行期间接收新输入：**未实现**，页面上按「不支持」显示。
- 取消与中断后查询只到受控验证；没有真实供应商的中断恢复证据。
- 没有部署、没有真实资金、没有迁移生产数据；不关闭 TLS 校验。
- 因此本卡不满足 U-075 完整验收（逐 profile 的真实配置/原生内容/流式/长作业恢复各需单独真实证据），
  本轮只完成第一段可控的垂直切片。

## TDD 步骤与证据

| 步骤 | 内容 | 证据文件 |
| --- | --- | --- |
| RED（后端） | 先写行为测试 `tests/test_core_model_profiles.py`，实际运行报 `ImportError: cannot import name 'model_profiles'` | `red-backend.log` |
| GREEN（后端） | 新增注册表 + 服务读回 `capabilities.profile_scope` + 校验改读注册表，44 项相关测试通过 | `green-backend.log` |
| RED（前端） | `Models.test.tsx` 新增能力范围行为测试，实际运行 2 项失败（列表里没有该卡片） | `frontend-models.log` |
| GREEN（前端） | 新增 `ProfileScope.tsx` 并接入模型页，`src/features/models` 52 项全部通过 | `green-frontend.log` |
| REFACTOR | 在通过状态下把 `domain/work.py`、`domain/model_access.py`、`application/model_access.py` 里
重复的 profile 字面量换成注册表函数；`test_core_model_profiles` 用移除条目的反例保护该接线 | `green-backend.log`、`green-npm-check.log` |

RED 期间对既有测试只做了**收紧**：原断言 `getByText(/core.model_check/)` 过宽，会被新增的证据路径
`tests/test_core_model_checks.py` 命中；改为精确匹配「执行定义：core.model_check · v1」，断言意图不变
（回执必须展示绑定到这次检查的执行定义），没有放宽任何既有覆盖。

## 验证结果

- `set PYTHONUTF8=1; .venv\Scripts\python.exe -m unittest discover`：**Ran 585 tests，1 error、9 skipped**。
  唯一 error 是 `tests/test_workspace.py` 在建立目录符号链接时被主机拒绝
  （`OSError: [WinError 1314] 客户端没有所需的特权`），属于本机没有符号链接权限的环境限制，
  发生在测试准备阶段，与本轮改动的 models/work 代码无关；未修复、未伪造通过，见
  `python-discover-summary.log`。
- 受影响子集：`tests.test_core_model_profiles / test_core_models / test_core_work /
  test_core_model_checks / test_core_model_boundaries / test_core_model_recovery` **38 项全部通过**。
- `npm run check`：`Management check: 15 modules, 8 milestones, 76 tasks; PASS`；Node 测试 9/9；
  前端 **18 个文件 193 项全部通过**；typecheck 与生产构建成功（只有既有的 >500 kB 分包提示）。

## 复现

```bash
set PYTHONUTF8=1
.venv\Scripts\python.exe -m unittest tests.test_core_model_profiles -v
cd web/console && npx vitest run --run src/features/models
cd ../.. && npm run check
```

## 下一步（同一张卡，未完成）

1. 选一种**新的**接入方式（例如某个具体供应商的原生协议），完成其认证与原生内容/流式/工具往返的
   真实证据，并把该 profile 的能力声明升级为 `verified_real` 或如实保持 `unsupported`。
2. 长作业的新输入与中断恢复需要真实中断证据（README 里不预支）。
3. 每种 profile 各自的证据文件分开记录，不用一次成功外推其他 profile。
