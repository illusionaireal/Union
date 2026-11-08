# U-077 在线运行态修复

2026-11-08 / codex-home / 当前 Codex 工程会话。契约先冻结于 management/OPERATIONAL_CONTRACT.md；原审查的双状态漂移已在真实 CLI/MCP 控制流中复现。

RED：最初 6 个反例全部失败：在线独有 U-077 被本地拒绝、未查询在线 owner/deps、MCP 可覆盖他人 assignee、CLI 未发 PATCH 因而无法读回冲突、缺证据先写 done、忽略在线 WIP。增加选卡器测试再次观察 RED：返回他人 U-067 progress，而期望无可认领卡。

GREEN：共 37 个离线测试通过，其中 12 个回环 HTTP 行为反例覆盖 CLI/MCP、选卡、HTTP 409/202/响应丢失、无配置、完成预检、阻塞 WIP、幂等与保留已开工责任；25 个历史管理/本地镜像测试保持兼容。所有网络为回环假服务，未据此宣称线上完成。

改动：共享 kanban-operations；运行态不依赖 project.json，不自动镜像，不抢占在线 owner。当前服务端没有明确 WIP 配置时显示未配置；客户端检查并不提供跨卡全局事务。

验证命令：`node --test tests/kanban-operational.test.mjs tests/union-board.test.mjs tests/project-management.test.mjs`，并纳入 npm run check:management。原始输出保存在宿主运维目录；本目录只保存脱敏摘要。

线上读回遇到连接失败，真实 #31 认领/更新尚未确认。修复受控证据不代替线上采纳。长期本地台账不因“缺卡”阻止后续在线独有任务。
