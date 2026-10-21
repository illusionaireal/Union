# 启动 ai-union-corp

本公司负责建设和运营 AI-UNION 与 ai-union-platform。目标、阶段章程与首次有限调用配置在 [公司配置](../examples/ai-union-corp.json)。公司自行决定成员和任务；`prepare` 只保存筹建条件，不产生团队、模型请求或费用回执。

## 当前环境启动

在 `dev` 安装固定 Python 依赖、Node 依赖并构建 React（详见 [开发说明](DEVELOPMENT.md)），然后：

```sh
.venv/bin/python -m ai_union.corp --root .union/ai-union-corp prepare --board-name "Benedict.Zeng（依据启动公司指令）"
.venv/bin/python -m ai_union.corp --root .union/ai-union-corp status
.venv/bin/python -m ai_union.corp --root .union/ai-union-corp serve --port 8766
```

`prepare` 使用同一创建请求，只接续原公司。修改 profile 或采用人不会覆盖原采用内容，后续调整使用原有资源/章程操作。创建存储不确定时保留原回执和分配目录；禁止删除目录重建以抹除记录。此入口不启用 fixture；网页只提供 API 执行器，不自动启动模型。公司保持暂停，等待实际连接和启动操作。

一次性本机会话链接保存在私有服务目录 `local-access.json`，10 分钟内使用；不要把链接/文件提交到 Git。工作台绑定 127.0.0.1。`status` 只读，可与服务同时使用；`prepare` 在工作台运行时应先停止服务，避免争抢 Console 锁。

## 连接模型与正式筹建

进入工作台“模型与 API”，配置已获授权的模型连接并设为公司默认。配置本身不调用模型。工具往返测试会占用两次真实调用，成功也不代表组织经营通过。只有同一连接 ID、版本、真实供应商的成功往返才显示已验证。

按原有 [API 使用步骤](API_MODELS.md) 测试和启动，继续保留每次调用、失败、未知结果及 token/费用不确定性。公司默认资源为累计最多32次、每次最多180秒；这是拟采用的有限筹建资源，不是32次调用或金额支出已经发生的证明，也不是自动使用付费模型的授权。现有授权为免费模型的范围不得扩大为收费模型。无可用连接时，保持待筹建；不得用 fixture 填成员或成果。

`status.can_attempt_bootstrap` 只说明本地配置允许尝试，不证明 API 可达、模型能力、持久托管或自主运营。`tool_roundtrip_verified` 独立显示，不通过环境变量存在与否推断。当前 `operating_blockers` 固定列出尚未实现的成员开发工具和未取得证据的持久主机；后续真正接入并验收后应由实现与证据消除此缺口，不能新增一个“已准备好”开关掩盖它。

## Linux 持久主机安装

当前 Python/SQLite 运行时需要可持久写入并执行 Python 的主机。Cloudflare Containers 在本轮账户检查中返回需要 Workers Paid；本轮没有升级套餐或部署。普通 Workers 静态站点不能承载现有运行时。

已具备合适 Linux 主机时，由运营者将 `dev` 安装到 `/opt/union`，建立专用 `union` 系统用户，安装 `.venv` 固定依赖并构建前端；将私有公司服务目录放在 `/var/lib/union/ai-union-corp` 并仅授予该用户访问。先停原服务再迁移整个目录，保留所有 SQLite/WAL、资产、执行记录和凭据；不要只复制主数据库文件。备份也须视为秘密，不提交到仓库。

运行 prepare 后，status 返回的 `organization_root` 才是实际组织目录；它不同于 Console 的服务根。将此绝对路径写入 `/etc/union/corp.env`，示例：

```ini
UNION_ORGANIZATION_ROOT=/var/lib/union/ai-union-corp/organizations/3a628ad66d73c815dadccee503719eedad7ad8f423a6075932317817fc15fc66
```

目录名称由稳定创建请求派生，仍以实际 status 输出为准。环境文件中不需要重复保存模型 key；原工作台的私有连接存储继续使用。代理/CA 如有需要应在主机按其实际环境配置，不能关闭 TLS 校验。复制 [运行服务](../ops/systemd/ai-union-corp.service) 与 [私有工作台](../ops/systemd/ai-union-corp-console.service) 到 systemd；先核对模板路径、用户和目录权限，再安装。

工作台通过 SSH 端口转发从运营者本机访问；在保留 Host/Origin 的 127.0.0.1:8766 打开原一次性链接，不把现有本机会话机制直接暴露公网。示例转发：`ssh -L 8766:127.0.0.1:8766 USER@HOST`。模板不会配置 SSH、域名、账号或公网身份服务。

模型连接、工具测试和预算授权就绪后，在工作台显式有限启动；该作业结束且派发仍启用后，才能交给常驻 runtime 服务接续。不要让网页作业和服务竞争同一组织。服务每个窗口最多32次/86400秒，累计上限仍取组织数据库；跨窗口不补额度。退出2（资源到限、暂停、失败或未知）不自动重启；在途主机崩溃在下一次恢复时成为 unknown，必须核对。空闲只监听，不调用模型；正常窗口结束可重启接续。

安装后必须验证开机启动、掉电/在途执行恢复、无事件空闲零调用、事件唤醒、额度到限和暂停。模板存在或进程存活不能替代这些验收。本轮只准备模板，没有主机安装与重启验收。

## 公司实际开发和运营所需的剩余能力

成员 Harness 当前只能产出文本及虚拟任务文件，不能直接读写代码仓库、执行测试或管理部署。下一工程里程碑是接入隔离的开发工作区、已有 Agent 编码执行器、实际验证回执及可审查的代码变更；发布、权限/资金变更继续按董事会边界与工程复核执行。这是本公司的业务需要，不是所有 ai-union 的统一前置条件。

本轮由宿主工程代理实施的仓库代码及测试属于用户授权的工程工作，不是公司成员已经具备这些工具的证据。尚无真实收入、融资、公司法律登记或自维持证明。
