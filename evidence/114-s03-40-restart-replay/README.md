# 114：#40 重启后同 id 重放与派发计数（**已于 2026-11-09 00:20 真实执行**）

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

## 真实执行结果（2026-11-09 00:20，用户已无限授权 deepseek-v4.1-flash）

```
RESTART40:
 request_id = work-0ce6ae0b3ff37006ae2a25a02353d8f0013246496079167adcad7b18c992b4f9
 cancel_reply = {"state":"streaming","cancel_requested":true}
 final = {"state":"interrupted","au_id":"org-2094731a55384522bc992bae923d5241","cancel_requested":true}
 before_restart = {"steps":1,"budget":{"max_calls":1,"reserved":1,"used":0},"model_request_id":work-0ce6…}
 after_replay   = {"steps":1,"steps_status":["unknown"],"budget":{"max_calls":1,"reserved":1,"used":0},
                   "model_request_id":work-0ce6…}      ← 与重启前完全相同
 first_receipt  = {"status":"succeeded","model_outcome":"unknown",
                   "message":"…work_step_interrupted","step":"work-40#s1"}
 replay_receipt = 同上（重放返回同一原请求回执）
```

**证明**：
1. 重启后**原样重发同一 command payload**成功（没有被 `id_conflict` 拒绝，说明 payload 一致）；
2. **没有新增步进、没有新增派发**：`steps` 仍为 1、状态仍 `unknown`、`model_request_id` 与重启前一致；
3. 预约仍被占用（`reserved=1, used=0`），符合"未确认原请求时不得释放/记账"的语义；
4. modeld 侧 `au_id` 与产品 AU 一致（`org-2094731a…`），中断状态为 `interrupted`。

## 仍未覆盖（保持诚实）

- **真实输出事件流**（SSE 内容）未采集：本轮只观察到 `streaming` 状态；
- **远端取消确认**未获得：`cancel_requested=true` 是 modeld 的受理标记，不等于供应商侧已停止；
- **页面级 22-B** 仍需 PR34 合并后从核心 tasks 页完成，脚本 HTTP 取证不替代 #39。
