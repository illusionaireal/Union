# S05 前端 strict TDD 与消费端边界记录

日期：2026-11-05。范围为 U-069/S05 的 React 用户路径；API 权限、规则、版本与持久化由生产后端持有。协调者管理主账、在线卡、Git 与整卡验收。

固定命令前缀：Windows PowerShell 中将项目 `.union/tools` 加入 PATH，用 `.union/tools/node.exe` 运行 `C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js`。Node 版本为项目固定 24.19.0。下述测试均使用 `run test --workspace @union/console -- <文件>`。

| 变更 | 观察到的 RED | 最小实现后的 GREEN |
| --- | --- | --- |
| 普通核心参与者登记与恢复码确认 | `src/pages/Identity.test.tsx`：8 通过、2 失败；找不到“登记核心参与者”。 | 10/10。正常注册、保持恢复码直到明确确认；失败与后台读取保持输入和焦点。 |
| 核心参与者自己的 V1 创建 | `src/features/commands/core-boundaries.test.tsx`：9 通过、1 失败；create_v1 被旧 board-only 判断禁用。 | 与身份测试合计 20/20；core 可创建自己的准备 AU，旧版操作仍禁用，稳定 principal 可选取。 |
| 当前治理读取取代不可变创建根判断 | `src/app/governance-workspace.test.tsx`：3 失败、2 通过；接班主体被拒，403 和新主体读取失败仍显示原 AU 投影。初次测试选择器错误先修正，再观察此真实 RED。 | 与既有 workspace、S01 创建/边界合计 26/26。按 schema 2 access 主体与服务校验；当前拒绝清除旧投影并保留当前登录。 |
| 21 类治理与责任操作的渲染流程 | `src/features/governance/Governance.test.tsx`：36/36 失败，均为缺少治理区域/对应操作入口。 | 36/36。首次运行 35 通过，撤权查询断言先于 React Query 通知；改为等待“旧投影消失”的条件后通过，未更改生产行为。 |
| 登记处理中退出、关闭 unknown 后同范围新 ID 重复请求 | 身份与治理合计 50 项中 2 失败：返回登录仍启用、重新打开同范围操作可进入新预览。 | 50/50。登记处理中保持表单；unknown 按 principal/AU/kind/非正文目标标识隔离，同工作仅查询原 ID。 |
| 恢复范围与生产契约补充 | 无关 Work 可继续、重启后同 principal 新服务实例可查原请求、evidence_only 拒绝刷新而不丢正文、存储失败不 POST 均作为现有保护回归。 | 全量前端 14 文件、121 项通过，保留原有 70 项行为。 |
| 明确能力拒绝与版本拒绝回执 | 两项定向 RED：HTTP unsupported_capability 被误归 unknown；服务端当前版本低于请求 base 时拒绝回执被丢弃。 | 44/44 治理测试通过。明确 HTTP 拒绝保持可编辑输入；历史回执匹配 id/kind/AU/base/principal，不由客户端推断服务器版本方向。当前后端 schema 1 的规则/版本拒绝是持久 HTTP 200 rejected，沿同一回执处理。 |
| 当前启用缺口 | 一项定向 RED：未显示 `readiness_gaps`，并把所有 unavailable 写成期限已到。 | 45/45 治理测试与类型/生产构建通过；直接展示服务端缺口，使用“治理当前不可用”。 |
| 独立评审后的提交恢复、当前读取、创建入口与注册竞态 | `ui-review-red.txt`：70 项中 7 失败。成功 POST 后带 `not_authenticated` 的二次会话检查会删除原 ID；明确会话失效仍显示旧 AU；治理后三页缺少新 AU 创建入口；注册/初次设置的身份轮询先于响应正文返回时恢复码丢失。P1 最初断言同时匹配页内与表单错误，先将选择器限于操作窗口，再观察到原 ID 实际变为 `[]` 的 RED。 | 逐项修复并通过定向检查：POST 接收阶段与结果核验阶段分开；会话失效清身份和投影；账号级创建入口不依赖当前治理命令；进行中表单固定其模式并保持到恢复码确认。 |
| HTTP 无 code 的认证拒绝 | `ui-http-auth-red.txt`：5 项中 1 失败，命令 POST 的无 code 401 被当成未知结果。 | 5/5。命令 POST 的有/无 code 401 为明确拒绝；已经收到 POST 回应后，会话 401（有/无 code）及 409 `incompatible_state` 均保留原 ID，仅查询原回执。普通 `/api/session` 的实际 401 可以无 code；早期带 code 的复现是客户端接缝证据。 |
| 有缓存的身份和服务边界 | `ui-cache-red.txt`：10 项中 3 失败；包括 session 401 清理，以及观察到新主体/服务后返回原 AU 缓存时恢复旧投影。使用实际保留缓存的 `gcTime: 60000`，同主体回访及普通断网控制均通过。 | 14/14 workspace 定向检查。身份只由真实 session 读取更新，AU 缓存不能反向恢复身份；取消的读取不能更新身份。既有过期登录测试将普通 Error 文本改为真实 HTTP 客户端的 `ApiError(status=401)`，原登录页面断言保留。 |
| 相同主体撤掉 AU 范围、注册时新身份查询进入 loading | `ui-review-expansion-red.txt`：2/2 失败；同一主体失去原 AU 范围后旧缓存仍出现，新身份的 auth 查询尚无数据时注册表单被卸载。 | 29/29 workspace + Identity；缓存投影还须在最新 session 范围内，pending/completed 表单先于 auth 查询 loading/error 分支保留。 |
| 关键治理说明与状态可读性 | 真实 Chromium `ui-browser/readability-before-contrast.json` 共 32 组、88 次计算样式测量，其中 80 次未达字号或对比度门槛；正文 11px/2.8608:1，确认提示 11px/4.4893:1，标签 4.4347:1，小屏状态 9px/4.1791:1。修改前截图和失败记录保留。 | `ui-browser/readability.json` 同样 88 次全部通过；预览正文/标签/提示/展开控件 14px、标题 15.75px、治理/责任状态 12.25px；最小对比度约 7.13:1。仅在 governance.css 局部覆盖，未改共用 legacy 样式；未编写 CSS 字面量镜像测试。 |

