# U-086 / #40：收尾就绪度陈述（2026-11-10）

本文件只汇总 **当前已核实/未核实的事实**，供值守与协调者做关闭判定；它本身不关闭
任何出口，也不把未验证项写成已验证。执行者为 DSH 开发会话
`dsh/deepseek-v4.1-flash/DESKTOP-SA4MRG7`（在线成员 HOME-GOOSE /
`cafeef64-ac40-4062-97c1-ac82ece0a379`，ID 分别记录）；真实推理 0、无部署、无迁移。

## 卡的验收原文（在线卡 #40）

> 看到原请求真实输出后取消；分别记录取消受理/modeld interrupted/远端事实；
> 未知留预约、确认完成才 used，重开不派发新请求。

## 已覆盖（受控工程面，本轮可复核）

- 集成 head `faa5a4ca98331657a78546f9f1480734a959a01f` 上：
  - Node `npm test -- exit22` = **306/306 通过**；
  - 全量 Python `python -m unittest discover -v` = **Ran 812 / OK (skipped=11) / exit 0**
    （见 [daily-full-python-faa5a4c.md](daily-full-python-faa5a4c.md)，含私有日志摘要）。
  - 本地前端面 `npm run check:console`（tsc + 相关前端/浏览器用例 + 打包）= **exit 0**：
    2054 modules transformed、`dist` 主包 563.89 kB（gzip 174.04 kB）、构建 6.75s
    （日志摘要 sha256 `f0d96f88e5a978b4dea85ab341c2edd955ccd11ac955bcaf0697fccc8d67b921`，
    原日志未提交）。
- 本卡目录内的多个增量各自带合同、可执行反例与验证记录（逐项索引见本目录 README；
  本轮未逐条重跑）：取消边界、取消交付、页面取消动作、取消响应断体、登记响应断体、
  观察结算、预算守恒、成果来源、重开下载、材料读取、最终中断复核等，均以实际
  Chrome / Core HTTP / SQLite 与替身模型成对观察 RED→GREEN。
- 既有的独立工程角色复核（非实施者自批）：PR44 采用记录 review `5820485820`
  覆盖权限/身份/原 run_loop 与取消恢复、观察完整性与 unknown 预约；PR70/PR73 的
  取消读取与能力声明各自经过值守复核后再采用。
- 索引完整性（2026-11-10 本轮核对）：`evidence/U-086` 全目录 71 个 markdown、
  144 个相对链接**解析全部可命中（0 失效）**；外部 http(s) 链接未逐一访问，
  不作为已验证内容。

## 未覆盖（真实出口，仍未完成，不得据此关闭）

本卡后续确实做过**真实派发**（`deepseek-v4.1-flash`；`evidence/127`–`139`，其中 139 为门控版 118/118），
因此不能再写「本卡所有运行都是替身模型」。但按 [原 ID 补证映射](original-id-supplement-2026-11-10.md)
的两层判定（驱动报告 / 存档可核对），下列各条仍有实质缺口：

1. **看到原请求真实输出后取消** —— 139 的驱动报告有 `original request text observed before cancel`
   与有序公开文本/工具观察标签，但**事件正文未入库**（只留哈希与 UTF-8 字节数），
   不能升级为完整页面验收。
2. **取消受理身份与远端事实** —— 驱动报告声称回执与提交命令/attempt/step/model request 一致，
   但存档内嵌回执 **在 192 字符处截断**、提交命令与配对 POST/GET 正文未入库，
   第三方无法逐字段重算；modeld 真实中断回执缺失；远端是否已取消必须保持 unknown。
3. **真实用量/费用** —— 每个 run 内可见两条模型请求记录（1 `used` + 1 `unknown`），
   已知用量子集 139=438/46、134=438/40；被取消请求用量缺失、`cost_status=unknown`，
   不得补 0，也不得把「单次派发」写成「一次模型调用」。
4. **同运行前后事实** —— 127/128/129/134/136/137/138/139 八个 `snapshot-before-restart.json`
   全部是 117 B 的 `unsupported_capability`，**前侧缺失且不可事后重建**；后侧（`reserved=1`、
   unknown 以原身份存活）只能单侧成立。曾把根因记为「catalog 行 legacy_v0 与目录 core_v1
   不一致导致整次 `/api/session` 409」，但本轮复核发现该不一致会先以 `incompatible_state`
   结束、且 `session_info` 会跳过 core 条目，故**根因仍未证实**
   （[归因与反证](session-409-during-core-creation.md)）。已交付的
   [修复候选 9472a64](session-409-skip-fix.md) 只覆盖「单个不一致条目不应拖垮 session」这一
   **稳健性缺口**，**不声称**修好了 117 B 前快照；第 4 项仍需一次有界真实运行取证。
5. **重开/重放不派发新请求** —— 状态侧证据（重启后 attempts 数、`attempt_ids`、预约保持）成立；
   「以原命令重放时新增派发 = 0」的观测函数与三态记录器已实现并接入驱动
   （[观测](replay-no-dispatch-observation.md)、[接线](replay-observation-wiring.md)），
   但真实运行要拿到 `observed` 仍需可用前快照，即仍依赖第 4 项。
6. **准确 head 的 CI 与关闭判定** —— 本会话未取得 CI 结论：本机无 `gh` CLI、无
   `GH_TOKEN`/`GITHUB_TOKEN`，未认证访问 GitHub API 返回 403 rate limit，且未读取
   Windows Credential Manager 中的 Git 凭据（不回显任何凭据）。仓库现有三个工作流，
   需由值守/协调者按准确 head 确认全部绿：
   - `.github/workflows/ci.yml`「frontend and historical checks」（jobs：
     `offline-checks`、`console-browser`；push 与 pull_request 触发）
   - `.github/workflows/tests.yml`「mechanism-tests」（job：`unittest`）
   - `.github/workflows/model-service.yml`「fixed model service」（job：`model-service`）
   最近一次有记录的 CI 全绿是 PR44 受审 head `744b456`（14/14）。
7. **独立非实施角色对最近增量的复核** —— 已覆盖部分见上；最近几个增量是否已满足
   当前卡的复核要求，由值守判定。

## 解除真实出口所需（属用户侧授权，不在本会话执行）

需要为用户确认的**合法 profile/account/模型**、**有限调用次数**与**输出上限**授权，
且明确允许“看到真实输出后取消”的有界试验；缺此授权时不得派发真实请求，本卡也不应
以受控结论替代真实验收。

## 结论

- 受控工程面：本轮在 `faa5a4c` 上本地自动化面全绿（306 Node / 812 Python），
  证据索引完整，可支持“受控部分完成”的陈述。
- 真实出口：**全部仍未完成**，卡 #40 与父 #22 不能关闭；DSH owner/progress/WIP 保持。
