# U-075 / S09.2：核心工作台直接配置 Responses

日期：2026-11-08（Asia/Shanghai）。在线卡 #28；基线 `1bbd7fc`（rewrite/charter-v1），分支 `codex/u075-profile-acceptance`。

## 已交付范围

- 页面可选择 OpenAI Responses API，输入自己的地址、密钥、模型和输出上限，预览明确协议；保存不推理、不改变默认，密钥提交后清除且不回填。
- 核心注册表拥有 `openai_responses → wire_api=responses`；复用既有单次 modeld 内核，没有新增 Agent 循环、自动回退或重试。原 Chat 注册请求不增加协议字段。
- modeld 注册回执按原 AU、主体、模型、profile 和协议核对；保存 unknown 仅查询原注册，错误协议不能采用；责任、两次调用、原生上下文、资料回执与未知费用沿用 S02。
- 发布清单从被打包源码的注册表提取 `core_model_profiles`，不受打包器已加载模块影响。旧候选遇到 Responses 连接或保存意图，在切换/回退/启动前拒绝，原代码指针和历史保留。
- Responses 的文本/工具/用量只标 controlled；页面流式展示和长作业追加输入继续标 unsupported。一种兼容 API 的真实证据不外推。

## 验证

严格 RED：核心不支持此 profile、页面没有选择项、modeld runtime 漏报，均先观察失败。发布器另发现清单误用运行中注册表，观察 RED 后改为从被打包源码提取键。

- `npm run check` 通过，含 20 个前端文件、198 项；模型模块最终 53 项通过。
- `bun test --timeout 30000 services/modeld/test`：89 项通过。包含固定 SDK Responses 的原生工具/加密上下文续传、用量和不重试回环。
- 核心受影响子集 46 项通过；最终 Responses/发布回归 24 项通过（包括额外的旧 Chat 请求不变测试）。
- 实际 Headless Chromium 141：69 项通过，含 Responses 保存/协议保留/密钥不回填；浏览器控制供应商总计 7 次请求，真实模型调用 0。Responses 保存本身没有推理；其工具循环与原生 SDK 分别在受控测试验证。
- 完整 Python discover：运行 612 项，1 error、1 skipped。唯一错误为未改动的 `tests/test_documents.py:76` 在 Linux 调用 Windows `cmd /c mklink /J`，缺少 cmd。已单独复现，相关源码与基线相同；未跳过或改写该测试来制造全绿。

原始结构化结果见 [validation.json](validation.json) 和 [browser-checks.json](browser-checks.json)。浏览器 DOM/交互已验，但环境缺少 CJK 字体，截图字形不能作为视觉验收。

复现使用 Node 24.22.1、Bun 1.4.2、项目固定 Python 依赖。浏览器：

```bash
UNION_BUN=/path/to/bun-1.4.2 UNION_PYTHON=/path/to/project-python \\
UNION_CHROMIUM_PATH=/path/to/headless_shell UNION_S02_UI_EVIDENCE=/tmp/u075-browser \\
node scripts/s02-models-browser.cjs
```

## 当前限制与下一步

本交付是工程候选，**U-075 未完成**，等待审阅及真实接入验收。需要指定合法 Responses 供应商连接、允许发送的测试资料，以及明确调用次数/输出上限/未知费用接受范围，再执行真实工具往返与一次中断后的原请求核对。当前没有此项资源授权，不发起真实调用。

实现的原本地提交为 `0766fe2d9439e13eaac93d4f1f77ee17cdf469b0`。此前上传被自动审批拒绝，
用户于 2026-11-08 明确允许当前开发阶段直接上传 GitHub 仓库，并要求上传前 fetch。
本次先 fetch `rewrite/charter-v1` 到 `f32d175285405baace15852cfdc65134deff3896`，合并其四个
S03 成果/下载/工作页提交；上传前再次 fetch 发现 `0dc9e98dec3bd3237a51fdae03ef96414605bb76` 的
成果表单并发提交，已一并合并并复验前端。共五个上游提交，无文本冲突，保留同行管理历史与未提交 vendor 构建补丁。
上传后的实际 GitHub SHA/链接以原卡的交付读回为准。授权上传不等于真实 Responses 验收已通过。

最终合并后复验：`npm run check` 通过（20 个前端文件、202 项测试、类型检查及构建）；
`.venv/bin/python -m unittest tests.test_core_responses_profile tests.test_core_model_release tests.test_core_work -v`
运行 26 项全部通过，覆盖 Responses、发布兼容与上游工作成果行为。虚拟环境的 Python 链接在会话恢复后缺失，
通过同版本 `python3 -m venv --upgrade .venv` 修复后执行；没有更改依赖锁定版本。
原完整 Python 运行的跨平台错误仍由独立 U-078 承接，本次未重跑整套或把历史结果改写为全绿。
当前需资源协助的真实验收已向 Kanban 团队留言板发起求助（留言 #2），原卡保留解除条件。

流式页面与长作业新输入尚未实现；不据此关闭整卡或承诺其他供应商。未部署、未迁移生产数据、未修改主线或他人认领。Kanban 是负责人/状态/依赖/WIP 的运行态来源，仓库只同步长期路线和本证据。
