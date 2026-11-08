# U-086：a3bb2cc 的页面取消仍不能用于自动工作

2026-11-09，回应 #40 评论140。作者候选准确 SHA 为
`a3bb2ccf71b6a4de5b42588176f71f43489d35de`，GitHub HTTP200 与 fresh fetch
一致。它包含当前集成 `2ff90f1`；相对310c7e1新增页面按钮、类型和测试。
本次只修改评审证据，原 DSH owner/progress/WIP 和真实父卡验收保持。

**候选不能采用。** 四项预算安全检查通过，但实际自动调用仍没有取消
入口；新增取消代码还绕开了已有命令恢复与回执接纳边界。原“仅手工预约”
测试通过不能证明 Core 自动工作取消完成。

先冻结[页面复核合同](cancel-page-contract.md)，再在准确源码的隔离导出副本
运行新增DOM反例；沿用锁定Node24.19.0依赖、Python3.12.10环境。

| 准确 a3bb2cc 上的检查 | 结果 |
| --- | --- |
| 原四项实际HTTP/SQLite预算保护 | 4 PASS，5.250s；unknown仍占用，完成用量保留 |
| 实际在途自动请求取消送达原modeld ID | 1 FAIL，0.962s；HTTP200/rejected，cancel POST=0 |
| 自动reserved预约在实际WorkPanel中的取消入口 | FAIL：没有按钮；command_id正是页面隐藏条件 |
| 取消POST响应丢失、重挂载后查询同一命令 | FAIL：无“查询原请求”；新增随机ID未进入持久原引用 |
| POST后principal_id变化 | FAIL：缺少失效提示，DOM仍包含旧取消回执正文 |
| POST后service_instance变化 | FAIL：同上 |
| unknown浏览不自动发命令 | PASS；这是安全对照，不是取消能力通过 |

DOM合计4 FAIL/1 PASS，4.45s。身份两例中旧正文确实出现在渲染的`p`元素，
不是仅检查测试源码字符串。完整日志只存宿主私有目录；
[结果与日志哈希](cancel-page-review.json)不含私有地址、配置或运行日志。

新增源码定位：候选 `WorkExecution.tsx` 的 `cancellable` 使用
`reserved && !command_id`，恰好排除所有自动预约。`cancelLocal`直接生成新
UUID并POST，只在发送前读取session；它既没有remember原取消命令，也未经过
既有accept对回执身份和当前session的复核。因此已有start_attempt/run_loop
通过的恢复测试不能覆盖这个新handler。

后两类DOM测试使用未派发手工预约，只为触达候选新增的handler；不要求
继续开发这种UI。请原作者将取消接入真实自动请求合同，复用统一原命令恢复
和当前资格检查；保留unknown占用。远端取消受理、命令成功和实际执行结果
分别记录，不能用released与费用未知文案代替执行核对。

## 可运行反例

先将准确候选用git archive导出到新的临时目录，安装该版本锁定的依赖，
或链接与其锁文件一致的既有node_modules。不要在其他开发者checkout运行
注入器，它拒绝包含`.git`的目录，不覆盖候选原测试文件。

```text
python evidence/U-086/cancel-boundary-probes.py <exact-source-export>
python evidence/U-086/cancel-route-probe.py <exact-source-export>
python evidence/U-086/run-cancel-page-probes.py <exact-source-export> <node-executable>
```

第三项把[五项DOM断言](cancel-page-probes.tsx)与候选既有fixture前缀组合成
临时独立测试文件。预期在a3bb2cc失败；不并入默认应通过测试集合，也不
篡改被评源码制造RED。Windows设置PYTHONUTF8=1、PYTHONIOENCODING=utf-8。

这次是受控候选复核，无实际Chrome或真实供应商验收声明，真实推理为0。
PR42前一head98dd2e8的Python782/9跳过和npm结果保留，新增证据的结构检查
与准确head CI分列；check:management的37项检查、Python AST、TSX编译和
diff空白检查通过，候选产品/fixture字节及依赖锁逐一核对。不改产品、部署或迁移；
#28/#37/#61仍各按原资源/共享/迁移授权条件处理。
