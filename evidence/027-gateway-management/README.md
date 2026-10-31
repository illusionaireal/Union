# 027：New API 接入与观察（2026-10-30）

外部工程代理在 dev 上完成第一批代码；不是 AU 自主交付，也未启动真实公司。本批 U-037 仍为 blocked，等待实际浏览器验收，不因工程测试通过关闭。

## 已实现

- 平台网关登记/编辑/解除及持久幂等回执；宿主显式 platform_admin 权限，不由普通 board/observer/受限会话推导。
- 显式健康检测、实际接口版本/检测时间、部署 unknown；无凭据、无重定向、64KiB上限、4秒总时限及检测准入。普通刷新零模型调用。
- React 平台管理入口、后台链接、复制地址；AU 模型页选择最小公开目录、私有令牌及版本来源快照；登记变化不迁移原连接。现有工具往返测试复用。
- 无部署控制器时不显示启停/升级等按钮；external/managed 目前只是登记模式。

## 已通过的受控验证

- `.venv/bin/python -m unittest discover -v`：200 项，66.983秒，全部通过。含10项新网关行为测试；真实回环 HTTP 状态协议、总期限、权限、旧响应隔离、重启幂等、地址快照与密钥迁移均有覆盖。
- `npm run check`：完整退出0；管理8项、历史计划完整性、动作安全9项、TypeScript、前端20项、Vite正式构建通过。
- [独立权限复核](../../docs/reviews/2026-10-30-gateway-management.md)：通过；初审慢速响应问题已修复，独立实测总期限4.01秒、每实例互斥、全局8作业及最小AU投影。
- `git diff --check` 通过。API/状态响应协议依据官方接口文档；未据此推定真实 New API 已兼容验收。

## 未通过/未执行

实际浏览器验收未执行成功：环境无 Chromium，官方 Playwright 安装器下载的压缩包不完整（ZIP central directory 不存在）。未尝试绕过网络策略；未生成或伪造页面截图。安装及执行失败留存 [浏览器环境记录](browser-setup.txt)。

可在提供可用浏览器的环境重跑：

```sh
npm run build:console
UNION_PYTHON=.venv/bin/python UNION_CHROMIUM_PATH=/path/to/chromium npm run test:gateways
```

脚本使用独立临时服务和明确本地状态/模型替身，验证登记、检测、编辑、AU连接、两次工具往返成功回执、解除后保留连接、普通board拒绝管理、桌面及390/320px布局。脚本本身通过 Node/Python语法检查；浏览器步骤仍待真正执行和截图审阅。

真实 New API/上游调用数为0、真实费用未知且未发生本轮模型支出；没有商业订阅、OAuth、真实模型、Docker部署或持久服务器验收。U-039独立保留；第二批 U-038托管控制尚未实现，不是仅缺凭据即可用的按钮。
