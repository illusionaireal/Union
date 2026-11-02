# 044：正式开发与 NAS 试运行网页文档

2026-11-02。用户授权推送 dev、制作网页文档并部署到 Cloudflare；由 Codex 外部工程代理执行，不计组织自主交付或 NAS 更新。

## 源码和范围

React 正文位于 `web/console/src/documentation/Document.tsx`，构建与固定资源 Worker 位于 `web/console/documentation/`。构建清单记录源码提交、工作区是否干净及资源 SHA256；部署使用干净提交构建。源码和部署范围见 `docs/WEB_DOCUMENTATION.md`。

页面含开发阶段、0–5 批次、登录与模型配置、NAS 备份更新步骤、验收清单、已知限制、部署隐私及下一任务。公开部署仅包含脱敏文档资源，无管理台、模型后端、仓库历史或私有附件。

## 受控验证

- `npm run check` 通过，含 37 项前端测试、类型检查、构建及管理/历史检查，见 `validation/npm-check.log`。
- 实际 Chromium 21 项通过，见 `browser/checks.json`。桌面 1440px、手机 320px 截图经目视检查；覆盖目录、复制、清单临时性、折叠、打印、横向表格、无脚本错误或非本地网络请求。
- 使用构建后的实际 Worker handler 提供 HTTP，验证 GET/HEAD、405、404、CSP；页面没有 local/sessionStorage 写入。
- 真实内网地址、SSH 登录串及 NAS 私有路径未进入发布 HTML。此检查只针对发布文档，不声称旧仓库和脚本已整体清除。
- 本机 Node 为 24.14.0，低于项目声明的 24.19.0；上述检查为实际本机结果，不作为 NAS 声明工具链验收。文档未更改 Python 运行时，沿用前一提交 5c230c4 交付前的 393 项 Python 回归（5 项平台跳过），不冒称本批新跑。

## 发布记录

待完成 Cloudflare 上传、workers.dev 启用及线上核对后追加具体结果。受控浏览器检查不代替公网访问验证。

## 结果边界

本批真实模型调用 0，未访问或修改 NAS。文档发布不会关闭真实账号、模型权限、成员工作区或持续运营验收。旧站点不覆盖，不改项目可见性、许可、自定义域名或付费套餐。
