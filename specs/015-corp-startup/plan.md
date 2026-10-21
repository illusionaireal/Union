# 实施计划

复用 Console 的创建回执、登记表和 Engine，不引入第二份公司状态或另一套组织机制。新增 `ai_union.corp` 作为公司配置、只读诊断及真实工作台入口；新增 `ai_union.service` 包装现有 API watch，将调用失败/暂停/精确到限转换为禁止自动重启的退出码。

先验证幂等创建、只读读取、供应商证据版本绑定及预算/unknown 行为，再运行完整工程检查和真实本机 HTTP 会话。systemd 模板只为运营者已配置的主机提供安装文件；本环境 PID 1 为 supervisord，未运行 systemd、无 Docker 和可用模型凭据，不伪造部署与模型执行。用户选择使用已有服务器，SSH 连接信息尚未提供。

当前 Cloudflare 连接可读取 Workers 资源，但 Containers API 实际返回 401，明确说明需要 Workers Paid；不升级套餐、不用静态 Worker 冒充 Python/SQLite 常驻服务。后续主机选定后使用同一代码与私有状态目录，不另起模拟公司。
