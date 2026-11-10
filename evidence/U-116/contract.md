# U-116 / #70：固定上游补丁比较契约

2026-11-11。输入 `cb3fa500847f8dc3ce75488f85fd40d49e69082c`。
PR87@`0e8a14467255f3dd20665c07cc506589c3598368` 的真实 CI 作业
130143042945、130143447040 均在 `prepare.mjs:25` 的补丁比较失败；配对
Windows 作业被矩阵取消。本机同一校验也失败，已核对唯一差异为 Git 自动
10 位 blob SHA 与固定补丁头的 7 位 SHA；源码补丁内容相同。

这是从 #55 独立客户端验收拆出的通用构建阻塞，约 1–2 小时一个工程结果。
#55 原 owner/review 与完整权限验收保留，不把构建修复算作新 API 能力。

冻结行为：

- 相同 Git 内容与固定补丁，不因 `core.abbrev=12/40` 或对象库大小改变而拒绝。
  比较使用记录补丁采用的 Git 显示格式；不修改用户或 CI 的全局 Git 配置。
- 仍比较完整规范化 diff；任何额外已跟踪源码改动、错误 hunk 或不同补丁必须
  拒绝。保持现有 CRLF/LF 规范化，不通过删除 index/hunk/正文来放宽校验。
- vendor commit、原补丁、依赖锁、运行时接口和真实资源授权不变。新构建 helper
  必须纳入发布器 source_hashes，不能丢失构建输入追溯。
- 先提取现有比较行为，真实临时 Git 仓库设置不同缩写得到 RED；再最小固定
  diff 输出格式得到 GREEN，保留额外源码拒绝控制。不修改产品正常行为制造 RED。

实施 actor：Codex CI duty session `01a1c746-eb38-7711-ad90-290392a05d89`；
online member `codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`，
不是产品 AU 成员。验证包含 Node 行为回归、npm check、Python 全量、受影响
SDK 构建/检查和准确 head CI。原 CI 与本机失败均保留；不盲重跑旧作业。
