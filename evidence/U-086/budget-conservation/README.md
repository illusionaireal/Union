# U-086 / #40：重开快照预算守恒

实施：当前单一 codex-home 值守会话；基线 `726dad42ec109e7dee3648ada68eabe7cb16f6f1`，
线上范围评论281。原 DSH owner、WIP、#22/#39/#40真实出口保持。

## 问题与修复

两份快照都把已执行调用的 used 写成0时，原 helper 只比较相等，仍可报告
重开成功。下载 driver 同样会接受两份 unknown 步进但 reserved=0 的快照。
正常领域代码根据全部步进计算预算；这是验收遗漏，不是实测产品账本丢失。

按[事先冻结的合同](contract.md)，只读 helper 在建立基线和比较快照时，
分别核对 used/unknown 步进数、非负整数计数和正整数调用上限。
未执行 released 不计占用；unknown及未报告的used用量仍为null。
没有修改产品预算、授权、身份、事务、模型循环或超时。

## 严格验证

- 原始两 driver 完整重开片段：60通过、18个预算反例失败（含2个父测试共20失败）；
  正常对照未改。最小修复后相关246 Node全部通过。
- 真实 Chrome→Core HTTP→SQLite：两次替身调用的正常重开对照通过，6个
  丢失/虚增计数与超过上限反例在原 helper 下错误接受；修复后7场景通过。
  路由只改测试响应，SQLite与原请求未变，观察GET-only。
- 初次浏览器启动未指定已安装Chrome，缺Playwright缓存；这是环境失败，
  不计RED。改用现有Chrome后才得到上述实际RED。
- 相关回归先暴露旧final-read夹具凭空多计一次used，以及旧拒绝消息匹配：
  夹具补实际completed步进，保留最终GET身份竞态；另一个断言接受预算校验
  更早拒绝released。5个初次回归失败历史保留，没有放宽行为拒绝。
- 全量npm/Python、准确源码和私有日志hash记录在[validation.json](validation.json)。
  新浏览器场景接入既有CI；准确head检查和非实施角色复核须另行读回。

复验（固定依赖，UNION_PYTHON选择项目Python，UNION_CHROMIUM_PATH选择实际Chrome）：

```text
node --test tests/exit22*.test.ts
node evidence/U-086/budget-conservation/browser.cjs
npm run check
python -m unittest discover -v
```

两个driver主程序均未运行。替身次数分列在validation.json，真实模型调用0；
未知计费/派发仍不写0。PR66准确726dad42已读回独立review5827411245及作者分支采用，仍不是rewrite采用。
本增量须另行由非实施工程角色复核预算守恒与未知用量边界，实施者不自行批准。
原工作区20份文件、原HEAD/普通索引/vendor保持；只交付本轮候选路径。

最终本地全量Python808项、10跳过、0失败（514.231秒）；npm含255 Node、
363前端、37管理及类型/构建通过。受测7个源码/合同与7份阶段日志hash均核对，
2221个基线文件逐字节比较仅有声明的7个既有文件差异，另新增4份本卡证据。
