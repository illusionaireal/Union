# 参考：探针 harness 的 async 修正建议（供值守采用，未改其原文件）

## 问题（最小复现见 vm-async-swallow-repro.js）

两套复核探针（`strict-download-review-probes.py`、`final-interrupt-review-probes.py`）的 vm harness 以 `(async () => { ... })()` 包裹抽取块：

- Python 侧 `check=True` 期待进程退出码 0 并从 stdout 读 JSON；
- 块内 `check()` 抛出的 `'review assertion rejected'` 在 **async 上下文**变成 promise rejection；
- harness 的 `catch (error)` 挂在**同步** `vm.runInNewContext(...)` 返回值上，await 不到该 promise → rejection 无人处理（unhandledRejection）；
- Node 进程仍以 0 退出 → harness 把**断言失败**误报为 `accepted=true`。

最小复现：`node vm-async-swallow-repro.js` 输出 `completed without throw`（应为 rejected）。

## 修正建议（对两个 harness 的 JS VM 片段）

```js
(async () => {
  try {
    // 关键：await vm 调用返回的 promise，让块内 check() 抛出的
    // rejection 冒泡进本 catch，而不是变成 unhandledRejection。
    const value = await vm.runInNewContext(
      '(async () => {' + input.block + '\n})()', context, { timeout: 1000 });
    process.stdout.write(JSON.stringify({
      accepted: input.predicate ? value === true : true,
      checks: names.length,
    }));
  } catch (error) {
    if (error.message !== 'review assertion rejected') throw error;
    process.stdout.write(JSON.stringify({ accepted: false, checks: names.length }));
  }
})().catch(error => { process.stderr.write(error.name); process.exitCode = 2; });
```

要点：

1. `vm.runInNewContext` 的返回值是块 IIFE 的 promise，**必须 await**；
2. 外层 `.catch` 保持 `exitCode = 2` 的解析器错误语义不变；
3. `accepted=false` 路径只在块内同步抛出 `'review assertion rejected'` 时触发——现在它会真正到达；
4. 对 `final-interrupt-review-probes.py`（同样的 `(async () => { try { const value = await vm.runInNewContext(...) }` 结构）适用同一修正——其外层已 await，但需确认 `context` 内 `check` 抛出的 rejection 路径同样冒泡（同一原理）。

## 采用后预期

- `reopen_other_result`（strict-download）将正确返回 `accepted=false` → 11/11；
- `final-interrupt-review` 三项 ERROR 将恢复为真实 FAIL/PASS 语义（其中 `test_prior_step_output` 的 FAIL 是真合同项，等待 work-events 二选一决定）。

## 边界

本文件仅为参考建议，不修改值守原文件、不改 driver、不含真实调用。
