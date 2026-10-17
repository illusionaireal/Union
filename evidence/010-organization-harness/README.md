# 010 验证记录

2026-10-17。真实 Deep Agents / LangGraph SDK + 本地 HTTP 模型替身；真实供应商调用 **0**。

## 通过范围

- Python 全量 131 项，包含 21 项 Harness 行为测试：分批筹建、草案修正与删除、独立进程 CLI 恢复、虚拟文件循环与两成员成果依赖、工具往返测试、逐次额度、暂停、unknown 不重派、修章后会话更新及原子成立。
- `npm run check`：历史计划/9 项动作测试、16 项前端测试、类型检查与构建通过。
- 工作台实际浏览器 71 项通过，包含草案展示与刷新恢复、390px 布局、正式成立、六次 SDK 调用对应六条用量记录、两成员实际文本成果及原有模型管理回归。
- 小说业务实际浏览器 16 项通过，同书三章、三轮 mock 经营及负面反馈后的实际任务与正文溯源。两次连接探测加十一轮业务调用共十三条记录。
- 一条命令启动 5 项通过；依赖锁校验通过。首次创建虚拟环境及安装另有独立检查结果。
- 独立工程角色复核发现的凭据过滤、已取得用量保留及修正结算出口问题均已修补和复验，见 [review](../../docs/reviews/2026-10-17-organization-harness.md)。

## 复现

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-harness.lock -e .
.venv/bin/python -m unittest discover -v
npm run check
.venv/bin/python scripts/check_console_start.py
UNION_PYTHON=.venv/bin/python UNION_CHROMIUM_PATH=/path/to/chromium npm run test:workspace
UNION_PYTHON=.venv/bin/python UNION_CHROMIUM_PATH=/path/to/chromium npm run test:novel
```

Windows 使用 `.venv\Scripts\python.exe`，环境变量按终端设置。新环境需先 `npm ci --ignore-scripts` 并安装 Chromium。测试脚本默认结果目录位于被忽略的 `.union/`。

## 验证过程中的修正

初次浏览器验证缺 Chromium，安装后继续；后来会话环境重建使工具缓存不可用，将浏览器安装到项目忽略目录后复验。旧小说断言仍按一次探测计数，改为验证两次探测及十三条总记录。新增工作台检查曾在取到运行回执后过早读取最终成果，现按本次请求 ID 并等待实际两份交付。两次失败都保留在本地过程记录中，最终结果见新 JSON 报告。

## 限制

这些测试证明 SDK 接入、持久化和宿主约束；不证明真实供应商兼容性、模型自组织能力、小说质量、真实发布或盈利。自动摘要在本轮关闭，会话输入有容量上限；成员当前仍串行派发。完整当前行为见 [组织 Harness](../../docs/ORGANIZATION_HARNESS.md)。
