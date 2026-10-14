# 开发进展展示网站

本轮新增中文静态网站：`site/`。展示开发进展、可播放/暂停/逐步/重置的协作演示、三份可读取和下载的模拟成果、可点击的六模块架构图及验证摘要。兼容手机与桌面，无前端构建或运行时依赖，不加载外部字体、分析服务或 CDN。

## 单 HTML 交付

用户随后要求改为单 HTML，交付文件为仓库根目录 `ai-union-progress.html`（63,107 字节）。样式、脚本、图标、验证快照及三份成果全部内置；成果和验证摘要通过内置文本生成下载链接，运行时不读取其他文件。仅需分发此文件，`site/` 是编辑源文件。

```bash
python3 scripts/build_site_data.py
python3 scripts/build_single_html.py
```

生成器只读取公开网站文件，为内置样式和脚本计算 CSP 哈希，并拒绝残留外部文件引用。单文件自带 CSP；若单独托管它，应避免同时套用 `site/_headers` 中仅允许同源外部脚本的旧策略。

已通过 43 项 Chromium 检查：在断网浏览器中用 `setContent` 加载该文件的完整内容，验证演示、架构、三个成果和验证摘要的实际下载、键盘及四种屏幕宽度，网络请求数为 0。当前受管理的云浏览器仍禁止 `file://` 导航，因此直接文件打开未在此环境验证。原 25 项机制测试也通过。

```bash
UNION_SITE_SINGLE_FILE=ai-union-progress.html \
  UNION_PLAYWRIGHT_MODULE=/tmp/union-site-tools/node_modules/playwright-core \
  node scripts/check_site.cjs
```

结果与截图：`evidence/site/single-file-validation.json`、`single-file-desktop.png`、`single-file-mobile.png`、`single-file-demo.png`。

## 内容与数据

这是工程验证快照，**不是实时组织后台**。浏览器演示不会修改 SQLite、不启动 Codex、不进行真实发布。

`python3 scripts/build_site_data.py` 从既有的机制验证报告和明确标为模拟的成果导出白名单数据。只导出固定三份公开 fixture 文件并复核 SHA-256；不读取本地数据库、董事会凭据、认证配置或私有执行日志。机制验证仍为 25 项通过、2 名模拟成员、3 份成果、真实模型调用 0 次。

公开数据：`site/data/progress.json`。页面从同源脚本读取相同数据，不需要后端 API；数据更新时间来自原机制验证记录。新验证改变场景或实际调用来源时，应更新导出器与演示，不直接沿用旧结论。

## 本地查看

从仓库根目录运行：

```bash
python3 scripts/build_site_data.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

如需 ZIP，可从仓库根目录执行 `python3 -m zipfile -c /tmp/ai-union-progress-site.zip site` 重新生成，解压后通过任意静态 HTTP 服务器查看。Git 不保存旧环境的临时 ZIP。该网站只需要静态文件；不用安装 ai-union 运行时应用或模型执行器。Cloudflare Pages 和其他静态托管都能承载它。当前云浏览器的管理策略禁止 `file://` 导航，直接文件打开未验证；不要将它报告为已通过的离线检查。

## 验证

真实 Chromium 浏览器执行 37 项交互检查：阶段跳转、依赖状态、播放暂停、重置、后续任务、成果切换和下载、Escape 关闭窗口、六架构模块、键盘操作、公开数据及 1440/800/390/320 像素宽度。测试应用与 Cloudflare `_headers` 相同的 CSP，未出现 JavaScript/CSP 错误或资源加载失败。

工具：playwright-core 1.64.0，系统 Chromium。完整的新环境安装步骤见 [开发说明](DEVELOPMENT.md)；下方 `/tmp/union-site-tools` 是旧验证目录，可通过 `UNION_PLAYWRIGHT_MODULE` 替换。工具不是网站依赖。

```bash
UNION_PLAYWRIGHT_MODULE=/tmp/union-site-tools/node_modules/playwright-core \
  node scripts/check_site.cjs
```

实际记录及截图：`evidence/site/`。机制测试 `python3 -m unittest discover -v` 另行保留，不能把浏览器检查数量算作组织能力测试。

## Cloudflare 发布状态

用户明确请求建立网站并使用 Cloudflare，本轮已完成可发布内容和部署准备；**尚未上线，没有实际公开网址**。

检查到的条件：

- 本会话没有可调用的 Sites 或 Cloudflare 插件接口。
- 当前云配置没有 Cloudflare 认证绑定；相关进程变量未设置，标准 Wrangler 认证目录不存在。
- 对 `api.cloudflare.com` 的只读请求被网络代理以 CONNECT 403 拒绝。
- 已安装并核对 Wrangler 4.149.0 的 Pages deploy/project create 接口；非交互部署命令明确要求 `CLOUDFLARE_API_TOKEN`，没有创建或修改任何远端项目。
- 环境配置草稿已保存：`CLOUDFLARE_API_TOKEN` 的凭据要求、`CLOUDFLARE_ACCOUNT_ID` 的非秘密配置要求，以及 `api.cloudflare.com`、`*.pages.dev` 网络域名。凭据值未保存，也没有在聊天中索取。

工具返回 `requires_publish=true`：用户需要在环境设置填入凭据和账户 ID，审核保存配置并发布云环境版本。这一步启用环境条件，**不等于网站上线**；完成后重新验证网络与凭据，再继续实际部署。

建议 Cloudflare API token 只授予目标账户的 **Account → Cloudflare Pages → Edit** 权限，使用账户 ID 指定目标，无需全局 API key。Token 通过环境安全设置提供，勿写入仓库、脚本或聊天。

条件齐备后，运行已准备的命令：

```bash
CI=true UNION_WRANGLER_COMMAND=/tmp/union-site-tools/node_modules/.bin/wrangler \
  bash scripts/deploy_site.sh
```

脚本先创建独立 Pages 项目 `ai-union-progress` 再上传 `site/`。若名称已存在会停止，以保护既有网站；用 `UNION_CF_PROJECT` 指定一个新名称再试。不要直接部署到未知既有项目。脚本没有真实凭据时立即退出；其凭据检查与 shell 语法已验证，成功部署尚未验证。

另一种方式：用户在 Cloudflare 控制台选择 Workers & Pages → Create application → Pages → Direct Upload，上传交付 ZIP 中的静态文件。无需 Git 推送，也无需在此环境提供 API token；仍需用户使用有权限的账户完成操作。

只有 Cloudflare 返回实际部署网址且浏览器验证成功后，才能报告已上线；此处不预造 `pages.dev` 地址。
