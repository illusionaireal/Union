# evidence/131 — 作用域下载核验（回应 strict-download-review 四项缺口）

## 背景

值守复核（`strict-download-review-probes.py`，11 项 7 PASS/4 FAIL）指出 evidence/129 下载断言四处缺口：HTTP 状态被丢弃、AU 不核对、Work 不核对、HTTP403 可被接受。

## 修正（四项全补）

下载 fetch 改为透传状态码与响应体：**HTTP 200 必须**（403/其他失败拒绝）；`body.organization_id === 原 AU`；`body.work_id === 原 work`；原有 id/content-sha256/title 断言保留。

## 结果

**17/17 checks，exit 0**（真实 modeld，deepseek-v4.1-flash，单次派发）——
download HTTP 200 / same id / original AU / original work / content sha256 匹配 / title 匹配 / adopt+deliver / 重启持久。

## 备注

- evidence/129 历史保留；131 为其作用域修正版。
- 值守同时记录：evidence/129 实际保存 2 条请求（用量 1032/898 已知合计），README 的「单次派发」描述仅指一次页面点击/run_loop，可含多个模型请求——后续 README 措辞已按此理解修正（本驱动同构，同页一次 run_loop 一次模型请求，但措辞按请求计数理解）。
