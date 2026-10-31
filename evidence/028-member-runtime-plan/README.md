# 028 成员执行与托管管理：规划交付

2026-10-30；代码基线 `dev@66a1f69`。本轮用户只要求plan，未修改运行时代码、配置实际主机、调用模型或启动组织。

## 交付与依据

- [实施计划](../../specs/028-member-runtime-management/plan.md)：部署位置、当前可复用代码、U-041观察与U-042托管控制两阶段、真实验收依赖及后置范围。
- [规格](../../specs/028-member-runtime-management/spec.md)：公开状态投影、权限矩阵、版本/恢复规则、A01–A12验收。
- [实施清单](../../specs/028-member-runtime-management/tasks.md)：可逐项执行的开发切片。

实际核查了 activity/runner/service/harness/workspace/observation、Members/Resources页面及现有systemd模板。当前是单AU互斥串行派发、持久任务会话、按命令启动容器且业务目录团队共享；没有成员独立服务器、远程Worker池、岗位级业务文件隔离或已验收的持久托管。

主账新增U-040文档交付、U-041下一实现切片、U-042后续托管控制、U-043并发候选。U-008/U-005/U-009/U-020继续承担真实部署、工具、恢复和指标验收；不另开同义“真实上线已完成”卡。U-007/U-037两个已开工阻塞项保留，在制上限不变。

## 验证口径

只验证文档、本地源码引用、主账/生成视图及既有工程回归。代码中的现有能力来自基线，计划里的控制器、runtime_manage和新增页面投影均未实现。实现阶段需另一工程角色复核观察/控制权限，本文自检不替代该复核。

本轮没有浏览器、真实New API、模型或实际systemd运行验收，不解决027的浏览器安装阻塞。

## 实际检查结果

- `npm run check`：通过。包括8项管理测试、历史计划完整性、9项离线动作安全测试、前端类型检查、20项组件/交互测试与生产构建。
- `.venv/bin/python -m unittest discover -v`：200项通过，61.450秒。它验证既有工程回归，不验证本计划尚未实现的能力。
- `npm run management:render` 与最终 `npm run check:management`：通过；15模块、8里程碑、43任务，生成视图一致。
- 变更及新增Markdown的316个本地链接：目标全部存在；`git diff --check`通过。
- 仅修改规划和管理文档；现有未跟踪的 `docs/research/` 未纳入本次提交。