2026-11-05 前端全量组件检查为 **14 文件、141 项通过**，输出为 `ui-final-tests.txt`。可读性修复后协调者又完成完整 `npm run check`，同为 141 项前端检查，日志为 `npm-check-final.txt`；最终 TypeScript/Vite 产物为 `index-CFPcT5Rn.js`、`index-CVEbdme-.css`。独立评审另有 15 项反例及控制通过；整卡检查与采用结论由协调者记录。

当前身份与历史回执是不同读取：schema 1 仍保留 S01 准备态形状；schema 2 采用 `access.principal_id/service_instance/commands`，不在浏览器计算治理授权。当前主体失去 AU 访问时清除旧投影，原发行人仍可通过全局“我的治理请求”查询自己的请求。

治理表单的预览、POST 前预检、返回回执绑定原 principal、服务实例和 AU；同主体续期保留草稿。预检取消会阻止 POST；错误或不匹配回执不会升级为成功。只向 sessionStorage 写原请求元数据及非正文目标标识，不写密码、配置正文或内部提交内容。unknown 不自动查询写入、不自动重发；显式查询仍重新核对当前身份。

真实浏览器另由 `scripts/s05-governance-browser.cjs` 复用既有可重启私有浏览器 host，使用新的 `.union` 临时数据目录。合法 200 字符 AU/成员名称和不含换行点的工作名称通过真实表单录入；检查 1440/1024/390/320 宽度、后台读取时草稿/焦点、取消预检时不 POST 及焦点返回。结果、设备宽度和键盘检查以 `ui-browser/checks.json` 及页面截图为准；测试与构建通过不代替这些运行证据，不声称 AI 自主业务或真实用户研究通过。

最终实际浏览器结果时间为 `2026-11-05T13:39:07.267Z`：**50 项检查、21 种命令通过，0 次模型派发**。构建 SHA-256、32 组样式测量与原始截图均已保存。两处验收脚本问题及其实际诊断另见 [浏览器记录](ui-browser.md)：折叠元数据的 `innerText` 为空，以及只等待 session 响应导致在 AU 读取完成前打开冻结表单。最终脚本等待新发起的目标 AU GET 及该版本呈现，并保留 600ms 慢读取作为回归条件；没有更改产品的草稿保护语义。

[最终独立评审](review-ui.md)已核对上述新结果、截图与源/产物 hash，六项发现均关闭；在声明的 S05 本地受控范围内通过前端复核。安装、任务状态与采用仍由协调者单独收口。
