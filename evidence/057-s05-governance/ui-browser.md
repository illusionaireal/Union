# S05 / U-069 实际浏览器记录

最终运行于 `2026-11-05T13:39:07.267Z` 结束（本地时间 2026-11-05 21:39），退出码 0：[50 项检查](ui-browser/checks.json)全部通过，覆盖 21 种治理命令。使用 Node 24.19.0、Chromium 156.0.8078.80、项目 `.venv` Python，以及真实 React、HTTP 和 SQLite。每次运行创建新的私有数据目录和三个独立浏览器账号上下文；结束关闭本次浏览器与服务。

这是受控工程验证。Playwright 代操作账号与本地文字提交入口，记录类型是 `local_submission`，没有 AI 业务执行器、模型派发或真实业务劳动取证。不能据此声称自主经营、持续运行、真实用户接受或全面无障碍认证。

| 已执行场景 | 实际观察 |
| --- | --- |
| 普通核心参与者登记与恢复 | 两个独立 core 账号起始无 AU/legacy/platform 权；恢复码保持到确认，账号显示可选取的稳定 principal；接班后恢复密码仍保留同一主体。 |
| 单主体本地治理 | 创建准备 AU、采用/启用/续期；一名明确责任主体完成 Work → Mandate → 尝试 → 文字提交 → 采用。 |
| 有效规则与范围 | 修章撤掉 record_memory 后，实际授权入口拒绝；恢复规则后继续。目标/章程修订、职责修改、工作调整和退出沿同一生产 HTTP 契约。 |
| 有限授权与局部撤销 | A → B → C 三级链；撤掉父授权后，新动作被拒，迟到内容保存为 evidence_only，未改变已采用成果；独立 Work 继续。 |
| 原责任交接 | 原 Work ID、未采用尝试和已完成历史保留；旧绑定失效，接收者经明确复核、重新获权后完成原 Work。 |
| 治理交接与失能恢复 | B 以本人账号确认接班；A 失去当前 AU 投影且不能修章，但仍能查询自己的原回执。预先确认后继者后，经过真实 60 秒期限，按既定程序恢复，再明确退出。 |
| 未知结果与重启 | 真实 POST 已保存后丢弃响应；查询暂不可用时原 ID 保留；浏览器刷新、服务重启后查询同一回执，没有新 POST 重放。浏览器存储只含请求元数据。 |
| 长名称、小屏与键盘 | AU/成员/不含换行点的 Work 名称均为合法 200 字符；1440/1024/390/320 无水平溢出。后台读取保留输入/焦点；Enter 预览、Escape 取消预检，无 POST，焦点返回触发按钮。 |
| 可读性 | 四宽度共 32 组、88 次实际计算样式测量通过；预览正文/标签/提示/展开控件 14px，标题 15.75px，状态文字 12.25px，最小对比度约 7.13:1。 |

共观察 45 次命令 POST：1 次 S01 V1 创建、42 次 UI 治理提交，以及 2 次直接 HTTP 授权反例检查。21 种治理命令各自都经过渲染表单、影响预览和生产命令入口。没有派发模型或 legacy 执行命令。

本轮构建与浏览器记录一致，完整 SHA-256 也在 checks.json 中：

| 产物 | SHA-256 |
| --- | --- |
| `index-CFPcT5Rn.js` | `f0454f38bbd09e8dd920e509556b7e10831c76c69f0e89ab4222539185a4d8ff` |
| `index-CVEbdme-.css` | `393612f4cbac24d77a0a56923006bafbc137999060c009f2703d79e1928415bd` |

当前截图是 `governance-{1440,1024,390,320}.png`、`responsibility-{1440,1024,390,320}.png`、`preview-320.png`；额外的 [预览上部](ui-browser/preview-320-dialog.png)和[确认按钮所在区域](ui-browser/preview-320-confirm.png)用于查看小屏滚动窗口的实际字号与可达操作。[readability.json](ui-browser/readability.json)保留所有计算样式和标准 sRGB 对比度结果。截图只含验收名称、principal 和请求/组织标识，没有密码、恢复码、cookie 或一次性登录凭据。

失败记录保留为历史，不以旧 checks.json 代替最终结果：

- `failure-initial-version-check.json`、`failure-collapsed-metadata.json`：命令回执和真实 GET 均为 v1，DOM textContent 也为 v1，但折叠 details 内的 innerText 为空。脚本改为先展开“数据与运行记录”，再断言可见版本。
- `readability-before-contrast.json`、`failure-preview-contrast.json` 和 `before-contrast-preview-320*.png`：真实浏览器 RED。修复只限 S05 预览与状态样式，最终原有判定门槛全部通过。
- `failure-refresh-timeout.json`、`failure-refresh-context.json`、`before-refresh-fix.cjs`：保留后来一次交接授权选项超时的原失败、时间、脚本字节和构建摘要；原失败当时尚未采集下拉选项详情。
- `failure-refresh-reproduced.json`：追加 600ms AU 读取延迟后复现。打开时页面为 v27，失败时页面和 GET 均为 v31；目标授权与绑定有效、Work 开放，冻结表单仍只有旧授权。原 helper 仅等待 session 响应和已有连接标记。最终 helper 等待新发起的 session/目标 AU GET 以及相应版本呈现；600ms 延迟继续保留，并在最终运行通过。产品保持草稿和焦点的行为没有为测试改变。

在已安装并构建的仓库根目录重现：

```powershell
$env:PATH = (Resolve-Path .union/tools).Path + ';' + $env:PATH
$env:UNION_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:UNION_S05_UI_EVIDENCE = Join-Path (Get-Location) 'evidence/057-s05-governance/ui-browser'
& .union/tools/node.exe scripts/s05-governance-browser.cjs
```

运行期间不要同时重建该工作区的 `web/console/dist`。实体设备、屏幕阅读器、真实用户研究、安装候选和持续业务运行分别需要自己的证据；安装候选与整片收口由协调者负责。本报告不改变任务主账或采用权限。
