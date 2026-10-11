# 产品设计与高保真原型证据

此目录只记录产品设计原型验证，不是实际运行 Dashboard 或真实 Agent 能力验收。

- `browser-validation.json`：断网 Chromium 文档中运行单 HTML 原型的 48 项检查通过，包含七视图入口、筛选、详情关联、成果实际下载及不可用状态、异常状态、同版本模拟更新、旧模拟响应拒绝、键盘及四种宽度。
- `console-validation.json`：32 项操作交互检查通过，覆盖创建、预览取消、有限 fixture 步骤、费用确认流程、暂停在途、事件来源、资源保留用量、修章撤权、核对不退款、重复提交、角色变化、版本冲突及断开阻止提交。这是浏览器内设计检查，不证明服务端鉴权、持久化或作业控制已实现。
- `overview-desktop.png`、`overview-mobile.png`：桌面与手机总览。
- `disconnected-desktop.png`：断开及快照过期情景。
- `task-mobile.png`：手机任务详情。
- `operation-1440.png`、`operation-390.png`：桌面与手机的资源调整表单及预览。

加载方式为 setContent，网络请求数 0；当前受管理浏览器禁止直接 file 导航，不宣称 file 打开已验证。所有情景均为设计模拟，真实模型调用 0。

复现：

```bash
python3 scripts/build_dashboard_prototype.py
UNION_PLAYWRIGHT_MODULE=/tmp/union-site-tools/node_modules/playwright-core \
  node scripts/check_dashboard_design.cjs
UNION_PLAYWRIGHT_MODULE=/tmp/union-site-tools/node_modules/playwright-core \
  node scripts/check_console_design.cjs
```

原型公开成果在生成时复核 SHA-256；不会读取组织数据库、凭据或私有执行日志。生产观察与操作服务尚待按 A01–A10、C01–C09 单独实现和验收。原型表单只演示固定受支持字段，章程完整字段编辑、真实超时后的回执查询和持久审计仍属实际前端开发工作。
