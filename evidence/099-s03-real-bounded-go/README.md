# 099：一次真实有界验收（OpenCode Go · deepseek-v4.1-flash）

2026-11-08 15:4x。**这是 S03/U-067 的最后一项出口**：真实目标 → 授权资料 → 模型 → 候选成果，全部在已授权额度内（≤2 次调用、每次 ≤1024 输出 tokens、仅合成资料）。

## 环境

| 项 | 值 |
| --- | --- |
| 模型服务 | 仓库发布产物 `services/modeld/dist/main.js`，用 Bun 1.4.2 运行，回环 `127.0.0.1:63504`，`protocol_version: 1` |
| 凭据 | OpenCode Go 设备授权（`state: connected`，账号 `cred_1b9cf8bf…`）；配置为宿主私有 `modeld.json`，未写入仓库 |
| 模型 | `deepseek-v4.1-flash`（该账号可用模型列表中包含 deepseek-v4-flash/pro 两项） |
| 业务侧 | 临时 Console 根目录（测试夹具），**未触碰**此前的 `UnionOps\real-go-acceptance` 业务库 |
| 资料 | 合成 Markdown（"不含任何真实业务数据"），经宿主登记的只读根 |

## 结果（原样来自 `acceptance.txt`）

```
real acceptance: {
  "model": "deepseek-v4.1-flash",
  "receipt": {"status": "succeeded", "message": "自动循环结束：已产出候选成果",
              "turns": 1, "tool_calls": 1, "result": true,
              "usage": {"input_tokens": 396, "output_tokens": 29}, "cost_status": "unknown"},
  "budget": {"max_calls": 2, "reserved": 0, "used": 1},
  "usage": {"input_tokens": 396, "output_tokens": 29},
  "cost_status": "unknown",
  "tool_calls": [{"tool": "list_documents", "sha256": null, "bytes": null}],
  "results": [{"id": "result-7e8c6e189a14", "status": "candidate"}]
}
```

- **调用次数 1（上限 2）**，输出 29 tokens（上限 1024），输入 396 tokens。
- 模型调用**授权工具** `list_documents`，产品记录工具回执；随后产出一份 `candidate` 成果等待采用。
- **费用仍为 unknown**（没有单价/汇率，不估算）。

## 过程中修掉的验收夹具缺陷（均为测试代码，不改产品）

1. 共享夹具会把 `ModelServiceClient` 全局替换成假 double → 真跑时必须 `stop()` 该补丁，否则 grant 校验会拿假数据（回读 `grant-a`/`model-a`）。
2. 连接保存后 revision 仍为 1（启用默认不产生新 revision），`start_work` 的 `expected_revision` 必须读取真实连接版本，而不是假设 +1。
3. 章程修订（授权读工具）要在保存连接**之后**做，避免 `check_operation` 的版本快照失效（`authorization_changed`）。

## 边界与诚实说明

- 真实调用 **1 次**，全部在授权额度内；未做第二次调用（模型首轮即产出候选成果，无需追加）。
- 未部署、未修改业务库、未改动他人工作区。
- 真实用量与费用未知项已如实记录：`cost_status: unknown`。
- 本卡其它 checklist 项（派发前持久化预约、工具正文传入下一轮、撤权后保留用量 PR #20）仍未完成，因此 #22 不能标 done。
