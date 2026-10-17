# 旧展示页与单 HTML 演示已退役

更新：2026-10-18（北京时间）。用户要求删除单 HTML 演示，将后续开发集中到 `dev` 上的正式 React 工作台。

已移除根目录的进展页、设计原型、旧单页工作台和 HTML 完成报告；其 `site/`、`design/dashboard/`、`design/console-legacy/` 源文件，以及专用生成、静态发布和浏览器验收脚本一并删除。正式 `web/console/` 工程、图标、Vite 构建和 Python 同源服务不受影响。小说业务的可选模拟场景属于正式工作台的测试入口，继续保留。

当前入口：首次 `npm ci --ignore-scripts`，然后 `npm start -- --open`。开发和架构见 [FRONTEND.md](FRONTEND.md)，安装及验证见 [DEVELOPMENT.md](DEVELOPMENT.md)。不再生成或分发独立 HTML 演示。

历史截图、验收记录、规格和原始附件保留在 `evidence/`、`specs/`、`docs/inputs/`；历史文件路径和命令只描述当时结果。需要查阅旧网页时使用 Git 历史，例如提交 `8179d6e`，而不是恢复第二套当前前端。
