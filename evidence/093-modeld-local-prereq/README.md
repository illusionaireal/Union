# 093：modeld 本机测试的前置条件（避免把 8 项失败误读为回归）

2026-11-08 08:50。在 U-067 的自动执行链核对中顺便跑了 modeld 自带测试，作为"我依赖的协议实现是否健康"的旁证。结论：**失败是环境前置缺失，不是产品回归**。

## 实测

```
bun test services/modeld/test
33 pass / 8 fail / 41 tests（约 2.6 秒）
```

失败集中在依赖原生内核与 vendor 的用例，错误为：

- `Cannot find package 'effect' from services/modeld/src/kernel.ts`
- `Cannot find module '../../vendor/opencode/packages/core/src/credential.ts' from services/modeld/test/fixtures/kernel-probe.ts`

即本 checkout 里 **vendor OpenCode 源码未展开、`effect` 依赖未安装**；需要先按 `services/modeld/prepare.mjs` 准备（CI 的 `model-service` 任务会做这一步）。

## 与 U-067 的关系

- 我的 `ModeldWorkTransport` 测试**不依赖**这些原生内核用例（用本地 HTTP 替身与源码契约核对），因此不受影响。
- 记录本文件的目的：任何人（含 CI 之外的本地验证）看到这 8 项失败时不要误判为本分支或集成分支引入的回归。

## 仍未验证

真实 modeld 进程与真实推理（需要宿主凭据与准备好的 vendor）。

## 补充（2026-11-08 13:01）：本机无法直接启动 modeld

尝试用仓库现有产物起一个本地实例以验证 `/v1/runtime` 协议，结论是不可行：

| 检查 | 结果 |
| --- | --- |
| `services/modeld/dist/` | 只有 `LICENSE.opencode`、`THIRD_PARTY_NOTICES.json`、`upstream.lock.json`，**没有可执行的 `main.js`** |
| `services/modeld/vendor/` | 仅 1 项，**上游 OpenCode 源码未展开** |
| `package.json` scripts | 只有 `test` 与 `build`（`build.ts`），没有 `start` |
| 本机工具链 | Bun 已安装（`~/.bun/bin/bun.exe`） |

因此要起真实 modeld，需要先：`prepare.mjs`（拉取并构建固定的上游内核，可能需要 Go 工具链与网络）→ 生成 `dist/main.js` → 提供宿主私有配置（回环 origin + admin/worker 令牌）与上游账号凭据。**后两项只能由宿主提供**，本卡不索取密钥正文。

结论：真实有界验收（≤2 次调用、≤1024 输出 tokens、仅合成资料）仍阻塞在宿主的 modeld 构建产物与凭据上，而不是本卡代码。
