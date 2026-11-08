# 111：22-B 真实出口（目标→正文资料→采用/下载→完成→重开）

2026-11-08 23:05–23:12。在集成 head `86f283a` 与真实 modeld（OpenCode Go · `deepseek-v4.1-flash`）上完成 **#22 的 22-B 项**：一次有界真实目标 → 读到资料**正文** → 候选成果 → 采用 → 下载 → 完成 → **重开验收**。

## 结果（`exit.log` 原文）

```
EXIT22B: {"loop": {"status": "succeeded", "message": "自动循环结束：已产出候选成果",
  "turns": 2, "tool_calls": 1, "result": true, "usage": {"input_tokens": 957, "output_tokens": 164}},
 "budget": {"max_calls": 3, "reserved": 0, "used": 2},
 "usage": {"input_tokens": 957, "output_tokens": 164},
 "reads": [{"sha256": "1f152757343b87c7a4b606ba74f1fab4c1e4bbd820867bf6f6b8f2f50916e8ac", "bytes": 108}],
 "document_sha256": "1f152757343b87c7a4b606ba74f1fab4c1e4bbd820867bf6f6b8f2f50916e8ac",
 "results": [{"id": "result-5beabf3183f7", "status": "candidate"}],
 "download": {"bytes": 119, "sha256_matches": false},
 "deliver": {"status": "succeeded", "message": "已按采用的成果把该工作记为完成"},
 "reopen": {"status": "delivered", "results": [{"id": "result-5beabf3183f7", "status": "adopted"}],
            "steps": ["used", "used"]}}
```

要点：
- **读到正文**：`read_document` 的 sha256 与合成资料摘要**完全相等**（`1f1527…`，108 字节）——不是只列目录；
- 两回合产出候选成果，`usage 957/164`，预算 3 中用了 2；
- 采用 → 下载（119 字节）→ 完成（`deliver_work` succeeded）；
- **重开**：关闭并重建 Console 后，工作仍为 `delivered`、成果仍 `adopted`、两步进仍 `used` —— 持久化与重开可用。

## 两个真实 RED（都是脚本自身问题，产品未改）

1. 第一次：`读取摘要必须等于合成资料摘要` 失败 —— `write_text` 在 Windows 把 `\n` 转成 `\r\n`，文件字节与摘要不符；改用 `write_bytes` 后一致；
2. 第二次：`deliver_work` 被拒 —— 执行尝试仍 `running`；先 `finish_attempt(delivered)` 再 `deliver_work` 即通过（与 UI"完成工作"按钮的前置条件一致）。

## 说明

- `download.sha256_matches: false` 是脚本里的**错误假设**：下载内容是**成果**（119 字节），不是资料正文；实际验证的是"下载可拿到非空成果正文"；
- 本脚本是一次性证据工具（`run_exit.py`），**不属于** PR32 驱动子范围，也没有修改任何 `ai_union/` 或 `tests/` 既有文件；
- 真实调用：本轮 4 次（两次失败重试 + 1 次通过 + 1 次重开复查不需要调用），均 `deepseek-v4.1-flash`、每次 ≤1024 tokens、仅合成资料。
