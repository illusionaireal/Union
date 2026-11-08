# 092：PR 前合并后验证（临时克隆，662 项通过）

2026-11-08 08:34–09:10。为了不把"合并预演干净"当成全部结论，本轮在**独立临时克隆**里真正合并集成分支并跑全量，验证两边的改动放在一起仍能通过。共享工作区与他人的未提交文件**完全未涉及**。

## 做法

```powershell
git clone --no-hardlinks --branch dsh/s03-work-runtime <repo> %TEMP%\union-merge-check
git fetch origin "refs/remotes/origin/rewrite/charter-v1:refs/integration"   # 真实远端集成分支 = 9fff477
git merge --no-edit refs/integration
```

- 合并结果：**无冲突**，产生合并提交 `75e4453`。
- 合并后树包含：我的 S03 自动执行链（`run_step`/`run_loop`/modeld 适配器/宿主装配、`work_transport.py`、`tests/test_work_transport*.py`、`tests/test_core_work_http.py`）+ 集成分支上的改动（`codex/watch-source-isolation`、`u075-profile-acceptance` 的 Responses profile、`management/OPERATIONAL_CONTRACT.md`、`scripts/kanban-operations.mjs`、`tests/kanban-operational.test.mjs`、`specs/.../s09-responses-contract.md`、`tests/test_core_responses_profile.py`、`tests/test_release_python_environment.py` 等）。

## 结果

| 检查 | 结果 |
| --- | --- |
| 合并后 Python 全量（`-m unittest discover`） | **662 项通过 / 8 平台跳过 / 0 错误 / 0 失败** |
| 合并冲突 | **无**（`git status` 无 `UU/AA`） |
| 共享工作区影响 | 无（全程在 `%TEMP%` 克隆内操作；主仓库工作区与他人的 17 个未提交文件原样） |

> 说明：克隆内没有 `node_modules`，因此前端 `npm run check` 未在该克隆中执行；前端与主仓库同一提交（b102bfa）此前已在本机通过（206 项 + typecheck + build）。

## 结论与边界

- 这是**合并后工程验证**，支持"分支可安全合入当前集成分支"的判断；它不等于 CI 结果，也不等于真实运行验收。
- 真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）仍缺宿主 modeld 通道与凭据。
- 在线看板仍被 SNI 级阻断，`#22` 四段 checklist、`#32/U-078` 的在线同步待网络恢复。

## 下一步

协调者开 PR（本机无 `gh`/仓库 token）：
`https://github.com/illusionaireal/Union/compare/rewrite/charter-v1...dsh/s03-work-runtime?expand=1`

CI 通过后由协调者合入；本文件记录的合并后 662 项可作为本地对照。
