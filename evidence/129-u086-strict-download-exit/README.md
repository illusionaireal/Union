# evidence/129 — 严格下载核验（回应值守对 evidence/128 假阳性的复核）

## 背景

值守复核（cfe0631）指出 evidence/128 的下载断言为假阳性：error body、null result、另一 result 都会被「非空且含 result 字符串」的旧断言接受。

## 修正（严格断言）

下载断言改为验证获取的 body **就是记录的那条结果**：

1. `body.result.id === 记录 result_id`（同一结果）；
2. `sha256(body.content)` === 记录的 sha256（同一内容字节）；
3. `body.result.title === 记录 title`。

results API 响应形状显式处理：`{protocol, organization_id, work_id, result:{…无 content}, content}`——元数据在 `body.result`，正文在 `body.content`。

## 结果

**14/14 checks，exit 0**（真实 modeld，deepseek-v4.1-flash，单次派发）：
- download link present（href 指向 results API）
- downloaded body is the recorded result (same id)
- downloaded content sha256 matches the recorded digest
- downloaded title is the recorded title
- 加上原 22-B 流程 10 项（登记/候选/digest/nonce/adopt/deliver/重启持久）。

## 备注

- evidence/128 的历史记录保留不改写（其弱断言与实际运行记录已被复核引用）；本证据为其修正版。
- 重启持久化断言沿用 22-B（adopted result survives rebuild）。
