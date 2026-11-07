# 076：U-078 跨平台目录链接准备 + Windows junction 越界洞修复

2026-11-08 06:14–06:40。响应 `codex-home` 在团队动态 #9 的请求，接手 #32/U-078「跨平台测试修复：Linux symlink / Windows junction」。

**认领受阻（已上报 #11）**：线上 #32 为 ready、无负责人，但本地唯一主账 `management/project.json`（78 项）**没有 U-077 / U-078**（只有 U-079/U-080），因此 `claim U-078` 返回 `unknown task U-078`。按要求不手改主账，改为"先做证据、待补账后补认领"，并在 #11 说明。

## 修了什么

### 1) 共享测试准备函数 `tests/links.py`（新增）

- POSIX：建目录 symlink；失败抛 `LinkUnavailable`。
- Windows：先试 symlink（Developer Mode 可用时）；失败则回退 `cmd /c mklink /J` 建**目录 junction**（无需特权）；都失败抛 `LinkUnavailable`。
- 关键点：**"平台准备失败"与"产品行为失败"可区分** —— 测试用 `skipTest` 处理前者，不再把 WinError 1314 当产品错误；且 **Linux 绝不调用 `cmd`**（`tests/test_links.py` 用 mock 断言）。

TDD：`red-links-helper.txt`（模块不存在）→ `green-links-helper.txt`（4 项通过：Linux 走 symlink 且不调用 cmd；Windows symlink 失败后调用 `mklink /J`；两端都失败时抛 `LinkUnavailable`；POSIX 失败也抛 `LinkUnavailable`）。

### 2) 三个调用点统一（`test_workspace.py` / `test_documents.py` / `test_core_creation_failures.py`）

- `test_documents.py:76` 原来**直接** `subprocess.run(["cmd","/c","mklink"...])` → 改为共享函数（Linux 不再触碰 cmd）。
- `test_workspace.py:142` 原来直接 `symlink_to` → 在无特权的 Windows 上 **ERROR（WinError 1314）**，改为共享函数。
- `test_core_creation_failures.py` 原来 symlink 失败即 skip → 改为共享函数，Windows 上现在**真正执行**该越界断言（此前一直跳过）。

### 3) 顺带发现的真实产品缺陷并修复（`ai_union/workspace.py`）

链接能建之后，`test_workspace` 的越界断言**失败**：`validate_config` 扫描时用 `item.is_symlink()`，而 **Windows junction 不是 `is_symlink()`**（是 reparse point），所以指向组织私有目录的 junction 被放过。

修复：新增 `_linked()`（symlink + Windows reparse point 检测），根目录与每个条目都拒绝 junction/符号链接，并额外要求 **`item.resolve()` 必须仍在工作区目录内**（跨平台兜底）。错误信息明确写"不能是符号链接或目录联接"。

这一条是**产品行为修复**，不是测试迁就：Linux 上因为建不了链接，该洞此前从未被验到。

## 验证

| 检查 | 结果 | 日志 |
| --- | --- | --- |
| `tests.test_workspace` | **12 项通过**（3 个 Linux-only 跳过） | [`green-test-workspace.txt`](green-test-workspace.txt) |
| links + documents + core_creation_failures + catalog_integrity + runtime_checkpoints + core_creation + workspace_harness | **61 项通过**（1 跳过） | [`regression-links.txt`](regression-links.txt) |
| 修复前 `tests.test_workspace` 同一用例 | **ERROR** `WinError 1314` | [`red-test-workspace.txt`](red-test-workspace.txt) |
| Python 全量 | 见 [`python-full.txt`](python-full.txt) | — |

之前每次全量唯一的 error 就是这条 `WinError 1314`；本轮之后应当为 0。

## 边界

- 生产目录授权契约未放松，只加强了 junction/reparse point 与解析后的包含性检查。
- 未改 CI workflow（矩阵已覆盖 Ubuntu/Windows，按卡片要求"只有矩阵未覆盖目标用例才改"）。
- 未认领/未改他人卡片；未提交 `management/project.json` 等他人维护文件。
- 真实模型调用 0；未部署。
