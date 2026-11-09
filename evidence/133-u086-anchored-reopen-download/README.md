# evidence/133 — 下载重开原成果锚定（reopened 原成果核对 GREEN）

## 背景

值守 `strict-download-review-probes.py` 的 `reopen_other_result` 反例指出：下载驱动的重开断言仅验证「存在某个 adopted 成果」，未核对**原成果 id**。这属于冻结合同要求的「重启后原成果核对」缺口。

## 修正

`exit22c_download.cjs` 的 REOPEN 段：

1. `work still delivered` 保留；
2. 新断言：原成果存活核对——`delivered_result_id` 存在时三者恒等（`delivered_result_id === adopted.id === 注册 resultId`），无 delivered id 时退回 `adopted.id === resultId`；
3. `evidence/132` 的 fork 探针将 REOPEN 抽取边界钉到 run-loop catch（旧边界 `snapshot-after-restart` 写入已不在该驱动）。

## 结果

- **复核者原版探针：11/11 PASS**（含 `reopen_other_result` 正确拒绝）；
- **修正 harness fork：11/11 PASS**（await 修正对同步断言面等价；吞错只影响 async 块的解释，见 evidence/132）；
- **真实运行**：14/14 checks，exit 0，单次派发（deepseek-v4.1-flash）——`the original adopted result survives the rebuild (original id): result-447c…`。

## 备注

- 前一轮的「吞错」归因对本 FAIL 不成立——真实根因是断言缺口；吞错仍影响 final-interrupt 的 async ERROR 解释（该项保持待定）。
- evidence/129/131 的历史记录保留；本证据为重开锚定修正版。
