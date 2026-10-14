# ADR-0003 · 正式工作台采用 React + TypeScript + Vite

日期：2026-10-14。状态：按用户明确要求实施。

原 `web/console/app.js` 集中了七页、轮询、表单、命令与详情，生成单 HTML。用户要求完整前端工程，同时继续复用 Python 运行时、SQLite、本机会话和命令接口。

选择 React、严格 TypeScript 与 Vite；React Router 管页面及 URL 状态，TanStack Query 管读取与缓存。页面、API、公共组件、操作与详情分别维护。命令不重试，不排队到恢复联网后执行；结果不确定时查询原回执。

构建产物由 Python 同源提供，`npm start` 构建后启动后端。开发模式采用 Vite 持续构建并手动重新加载，避免引入第二个来源和代理身份变更。代价是没有开发 HMR；后续若引入同源开发中间件，需要独立验证当前来源、Cookie 和 CSP 规则。

单 HTML 保留为演示/报告及历史交付，正式产品使用工程化源码和生产构建。验证覆盖类型、关键交互、实际 HTTP/Chromium、静态边界和启动入口；这些验证不等于真实组织或外部部署验收。
