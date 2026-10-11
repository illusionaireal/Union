# 网站验证证据

- `browser-validation.json`：实际 Chromium 浏览器的 37 项交互与响应式检查，含 Cloudflare CSP，全部通过。
- `desktop.png`、`mobile.png`：桌面与手机完整页面截图。
- `demo.png`：跨成员资料依赖演示截图。
- `deployment-check.json`：网络与凭据检查、实际 Wrangler 部署失败、已保存环境配置草稿的状态；未上线。
- `mechanism-regression.log`：网站改动后重新执行原 25 项机制测试的结果。
- `offline-validation.json`：直接 file 导航被云浏览器管理策略阻止，标为 blocked，不属于通过的浏览器检查。
- `single-file-validation.json`：单 HTML 在断网 Chromium 文档中的 43 项检查通过，交互与实际下载无网络请求；加载方式为 setContent，未宣称 file 导航通过。
- `single-file-desktop.png`、`single-file-mobile.png`、`single-file-demo.png`：单文件交付的桌面、手机和协作演示截图。

浏览器只重放公开 fixture。真实模型调用仍为 0，网站演示不构成真实组织、经营交付或市场反馈证据。
