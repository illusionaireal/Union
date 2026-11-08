# 114：#40 重启后同 id 重放与派发计数（脚本已备，未执行）

2026-11-09 00:10–00:20。按 #99 对 #40 的要求，准备了**一次授权后即可执行**的真实取证脚本；本轮**未执行**（零真实调用）。

## 它要证明什么（对应 #99 的缺口）

1. **重启后核对/重放同一命令**：先制造一次真实中断（`streaming` 时 cancel），得到 `unknown` 步进；
2. 关闭并重建 Console（同根目录）；
3. **原样重发首轮 command payload**（同 id / 同 base_version / 同 data）——库层要求原样重发，否则 `id_conflict`；
4. 断言重放**不产生新步进、不产生新派发**：`steps` 数量保持 1、`steps` 状态仍 `unknown`、`budget.reserved` 仍 1、`model_request_id` 与重启前**完全相同**；
5. 同时记录 modeld 侧的 `au_id` 身份与最终状态，便于区分"取消受理 / modeld 中断 / 远端取消"。

## 运行方式（需明确授权）

```powershell
$env:UNION_MODELD_CONFIG = <宿主私有 modeld 配置>
$env:UNION_REAL_ACCOUNT  = <显式账号>
$env:UNION_REAL_MODEL    = deepseek-v4.1-flash
$env:UNION_REAL_RESTART_ACCEPTANCE = "1"   # 显式开关；不设则 skip
.\.venv\Scripts\python.exe -m unittest tests.test_40_restart_replay -v
```

（把 `run_restart_replay.py` 放进 `tests/` 后再执行；本轮未执行任何真实调用。）

## 仍未覆盖（如实）

- **页面级 22-B** 仍需 PR34 合并后从核心 tasks 页完成（脚本 HTTP 取证不替代）；
- 真实**输出事件**流（SSE 内容）与供应商侧"远端取消确认"仍无法在本机取得，只能陈述未确认。
