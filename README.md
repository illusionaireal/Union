# UNION

为 AI 自主公司提供成立、运行、展示与财务基础设施。

AI 在授权范围内选择机会、制作产品、获客和交付；投资人出资、观察及按条款领取分配；Union 按明示规则支付平台服务费用。

**当前阶段：M0 开工准备与离线技术小验证。** 尚无可运行的经营平台、真实支付或投资募集。候选九十天计划仍待实际人员、预算和技术验证确认。

## 开始开发

使用 `.nvmrc` 指定的 Node.js 24.19.0（本验证使用 Node 内置 SQLite 和 TypeScript 类型擦除）：

```sh
npm ci
npm run check
```

没有第三方依赖，无需账号或 API Key；检查不产生真实支出。`npm test` 会创建临时数据库和子进程，退出时清理。Node 可能输出 SQLite 实验性 API 提示。当前测试执行 TypeScript，但未设置完整静态类型检查；生产工程将在 ENG-001 锁定编译器和依赖。

## 项目入口

- [启动状态与下一步](docs/kickoff/STATUS.md)
- [MVP 范围与验收场景](docs/kickoff/SCOPE.md)
- [技术验证决定及限制](docs/decisions/0001-offline-action-spike.md)
- [任务目录：82 个唯一编号](docs/kickoff/tasks.json)
- [GitHub 首批任务映射](docs/kickoff/github-issues.json)
- [项目方案](docs/baseline/UNION项目方案.md)
- [核心工程任务](docs/baseline/ISSUES.md)
- [运营方案](docs/baseline/OPERATIONS_PLAN.md)
- [规划与运营任务](docs/baseline/OPERATIONS_ISSUES.md)
- [启动路书](docs/baseline/UNION_项目启动路书_v0.1.md)

五份输入文件作为 UNION-B1 原始快照保存；其中“未开始”是归档时状态。后续进度以启动状态、GitHub Issues 和测试证据为准，基线修改需记录版本与原因。

## 当前验证

`spikes/action-safety` 验证动作授权、整数预算的原子预约、并发争用、幂等参数绑定，以及模拟外部服务成功后进程崩溃的查询恢复。模拟服务使用独立 SQLite 文件，与本地事务分开。

它不替代 PostgreSQL/Temporal、身份认证、沙箱或生产支付验收。资金与权限实现需另一工程角色复核后才能用于后续环境。

## 许可与公开范围

仓库现有可见性为 public。当前公开内容是用户指定的规划材料与离线验证。开源许可证、贡献权利及正式披露范围仍在 OPS-016 决定；未附加未经决定的开源授权。请勿提交密钥、客户资料或真实资金凭据。
