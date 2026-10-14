# 实现方案

1. 保留 004 运行时接口；归档旧前端。建立 npm workspace、Vite、严格 TypeScript。
2. `src/api` 定义契约与超时请求；`src/app` 集中会话/组织读取与路由；`features` 管命令和详情；`pages` 保持显示职责。
3. Python 提供构建目录及七条 SPA 路由，静态资产独立 404。`npm start` 构建后转交 Python。
4. 类型检查、Vitest、Python、历史 Node、实际浏览器验收；新证据写入 005，不覆盖历史。
