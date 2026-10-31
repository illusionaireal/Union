# UNION 外部开发调度器

按 `union-astra-sol-vps-handoff-v1.md` 实施；这是外部工程工具，不是 AU 成员或公司运营。部署记录、未通过项见 `evidence/030-dev-orchestrator/README.md`。

控制器使用 Python 标准库与 SQLite；专用 dev checkout 串行执行，不推送、不部署生产。模型固定 Astra / Sol / Astra。宿主配置和证据与目标仓库分开；模型输出不能指定宿主命令。模型调用、验证均经固定容器入口，日常角色没有 Docker socket。首次真实验收前保持 disabled。

## 本次部署

SSH `root@192.168.1.29:222`；安装根目录 `/volume1/docker/union-dev`。`Union/` 是专用 dev 副本，原 Synology 同步目录未被覆盖。`controller/` 和宿主 JSON 配置由 root 维护；`state/` 属于 UID/GID 10001；工作及验证容器使用 UID 10002/GID 10001。DSM systemd 219 无法解析无 passwd 记录的数字 User，受信 `union-dev` 包装器在进入控制器之前清除附加组并永久降为 10001。root broker 只执行固定镜像、挂载、模型和测试 profile；该 socket 不进入任何容器。

镜像工具链：Node 24.19.0、Python 3.13.5、Codex CLI 0.166.0、Chromium 156.0.8078.73。部署镜像使用实际构建的内容 SHA；基础镜像复用 NAS 已缓存的公开镜像，仅使用镜像层，不挂载现有 Hermes 服务/数据。Docker 的旧代理不可达，未改全局 daemon 设置或其他服务。DSM 不支持 CFS 的 `--cpus`，使用 4GB 内存限制和 CPU shares；shares 不是 CPU 硬上限。

通常验证使用 `network=none`。浏览器脚本使用固定专用 internal bridge `union-dev-validation`，禁止宿主网桥 IPv4 分配、不发布端口、不连接生产容器；实际检查 NAS SSH 和外网地址均不能连接。原因是 Chromium 在只有 loopback 的环境将 navigator.onLine 判为 false，虽然本地 API 正常返回200，导致原浏览器用例等待连接超时。此调整不改产品代码或测试断言，不启用公网访问。实现依据：[Docker internal network](https://docs.docker.com/reference/cli/docker/network/create/)、[bridge inhibit IPv4](https://docs.docker.com/engine/network/drivers/bridge/)。DSM 实际路由表仍有默认项，不宣称“没有默认路由”，边界以配置及拒绝连接实测为准。

## 操作

```sh
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev status
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev preflight
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev once --dry-run
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev pause
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev inspect RUN_ID
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev reconcile RUN_ID
# 仅在确认原作业结束、已审查证据后显式归档；保留代码与预算，不重放
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev reconcile RUN_ID --resolve blocked
ssh -p 222 root@192.168.1.29 /usr/local/bin/union-dev resume
```

`resume` 只清除暂停意图，不修改 `enabled` 或资源策略。未核对的作业阻止恢复。只读命令不消费模型；`preflight --probe-models` 是显式收费/额度动作，仍受沙箱、凭据隔离与预算门禁。`once --trial` 用于首次真实验收，不能绕过资源/权限门禁。每轮失败保留证据与代码；不要用 reset/clean 清除。

`install.py` 部署 broker、service/timer 和 CLI；适配 DSM 旧 systemd。timer 已安装但未启用，`enabled=false`、`max_calls=0`。本机断线后安装/验证容器继续运行已观察到；长期模型任务、整小时重叠、本机关机和未知供应商响应仍须独立验收。

## 当前禁止启用真实派发的原因

实际 `codex sandbox linux -- ...` 返回 bwrap 无法创建 user namespace。Docker 共享 DSM 4.4 内核，换容器发行版不能改变内核能力。独立 `codex login --device-auth` 返回 HTTP 403，未产生认证文件。不能关闭 Codex 沙箱、挂载 Docker socket或降级模型绕过。

此外，凭据文件与工具的读取隔离尚未实现并实测；只读挂载不足以证明秘密不可读。`sandbox_verified` / `credentials_isolation_verified` / `model_access_verified` 必须维持 false。后续需要新版 Linux VM/执行节点、可用官方认证和有限额度、假凭据拒读与独立复核，再做 E02/E03。官方资料：[非交互执行](https://learn.chatgpt.com/docs/non-interactive-mode)、[权限配置](https://learn.chatgpt.com/docs/permissions)。

## 证据与恢复边界

SQLite 调用预约先于 broker 请求；OS 锁固定在仓库 `.git` 内，另有 broker 对仓库标签和未核对预约的检查。具名容器和原始 Docker 日志保留，不依赖 SSH 会话。未知不重试，不释放调用预约；`reconcile` 仅查询原身份，下一阶段不会自动执行。不要仅凭当前容器不存在判断从未执行。

证据按 run/job ID 保存，修正前失败日志保留；完整 diff、内容 SHA、文件模式、HEAD、固定测试结果通过门禁才提交明确路径。代码和主账采用两个本地提交，收口中断时保留已完成的第一个提交，核对后处理。主账完成只记受控外部工程结果，不称公司自治。

当前限制：日志响应单行 JSON 上限16MB，超限会失败并保留原容器；未实现分块读取。四小时是控制器停止派发/观察的边界，运行中的原容器可能继续，不能宣称强制计算停机。磁盘配额/日志保留与清理策略尚未实现，未知作业证据不得清理。它们均是启用长期调度之前必须补齐的工作。

测试：`python -m unittest tests.test_dev_orchestrator -v`；最终Linux全量279项含本模块19项通过，Windows本模块17项通过/2项平台跳过。包含受控失败→修正→验收→代码和主账提交、WIP到限不写账不派发。替身测试不建立真实 Astra/Sol 调用结论。
