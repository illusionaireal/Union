# U-079 / #33：巡检来源故障隔离

2026-11-08，codex-home 实施与自检。现有巡检在 Kanban 连接失败后提前返回，GitHub/NAS 都没有被检查；这是用户已授权的部署值守职责内修复。预计小于 2 小时，单一可验收结果，不另拆卡；在线服务不可用，未伪造新的认领或状态更新。

编码前已补充 ops/automation/OPS_WATCH.md 契约。看板、GitHub、NAS 分别尝试读取，独立记录本轮观察。部分失败保留原完整 snapshot、last_success、fingerprint、pending；不触发自动 Agent、不确认已处理。错误只保存类型。未配置代理时传空映射，保留已配置代理的行为。

严格 TDD：两个新增用例先在“没有尝试后续来源”断言失败；恢复诊断用例因字段缺失失败。真实 HTTP 还复现空代理 `no host given`，随后本地回环 HTTP 用例也先失败再修复。最终 11 项巡检测试通过，涵盖原 7 项信号/互斥行为及 4 项新增回归。见 source-isolation-red.log、source-isolation-green.log；真实 HTTP 的 RED 记录为 failed != ok。

宿主已原子替换巡检脚本，保留旧版私有备份，Agent 仍 disabled。实际运行见 live-observation.json：2026-11-07 23:30 UTC，Kanban 失败，GitHub 和 NAS 成功；NAS running、OOM=false、restart=0。完整成功时间仍停留 22:19:30 UTC，未冒充本轮完整成功。所有观察/地址/密钥原件均留在宿主，本目录仅保留脱敏结果。计划任务仍每五分钟运行；网络错误不会再跳过部署健康检查。

本次没有替换 NAS 业务服务、迁移数据或调用真实模型。其他安装/模型验收分别见 U-074/U-075。原部署接入证据见 ../073-deployment-watch/README.md。

本地回归：隔离实现的 Python 全量 632 项通过、8 跳过（356.791 秒）；随后新增的空代理修复经过独立真实 HTTP RED/GREEN，最终巡检 11 项通过。最终 npm run check 通过。精确提交树以本 PR 的 Windows/Linux CI 为准。

12:44 后续：用户指出四小时没有推进，已确认并修复硬登录门槛及部分故障阻止 Agent 的问题；真实 CLI 执行通道已验证，见 [自动处理恢复](agent-resume.md)。上面的只读运行证据保持原历史范围。
