# 成员的隔离工作区

016 为现有 Deep Agents 成员循环增加可选 `workspace_execute`。成员可以通过命令读取/修改代码、运行本地测试；团队共享 `/workspace`。组织仍自行选择岗位、成员、工作与工具。平台和章程不会自动授予宿主访问。

**当前工程接入已经实现，真实 Docker、真实模型自主开发与服务器部署尚未验收。** 本环境没有 Docker 或模型凭据；仅通过 SDK、HTTP及容器适配替身的机制检查。原公司仍待筹建，不改写历史运行事实。

## 三层条件

1. 宿主用受信 CLI 绑定一个独立业务目录和本机预先安装的镜像。镜像必须包含所需 Python/Node/测试依赖，且不含凭据；运行期间无网络，不会拉镜像或下载依赖。Docker daemon 是宿主信任边界，本轮支持 Linux 本地 `/var/run/docker.sock`。
2. 董事会通过既有修章入口，将 `workspace_execute` 加到该组织的 `allowed_tools`，同步修订正文，明确业务范围；旧公司章程不自动扩大。
3. 筹建 Agent 在 `prepare_member` / `initialize_organization` 的成员 `tools` 中按职责选择该工具，或成立后由有权限的组织负责人通过 `update_position` 调整岗位权限。只在当前有效任职的正式工作轮暴露工具，决策轮及连接测试不执行业务命令。

不满足任何一层就不能执行。一次工作轮只接受单独一个工作区命令；模型不能指定目录、镜像、网络或 Docker 参数。绑定不等于 Docker 可用或测试通过。

## 宿主准备

使用专用非 root 系统用户，并为工作区设置独立磁盘容量配额。适配器限制内存、CPU、进程、临时文件、命令时间和返回输出，**不实现 bind 目录的磁盘配额**。不要把运行系统、组织数据库、API Key、董事会凭据或有认证信息的 Git 目录挂进业务容器。工作区内容视为成员可以修改的数据；宿主不得直接执行其脚本。

从已审查提交导出干净快照到全新的独立目录。例如在 `/opt/union` 的受信仓库执行以下命令（目标目录须不存在，路径按实际主机调整）：

```sh
mkdir /var/lib/union-workspaces/ai-union-corp
git archive HEAD | tar -x -C /var/lib/union-workspaces/ai-union-corp
```

初次绑定会拒绝符号链接、特殊文件、`.git`、`.union`、`.env*` 和已知私有凭据文件；这不代替管理员检查整个快照是否含秘密。目录须由运行服务用户拥有，容器使用该用户 UID/GID；宿主为 root 时容器使用 65534，不能假设它可写 root 拥有的目录。

准备受信镜像后，以 `docker image inspect --format '{{.Id}}' IMAGE` 取得完整 `sha256:...` image ID。新镜像/依赖只能由宿主按授权准备，当前成员工具没有网络、Docker socket 或宿主安装权限。本轮不提供已构建/已验证的镜像。

私有配置 `workspace.json`：

```json
{
  "directory": "/var/lib/union-workspaces/ai-union-corp",
  "image": "sha256:替换为本机完整64位image哈希",
  "timeout_seconds": 60,
  "enabled": true
}
```

公司 `status` 返回真实组织目录。以下 `ORG_ROOT` 是该目录，不能填写 Console 服务根：

```sh
.venv/bin/python -m ai_union.workspace --root "$ORG_ROOT" configure \
  --config workspace.json --board-key-file "$ORG_ROOT/board.key" \
  --reason "为产品开发绑定独立代码工作区；宿主已核对镜像、内容与磁盘配额"
.venv/bin/python -m ai_union.workspace --root "$ORG_ROOT" status
```

配置/停用与模型运行互斥。需要紧急停止新派发时，先在工作台请求暂停；等待已在途命令回执或进入未知核对，再执行 `disable --board-key-file ... --reason ...`。`disable` 不要求工作区仍存在，也不删除未知命令记录。改变目录或镜像需要重新配置；不因目录中的业务文件变化自动重配。

## 命令、交付与恢复

命令在只读根、无网络、无 Linux capabilities、非 root 容器中运行，只挂载一个业务目录。最长120秒、输出最多64KiB；宿主无 Docker 时明确拒绝，绝不改用宿主 shell。每条命令先持久预约，再执行；同一 run ID 不重放，也不允许换成第二条命令。已有的模型累计调用限额继续生效，命令不会绕过模型派发的计账。

Docker 客户端退出后，必须取得容器 `State` 的已退出证据才记录退出码；连接丢失、超时、中断或回执无法持久化，都保留待核对状态。命令成功仅说明容器退出结果，不证明测试充分、代码正确或已经发布。成员应在正式成果中写明实际修改、测试命令及输出、命令回执 ID 和限制；下一成员可以读取共享代码。虚拟文件工具仍只用于各自任务草稿。

`workspace status` 是宿主诊断，包含命令和输出，可能包含业务内容，不应直接公开上传。工作台活动只展示完成事件中的关联 run/work ID 和退出码，不暴露宿主路径。

若有未知命令，先核查该回执中的容器名称：确认容器已停止，检查业务文件及已发生的改动；通过原 `ai_union reconcile` 核对运行，再通过 `ai_union.workspace reconcile --run-id ... --board-key-file ... --reason ...` 保存容器停止与文件检查依据。核对封存原命令，不重放；需要后续工作时由组织另作决定。

## 上线前仍需完成

- 在目标主机真实验证镜像、文件读写、测试依赖、网络及私有目录隔离、磁盘配额、进程终止和重启后的未知核对。
- 接入授权模型，完成至少一次真实的“安排开发 → 修改 → 测试 → 另一成员复核 → 根据结果继续”的组织交付。
- 为部署和运营另行接入受限、可追溯的接口；本工具没有公网发布、仓库远端提交或生产系统管理能力。

因此这次接入消除了“运行时没有可插入真实开发工具”的代码缺口，但尚不构成公司已自主运营的证据。
