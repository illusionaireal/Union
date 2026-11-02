# 正式开发与 NAS 试运行网页文档

2026-11-02，用户明确要求推送 dev 并制作网页文档部署到 Cloudflare。范围为本轮工程交付与 NAS 有限试运行指南，不是运行中的管理台，不包含账号、模型或组织 API。

## 内容与实现

保留在现有 React 工作区：`web/console/src/documentation/Document.tsx`。正文包括 0–5 批次、固定网址登录、模型接入、NAS 更新与备份顺序、验收清单、已知限制和下一项 U-054。页面标明日期与构建时的源码提交；不把受控验证写成真实部署通过。

构建时使用 React 渲染，发布独立 HTML/CSS/JavaScript 资源；浏览器无 React 运行依赖、无 API 请求、无持久存储。交互限于目录定位、命令复制、临时勾选和打印。桌面侧栏与移动横向目录分别适配，打印可存 PDF。

```sh
npm ci --ignore-scripts
npm run build:documentation
```

输出位于被忽略的 `dist/documentation/`，含资源哈希、源码提交与部署包。既有工作台的构建和路由保持不变。

## Cloudflare 发布

使用已连接 Cloudflare 插件，经 Workers API 上传 `worker.bundle.mjs`。Worker 名称为 `union-trial-guide`，不覆盖账户中用途未核实的现有站点；不修改自定义域名或 NAS。发布仅包含已审阅的文档构建，不上传整个仓库、历史提交、证据附件或私有配置。

模块 Worker 仅允许固定资源的 GET/HEAD，其他方法返回 405，未知路径返回 404；没有资源绑定、上游代理或组织访问。CSP 禁止网络连接、表单、嵌框及外部脚本；页面不保存凭据，也不提供登录框。`noindex` 仅提示搜索引擎，不提供访问控制；该网页是公开可访问的脱敏文档。

当前部署链接与实际验证结果记入 `evidence/044-web-documentation/README.md`。工程文档发布不关闭 NAS、真实模型或长期运行验收任务。
