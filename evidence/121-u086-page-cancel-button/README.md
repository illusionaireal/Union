# evidence/121 — U-086 重建子步 2：WorkExecution 页面取消入口（RED→GREEN）

## 范围（遵守 evidence/119 冻结合同）

在 `WorkExecution` 增加「取消本次执行」入口，**仅当存在未派发的 reserved 步进**（`step.status === 'reserved' && !step.command_id`）时可用；点击调用 `cancel_step`（`{work_id, step_id, reason}`）。不提供对 `unknown` 步进的取消（那些只能按线端原请求核对）；不动 run/start/lookup 语义。

## RED

`web/console/src/features/work/page-execution.test.tsx::a reserved step can be cancelled from the page before dispatch`

观察失败：按钮不存在（`Unable to find role "button" name "取消本次执行"`）。
`evidence/121-u086-page-cancel-button/red.txt`

## GREEN（最小）

`WorkExecution` 的 `run_loop` 分支旁增加条件按钮：存在未派发 reserved 步进时显示「取消本次执行」，点击 `api.coreWorkCommand({kind: 'cancel_step', ...})`，成功后 invalidate `core-work` 查询并显示回执 message。

## 回归

- `npm run check:console`（tsc + vitest + build）全绿（page-execution 8+1 tests）。
- Python 全量 783 tests OK（11 skipped，本子步未改 ai_union）。
- reviewer 探针 3/3 PASS（本机复跑，UI 变更不影响边界）。
