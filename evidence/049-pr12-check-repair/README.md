# PR #12 check 修复（2026-11-03）

用户要求继续修复 PR #12；由 Codex 外部工程代理执行，不属于公司自主改善。

## 范围与计划

验收要求：创建组织后回执持续可见，组织切换期间清空旧快照且禁用写操作；身份或服务变化仍重新检查登录。SQLite 备份必须完整且及时释放文件；CI 包含依赖安装和完整 Windows 回归。浏览器脚本遵循现有高级设置折叠，并等待成功读取的刷新响应。

1. 从 GitHub 失败记录定位，复核已有未提交修复。
2. 定向验证身份边界、备份释放和浏览器操作；最小修复新暴露的检查竞态。
3. 完成 npm、Python、浏览器与独立工程复核，推送原 PR 分支并核对远端结果。

本项是用户指定的维护插单；执行期间在制上限从 4 临时调整为 5，远端验收通过后已恢复 4，原阻塞任务保持原状态。

## 原始失败与修复

- PR 基线 `dd590c6` 的 `console-browser` 在 `#operation-result` 超时：组织查询键变化使会话暂时消失，登录边界卸载操作组件。保留占位会话、清空快照并禁止占位状态写入；4 项回归覆盖草稿/身份/服务/401。
- Windows 机制任务的 5 分钟上限包含 SDK 安装，测试未完成即被取消；改为 15 分钟，保留全部检查。
- SQLite 连接上下文只提交/回滚，不关闭连接。备份连接改为 `closing()`，避免 Windows 句柄依赖 GC 释放。
- 小说浏览器脚本先展开高级设置，再填写连接标识。
- 本机浏览器首次修复后通过创建等 41 项检查，在断线重连时捕获了被手动刷新取消的响应。刷新辅助方法改为等待可读取的完整响应体，继续检查 UI 的快照序号。

## 验证记录

本机 Windows / Python 3.13.14 / Node 24.14.0：`npm run check` 通过（前端 51 项），`python -m unittest discover -v` 404 项通过（5 项平台跳过，216.625 秒），工作台浏览器 61 项、小说浏览器 16 项通过。CI 按仓库 `.nvmrc` 使用 Node 24.19.0 和 Python 3.12，远端结果单独核对。原始与新日志分开保存在本机忽略目录 `.union/pr12-checks-20261103*`。

备份测试新增禁用 GC、内容与完整性、立即删除验证；仅在内存中恢复旧连接写法时确定触发 Windows `WinError 32`，当前写法的 3 项重置测试全部通过。独立复核也检查了新增测试与刷新辅助方法，未发现断连检查被削弱。

启动检查 `scripts/check_console_start.py` 5 项通过。

修复提交 `aead41804c381788e36dd0c16418451418f1176c` 的 push / pull_request 共 10 项远端检查全部成功（2026-11-03）：

- [push 前端与浏览器](https://github.com/illusionaireal/Union/actions/runs/41567196985)、[PR 前端与浏览器](https://github.com/illusionaireal/Union/actions/runs/41567202623)。
- [push Linux/Windows 机制与模拟 CLI](https://github.com/illusionaireal/Union/actions/runs/41567196867)、[PR Linux/Windows 机制与模拟 CLI](https://github.com/illusionaireal/Union/actions/runs/41567202502)。
- PR Windows 任务总时长 5 分 3 秒，依赖安装 55 秒、机制与 CLI 3 分 56 秒；验证了旧 5 分钟上限不足。测试退出 0，模拟 evaluate 按预期退出 3，真实模型调用 0。

U-063 按 controlled 范围完成；后续仅验收记录变更，代码修复与实际集成/发布门槛保持分开。

独立工程角色 `review_pr12_boundaries` 只读复核无阻断发现：前端身份与工作区 12 项、重置 3 项通过；Windows 禁用 GC 时备份含原账号、`integrity_check=ok`，原账号清空且备份可立即删除。无授权/删除范围变更。

真实模型调用 0。上述受控检查不代表真实模型集成、组织交付、发布或持续运行验收。
