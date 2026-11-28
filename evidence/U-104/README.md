# U-104 / #58 无私有平台的 Core 受控验收

在固定集成树 `d829a9d6b65236e93bda111459d1e96725f05a39` 上，
复用标准库客户端和 Core 子进程。该子进程使用独立临时用户目录和最小环境。
初始化账号和负责 AU 的登记账号都没有平台管理员权限；独立客户端以普通核心账号
创建、读取同一 AU 并完成一次受控 `start_work`。模型授权由回环替身提供，
记录仅含 grant GET，实际推理为 0。

本次分别观察到公开协议 `core.au.v1` 和 `core.work.v1`、配置后 AU schema 3、
每条命令的持久状态版本以及 Agent Definition v1。陈旧状态版本有原拒绝回执，
有效登记仅增加一次 AU 版本。客户端丢弃有效 POST 正文后只用 GET 找回原回执，
重启并重新登录后仍能读回原主体、AU、Work、责任及回执。另一个普通核心账号
对这组 AU、Work 和回执的读取均得到 403。工作处于 pending，执行、步骤和成果为空。

复查 U-103 所审基线以来 scripts、ops、web 和 modeld 的源码变动。新增业务界面经
Core 公开 HTTP，浏览器脚本属于受控验收。发布脚本的新增 AU 库读取为只读兼容预检，
旧开发调度访问自己的 runs/calls 库。当前仓库范围未发现新增外部业务写入私有 AU 表的调用者。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m unittest tests.test_public_core_client -v
```

[冻结验收合同](contract.md)与[验证记录](validation.json)绑定入口、独立环境和输入。
交付为受控候选，准确提交的 CI 与独立权限复核用于采用。发布安装和持续使用归 #27。
