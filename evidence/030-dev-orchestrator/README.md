# 030 / U-044：NAS 外部开发调度器部署

> 2026-11-02 运维信息脱敏：实际地址、SSH 用户/端口、私有目录和证书指纹改为占位说明；历史验证结论不变。当前连接信息应取自宿主私有配置，本文件不作为连接配置。此编辑不构成对部署脚本的新复核。

2026-11-01。用户要求以已授权 SSH 主机为基地完成 Astra/Sol 交接文档。交接原件仍在用户下载目录，SHA256 `95f2743843406ba172508d01771a65c13ff2b8b12de7c1f865db1af144ff8988`。

## 当前结论

已部署**默认关闭**的控制器、固定容器 broker、专用 dev checkout、systemd 服务和未启用的小时 timer。工具链、Chromium、项目基线回归与网关浏览器验收有真实执行证据。真实 Astra/Sol 模型调用数 **0**，未形成双模型链，未启用自动开发，不表示公司成立或自治经营。

主机实际为 Synology DSM 7.3.2 / Linux 4.4.302+，不是文档建议的 Ubuntu VPS。Docker24.0.2、约18GB内存，部署位于 `${UNION_DEPLOY_ROOT}`，未覆盖原同步仓库或其他容器数据。日常控制器 UID10001；Worker/Validator UID10002；根权限仅用于安装与固定容器 broker，Docker socket 不进入执行环境。

初始远端 `b39c06c` 不含交接后续源码。用户随后推送验证快照 `53dd96bde22bf95c149929c686ead7dc5ddaa579`，专用 dev 副本无在途作业时已快进。原六个提交 SHA 没有随快照导入，不声称其祖先关系成立。本地 Windows 原 checkout 仍有大量用户既有改动，本轮没有 reset/clean、整体暂存或覆盖。

## 实际验证

- 固定工具版本：Node24.19.0、Python3.13.5、Codex0.166.0、Chromium156.0.8078.73；实际镜像内容 SHA `1d6e909941870743eb6677a392e685df38c4c346d7dd1eb4f83a258ba83b1dac`。
- 专用低权限容器完成 `npm ci --ignore-scripts`、venv/锁定依赖安装和 React 构建，退出0。Chromium 实际启动、页面 title 断言、关闭，退出0。
- `53dd96b` 加本轮最终改动后的 `npm run check` 退出0，包含31项前端及管理/历史检查；最终 Python 全量**279项通过**（其中控制器19项），75.644秒。先前278项也通过，原记录保留。Windows控制器19项中17项通过、2项平台跳过。
- 工作台实际 Chromium **61项通过**；网关 **12项通过**，均为显式 fixture/本地HTTP替身、真实供应商调用0。
- [网关检查](gateways/checks.json)、[1440px截图](gateways/gateways-desktop.png)、[320px截图](gateways/gateways-mobile.png) 已审阅：窄屏无横向溢出，按钮、表单、来源/部署未知提示可见。结合既有[独立权限复核](../../docs/reviews/2026-10-30-gateway-management.md)满足 U-037 的受控验收；真实 New API 仍是 U-039。
- 初次 browser/gateway 均因 network=none 导致 navigator.onLine=false 而超时，API实际200、无JS异常。原失败私有日志保留。浏览器使用专用 internal bridge、不分配宿主网桥IPv4、不发布端口后通过；未修改产品代码或测试断言。有限连接探测中NAS SSH及外网不能连接，不将其扩写为所有协议的全面隔离证明。普通验证继续network=none。
- `union-dev status/preflight/once --dry-run/pause/resume` 实测；默认关闭的 systemd once 正常退出，broker active且开机启动，timer disabled。安装/验证容器跨多次SSH会话继续工作已观察；不是本机关机或真实长作业验收。

原始安装、测试、诊断、失败与具名容器日志留在 NAS `install/`、`broker-jobs/` 和 Docker；未提交认证/原始模型事件。Windows原工作区 `npm run check` 因既有 Artifacts 类型不匹配失败；Python207项记录1失败50错误5跳过，主要为Windows SQLite文件占用清理、代理条件及符号链接权限；这些失败被保留在本地忽略的 `.union/dev-orchestrator-validation`，不以NAS通过掩盖。

## E01–E10 逐项口径

| 项目 | 本轮事实 |
| --- | --- |
| E01 | 部分通过：SSH、依赖、Chromium与关闭服务可用；Codex沙箱不能使用 |
| E02 | 未通过：设备登录403，真实模型探测0；resolved_model未知 |
| E03 | 未执行真实双模型链；代码有受控替身验证 |
| E04 | 受控失败→修正→独立验收合同→两个明确提交通过；非真实Sol修复回执 |
| E05 | Linux OS锁/不同状态目录/在途broker拒绝已测；超过一小时重叠未执行 |
| E06 | 预约、未知、原身份核对、不重放有行为测试；真实模型中断与恢复未验 |
| E07 | 空队列、预算、暂停、未验证沙箱禁止派发有测试；无续费/采购 |
| E08 | HEAD、diff、哈希索引、测试日志、文件模式漂移拒绝有测试 |
| E09 | 受控认领/WIP、验证/接受、主账生成和精确提交有测试；真实Astra/Sol接受未验 |
| E10 | SSH查询/暂停和固定服务安装已测；timer关闭，小时持续运行/本机关机未验 |

## 阻塞与后续

实际 `codex sandbox linux -- ...` 退出1：`bwrap: Creating new namespace failed`；未降低沙箱。独立无凭据设备登录容器得到官方HTTP403，未生成认证文件。默认 `enabled=false`、`max_calls=0`、三个验证标志false，控制器与broker双重拒绝派发。

另有代码边界尚不能启用：真实凭据必须在工具/测试中不可读，当前尚未实现并实测；完整日志单行传输16MB上限、磁盘/日志保留政策、强制资源停机等见[操作手册](../../ops/dev-orchestrator/README.md)与[独立工程复核](../../docs/reviews/2026-11-01-dev-orchestrator.md)。复核只允许关闭部署。

下一步先选择新版 Linux VM（仍以NAS存储/SSH为基地）或另一执行节点，验证沙箱与假凭据拒读；再通过官方登录、确认有限订阅/调用范围与路由证据，执行E02/E03及其余真实验收。U-041仍有最新交接中的热配置、真实恢复及整体复核缺口；不因本轮有浏览器就自动关闭。现有小时ChatGPT开发任务的写入者切换尚未确认，不能同时开启新timer。
