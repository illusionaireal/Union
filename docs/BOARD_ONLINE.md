# 开发看板的在线版本（Cloudflare）

2026-11-04，用户要求把开发看板放到 Cloudflare 上，方便随时查看。本文件记录做法、边界和没做的事。

## 它是什么

`site/board/` 是**一份只读快照页面**：从 `management/project.json` 生成 `data.json` / `data.js`，浏览器不需要任何后端、不需要 React、不发起请求（`connect-src 'none'`），手机浏览器也能用。

```sh
node scripts/board-snapshot.mjs        # 生成 site/board/data.{json,js}
UNION_BOARD_DRY_RUN=1 scripts/deploy_board.sh   # 只生成，不发布
scripts/deploy_board.sh                # 生成 + 发布到 Cloudflare Pages
```

页面内容与本地 DSH 面板同源：七列状态、WIP 上限、里程碑、可开工队列、卡片验收条件 / 依赖 / 阻塞 / 证据，支持按编号标题筛选、按状态过滤。

## 发布边界（重要）

- **快照，不是实时**。线上看到的是生成那一刻的状态；要看新数据就重新运行一次发布。真正实时需要 Worker + KV（见下）。
- **没有登录**。Pages 免费站点谁拿到网址谁就能看；页面带 `noindex` 只挡搜索引擎，不是访问控制。需要限制就用 Cloudflare Access（Zero Trust）套在这个路由上。
- **发布内容仅限 `site/board/`**：不含证据附件、日志、仓库历史、`management/project.json` 之外的配置。`data.json` 里没有绝对路径、没有凭据。
- **凭据只走环境变量**（`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`），不写进仓库、不进命令行参数。参见 `docs/DEPLOYMENT_PRIVACY.md`。
- 项目名默认 `union-board`，已有账户里用途未核实的站点不会被覆盖或改名。
- 响应头在 `site/_headers`：`/board/*` 关闭外部连接、拒绝被 iframe 嵌入、`no-store`。

## 还没做（等你定）

如果「在哪里都能用」指的是**不用回来点发布**，下一步是把只读快照换成 Worker + KV：

1. 一个 Worker：`GET /api/board` 读 KV 里的最新快照，`PUT /api/board` 用 Bearer token 写；
2. 本地 `npm run board:snapshot` 之后顺手推一次 KV，不需要重新部署；
3. 页面改成同域 fetch，仍然保持只读渲染。

代价是多一个 KV 命名空间和一个推送令牌。若还想在手机上**改状态**（认领、记录验收），那是另一件事：主账在这台机器上，远程写入需要队列 + 冲突处理，不能靠页面直接写文件。
