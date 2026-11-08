# U-106 / PR39 前台独立工程复核

2026-11-09，复核源码 `702fd8718d817a61f8e57fdeef05c73b4ef01571`，
基线 `3e1071b`。产品实施者为此前单一值守执行；前台协调会话独立设计反例、
复验权限/身份/持久事实并决定采用。两者在线 member 均为 codex-home，工程
actor 分别记录，不能据此称为两个产品 AU 成员。

初版发现两个阻止采用的问题，未直接放行：

1. 原自动 loop 已产生候选，但 attempt 仍 running，合法采用后无法交付。
   基线实际 HTTP 两项失败。修复仅在显式采用事务内用原 loop/最后 step 的
   持久 succeeded/result 回执、原成果 ID 和 attempt 关联结束原尝试。
   独立反例确认手工候选不能借用循环证据；未知预约、缺失回执及后续尝试
   不会被关闭。不放宽交付约束，不自动释放额度。
2. 实际提交发生版本竞争、命令明确 rejected 后，页面无重新核对入口。
   修正夹具后 DOM 和真实 Chrome 均 RED。修复允许确认拒绝后显式核对并
   提交新命令，保留原拒绝 ID；unknown 和 succeeded 均不能据此重放。

最终精确候选：独立 HTTP/SQLite 11 项及作者 HTTP 9 项，共 20 项通过；
相关 DOM 86 项通过（含独立 5 项）；构建后实际 Chrome 16 项和独立版本
竞争恢复 7 项通过。每个浏览器场景两次显式替身调用，真实调用为零。
覆盖采用/交付落盘后丢响应、刷新查询原回执、主体变化清除、停用模型后
仍可治理成果、同 Work 的错误 result、下载来源/正文/摘要/原 Work 一致。

作者全量日志经前台核对：782 Python、9 跳过、0 失败；npm check 含 315
前端用例。产品源码、精确构建及每份日志 SHA256 见
[复核记录](foreground-review.json)。采用还须最终 PR head 的全部 CI 通过，
并核对合并 tree；此文件没有预先声称已合并。

原 RED 和夹具错误均保留在宿主私有评审目录并记录哈希。漏导入 ApiError、
复制遗漏 CSS、浏览器辅助请求缺 Origin 属于夹具/准备错误，不算产品 RED。
最早 HTTP/DOM 失败与修正 Origin 后实际浏览器失败才是相应行为证据。

可在仓库根目录复验独立 HTTP：

```sh
python -m unittest discover -s evidence/U-106 -p independent_probe.py -v
```

在先构建 Console、设置 `UNION_PYTHON` 和 `UNION_CHROMIUM_PATH` 后，执行
`node evidence/U-106/independent-rejection-browser.cjs`。它只创建临时测试实例，
通过既有自动 loop 与替身产出候选，再制造真实版本竞争；不连接真实模型。

本卡是受控工程交付。父 #22 的真实成果 #39、中断 #40 和持续运行仍未完成。
NAS 固定 PR38 发布另属 #61，不被本复核或后续 PR39 合并自动替换版本。
