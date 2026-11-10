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

按卡的验收原文，以下各项都要求**真实模型请求**与**真实远端事实**；本卡至今所有运行
均使用替身模型（真实推理 0），因此这些仍是开放出口：

1. **看到原请求真实输出后取消** —— 受控链已能读取“已保存的部分文本”并发起本地取消，
   但没有一次真实供应商响应被“看到后取消”。
2. **真实取消受理与远端事实** —— 只记录到本地取消请求与 modeld `interrupted`；
   远端是否已取消不可确认，必须保持 unknown，不能宣称已取消。
3. **真实用量/费用** —— 替身运行不产生真实 token/金额；真实账单与币种仍未知，
   不得折算成真实费用，也不得记为零。
4. **重开不派发新请求**（真实条件下） —— 受控链已验证原 ID 复核不重派发，但未在
   真实请求上验证；真实 `unknown` 预约的保留语义随之未验。
5. **准确 head 的 CI 与关闭判定** —— 本轮未取得 `faa5a4c` 的 CI 结论：本机无 `gh`
   CLI、无 `GH_TOKEN`/`GITHUB_TOKEN`，未认证访问 GitHub API 返回 403 rate limit，
   且未读取 Windows Credential Manager 中的 Git 凭据（不回显任何凭据）。仓库现有三个
   工作流，需由值守/协调者按准确 head 确认全部绿：
   - `.github/workflows/ci.yml`「frontend and historical checks」（jobs：
     `offline-checks`、`console-browser`；push 与 pull_request 触发）
   - `.github/workflows/tests.yml`「mechanism-tests」（job：`unittest`）
   - `.github/workflows/model-service.yml`「fixed model service」（job：`model-service`）
   最近一次有记录的 CI 全绿是 PR44 受审 head `744b456`（14/14）。
6. **独立非实施角色对最近增量的复核** —— 已覆盖部分见上；最近几个增量是否已满足
   当前卡的复核要求，由值守判定。

## 解除真实出口所需（属用户侧授权，不在本会话执行）

需要为用户确认的**合法 profile/account/模型**、**有限调用次数**与**输出上限**授权，
且明确允许“看到真实输出后取消”的有界试验；缺此授权时不得派发真实请求，本卡也不应
以受控结论替代真实验收。

## 结论

- 受控工程面：本轮在 `faa5a4c` 上本地自动化面全绿（306 Node / 812 Python），
  证据索引完整，可支持“受控部分完成”的陈述。
- 真实出口：**全部仍未完成**，卡 #40 与父 #22 不能关闭；DSH owner/progress/WIP 保持。
