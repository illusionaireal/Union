# U-102 / #56 独立 HTTP 客户端登记工作

2026-11-28 在集成提交 `c8ab77d51796ee3e962f9cb4c09c775af0d4e428` 上复验 11 月 16 日的候选。负责账号为 `codex-home-coordinator`，在线成员 ID 为 `89f4c1c1-329a-4b54-ad37-235cf061e9a8`。原候选实施会话为 `01a1e041-e19d-7732-b6d8-025ff9dc3252`，本轮续接与验证会话为 `01a220ea-bfdd-7b91-b63e-ccacc4333684`。

[冻结合同](contract.md)的 W01–W08 由[标准库 HTTP 客户端](../../tests/test_public_core_client.py)覆盖。公开入口为 `POST /api/v1/work/commands` 的 `start_work`、`GET /api/v1/work` 和 `GET /api/v1/governance/receipts`。临时 Core 在独立进程中运行，账号、AU、治理和模型连接均通过公开 HTTP 准备。合成模型服务只回答授权查询，测试要求所有探测请求均为 GET。

| 验收项 | 受控观察 |
| --- | --- |
| 合法登记 | 普通 Core 账号在自己的 AU 中提交一次，原 Work、负责成员、绑定、定义和 Mandate 可读，版本增加一次。Work 保持 pending。 |
| 权限与版本 | 跨 AU 的平台管理员读取、提交和重放均被拒绝。陈旧版本、停用连接和退出治理可查原拒绝回执，公开 Work 视图一致。 |
| 同一请求 | 同主体用新登录会话提交同 ID 同内容返回原回执。同 ID 改内容返回 `409 id_conflict`。 |
| 响应丢弃与重启 | 客户端丢弃单次 POST 的响应，只 GET 原 ID。Core 重启后正常登录，读回同一回执、责任与版本。 |
| 入口校验与审计 | 匿名、跨 Origin、非法类型和伪造主体请求不消耗 ID。合法回执关联命令、AU、主体与版本，受控秘密和宿主位置不进入公开响应。 |

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m unittest tests.test_public_core_client -v
```

本轮复用原候选的测试补丁，首次运行 14 项通过，其中 U-101 回归与 U-102 各 7 项。候选仅改测试与交付证据。受控测试使用合成账号和回环服务，实际产品推理调用为 0。验证输入、工具和结果见 [validation.json](validation.json)。采用须等待候选准确提交的 CI 和独立权限评审。父 #30 的完整公共契约以及 #58 的独立使用由各卡验收。
