# S02 / U-072 / #21 Python 独立工程复核

2026-11-06，两阶段评审。**当前第二轮结论：第一轮三项生产问题均已修复，复审期间发现的并发测试调度缺口也已收紧；本报告限定范围内没有未关闭的阻断项。** 独立相关回归 47 项通过；最后一次测试调度修改后的 observations 8 项通过，旧实现的两个负面对照均明确失败。精确证据、版本及限制见末尾“第二轮复审”。本报告只评价所列 Python 范围，不授予整卡完成、真实模型验收或采用权限。

第一轮历史结论：本批尚需修复三个契约缺口，建议修复后复审。以下第一轮内容和原始 RED 日志保留，不将其改写为当时已经通过。

主负责人委派范围：`ai_union/model_diagnostics.py`、`application/model_access.py`、`application/model_checks.py`、`adapters/model_access_store.py`、`model_service.py` 和 `tests/test_core_model_diagnostics.py`。正式代码只读；本目录中的报告、反例与运行日志是本评审的全部写入。

依据与边界：已读根、application、adapters、domain 和 053 的 AGENTS；S02 冻结契约全文及其 2026-11-06 诊断/事件/启动恢复细化；架构 §2、S02 调用链和 ADR-0005/0006 的 S02 决定，并核对领域规则、公共/私有存储及既有测试。审阅入口为 `rewrite/charter-v1`、HEAD `d5802f8672df88db447e7e0bb86c2f1a5265ad18`，upstream 为 `origin/rewrite/charter-v1`。工作树包含未验收的 S02 草稿，不能将 HEAD 或既有草稿当作本批已通过基线。

`.union/s02-finish/task-start.json` 只有开工哈希，协调者也未找到修复前源码副本。因此下文准确归类为**当前续接修复路径仍存在的缺口**，不能声称已逐行证明其相对开工草稿是新增回归；没有以猜测重建旧源码。`model_service.py` 可见的 HEAD diff 同时包含原 S02 撤权防护和本轮安全错误解码，两者也不混作本轮独有变更。

**先核对契约**

1. **启动失败记录可覆盖已完成的原验证。** `ai_union/application/model_access.py:233–243` 在清除 `running`、退出 `app.mutex` 后，无条件把原记录改成 `unknown`。确定性反例暂缓该失败记录，让另一个显式 `reconcile_model_check` 在空出的登记中启动并完成原来的两次推理；之后首个失败回调把 `succeeded / stage=2` 改回 `unknown`，而 Work 和输出已成功。这破坏 S02:94 的原作业恢复与重复点击要求；下一次核对又会因阶段不是 0/1 被拒绝。反例没有重复派发，始终只有原来的两次请求。

   证据：`test_review_boundaries.py::ReviewBoundaries.test_late_start_failure_does_not_overwrite_successful_explicit_recovery`，实际 `unknown != succeeded`。最小修复：清运行登记、去掉未启动线程与记录失败状态处于同一个互斥临界区，或以原阶段/状态版本条件写入；迟到启动失败不得覆盖已经进展的同一作业。保留正常线程 finally 清理和原命令回执。

2. **收集层把同序号重放当作永久失败，冲突还会丢掉本页已收集的有效前缀。** `ai_union/application/model_checks.py:190–203` 对每项都要求 `seq > cursor`，没有比较相同序号的内容。相同事件连续返回两次，使本可完成的原验证变为 `failed`。另一反例同页先返回 `seq=1, input_tokens=37, output_tokens=9`，然后返回内容冲突的 `seq=1`：拒绝冲突正确，但 `persist()` 尚未调用，先收到的有效原事件和用量均未保存，公开投影仍是 `null`。这与 S02:91–93 的原序号去重、保留原事实和已收集用量要求不符。当前正常 modeld 游标页通常不会重叠；反例明确模拟重放/冲突边界，没有把该异常响应说成正常供应商流。

   证据：`test_identical_replayed_sequence_does_not_fail_original_check` 得到 `failed != succeeded`；`test_conflicting_sequence_keeps_original_observed_prefix` 得到 `None != 37`。最小修复：相同 seq 内容一致时忽略重放，内容不同则拒绝；在拒绝后续坏事件前，经过原 request/AU/digest 校验的有效前缀应持久保存，坏项不得进入事实。继续使用原 request ID，不因冲突创建或重发 attempt。适配器 `model_access_store.py:51–66` 已有内容冲突检查，收集层须与它保持一致。

3. **用量合并能制造不存在的币种金额，或删除最后一次有效观测。** `ai_union/application/model_checks.py:30–48` 先把所有非 null 字段覆盖进一个字典，再验证类型，金额和币种也分别覆盖。事件 1 是 `cost_minor=4,currency=USD`，事件 2 只有 `currency=JPY`，当前结果成为 `JPY 4`；没有任何原事件报告过该费用。另一个反例已有 `37/9` tokens 和 `USD 4`，最终用量返回 `input_tokens=-1, output_tokens="unknown", cost_minor=-1`，当前投影把已知值抹成 null。这违反 S02:53、92 的“最近有效累计量”“最终已知字段优先”和明确币种/整数 minor unit 事实要求，不能采纳为可信费用投影。

   证据：`UsageFacts.test_currency_only_update_does_not_relabel_an_old_charge` 实际 `(4, 'JPY')`；`test_invalid_later_values_do_not_erase_last_valid_observation` 实际 `(None, None)`。最小修复：对新值验证后再合并；无效新值不能覆盖已有有效字段；金额/币种必须来自同一个有效观测，作为一组更新，不能跨观测拼接。合法最终值仍优先且不相加，缺失从未观测的字段仍为 null，无币种浮点 cost 仍不能推断成金额。

**代码质量与其余本批边界**

- 固定诊断集中在 `model_diagnostics.py`，供应商原错误正文未直接进入新增公开诊断；实际解码后的 key 检查与 modeld/供应商认证区分的现有行为测试均通过。本批没有发现新的已复现诊断泄漏。
- 配置意图、AU 事实和私有 attempt 仍进入既有 GovernanceStore 的同一 AU 事务；实际模型 I/O 位于这些事务外。原请求摘要/身份检查保留，恢复不创建新的原请求，也没有引入未来 S03 通用循环。
- 序号合并在收集层和适配器两处表达，当前差异已造成第 2 项问题；应明确每层的验证/持久化责任，避免一层支持幂等而另一层提前终止。用量合并应先规范字段，再产生公开投影，防止有效性判断与覆盖顺序分离。
- 既有回归覆盖正常两阶段工具往返、当前授权/祖先版本变更、资源并发、原工具回执、重启恢复、撤权后事实以及 legacy 消费者。通过只证明所覆盖的受控行为，不把现有用例数或本次评审解释为 M01–M10 全部完成。

**实际运行证据**

Python `3.13.14`，使用项目 `.venv/Scripts/python.exe`，`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。模型调用均为临时 HTTP/SQLite 和 `ModeldDouble`；真实模型调用 0。

```powershell
.venv\Scripts\python.exe -m unittest tests.test_core_model_diagnostics tests.test_core_model_checks tests.test_core_model_recovery tests.test_core_model_boundaries tests.test_model_service -v
```

`regression.log`：39 tests，68.304 s，全部通过，包括用户提供的新增 7 项 diagnostics 测试。

```powershell
.venv\Scripts\python.exe -m unittest discover -s .union/s02-finish/python-review -p test_review_boundaries.py -v
```

`boundary-probes.log`：8 tests，9.225 s，5 个有意义失败对应上述三类缺口。3 个通过的独立正常对照为：收到第一页后下一次 request 查询失败、500 条第一页后第二页查询失败、已持久观察用量后取消。这三项均保留已知用量，保持原请求，未执行资料工具，也未派发第二次推理。反例不修改正式代码；主负责人可按严格 TDD 将必要行为断言收入正式测试。

本轮未复验 modeld TypeScript 保密实现、当前 Codex Responses 适配、真实 profile、浏览器、全量 npm/Python 或发布安装；这些在父任务的其他已分配范围中，不以本报告替代。

开始审阅时文件 SHA-256（用于识别本报告所见内容；随后并行修复可能改变工作树）：

| 文件 | SHA-256 |
| --- | --- |
| `ai_union/model_diagnostics.py` | `8f5f1b648fb4af7bf6473668ede63642101804886e0306ff9c5b319f21c07e15` |
| `ai_union/application/model_access.py` | `fc8871dd6480869bcd3e50bde5a49f20fa72e95b382d6ef7781c94e4e8013563` |
| `ai_union/application/model_checks.py` | `b5fcc5a3005a9f248d103009488109f35599e5478ca73163b7e904139d8e982f` |
| `ai_union/adapters/model_access_store.py` | `7a2153e866bbbea3daa2182ebecd75332870729a7f949a528e2cb14d71ffb446` |
| `ai_union/model_service.py` | `bd37bf907ee66df94d2b955f6e0be2e30bb92f6668825e4cd66c4611e0081885` |
| `tests/test_core_model_diagnostics.py` | `30348f30eff462f5c418bd159883439eb7e44b2f4b576a4404af22ea6b91e309` |

契约在本次核对时 SHA-256：`fb3678c742fa883ab08c5f0ed73bc88d3eea4861b0b6170d19240f1ddcb861c7`。

**第二轮复审：生产修复与确定性回归**

仍在同一 HEAD/branch，只重审上述三个问题和被收入正式测试的 `tests/test_core_model_observations.py`。生产修复、测试改动由主负责人实施；本评审没有修改正式代码、测试、Git、主账或在线记录。核心契约及私有适配器哈希未改变。

1. 第 1 项已关闭。`application/model_access.py:216–245` 在同一 `app.mutex` 内记录 `worker_start_failed`，其后 finally 才清除 running 与未启动线程引用；正常启动仍由原 worker finally 清理。显式恢复不能抢在这份旧失败事实之前完成，再被它覆盖。原命令回执、Work 与请求仍保留，没有新增后台自动派发。
2. 第 2 项已关闭。`application/model_checks.py:180–226` 用原 seq 对应原事件内容；相同内容精确去重，冲突/非法顺序拒绝；错误处理通过既有身份和 request digest 校验持久保存已验证前缀，坏项不进入事实。满页没有推进游标时明确拒绝，避免重放页形成无进展循环。原分页故障、下一次 request 故障及取消对照继续保留，完整正常验证仍成功。
3. 第 3 项已关闭。`application/model_checks.py:27–65` 先验证每个新 token 字段，再更新最后有效观测；金额与三位大写币种只在同一有效观察中成对更新。无效或缺失新值不抹去原事实；已知最终值继续优先，累计流值与最终值不相加，也没有把 SDK 无币种浮点 cost 推定为费用。metadata 本身不会把未知用量的 basis 冒称为最终结果。

复审时另检查了并发测试是否真的约束旧缺陷。中间版本使用 `reconciled.wait(0.5)` 后释放记录屏障，未保证坏实现先完成恢复；评审在独立进程中仅把此前读到的旧 `spawn` 替换到内存，无额外模型延迟时同一测试居然通过，见 `rereview-negative-control.log`。这不是生产修复回退，而是发现其回归测试可能漏检。

主负责人随后去掉 0.5 秒判断。最终 `tests/test_core_model_observations.py:194–220` 在屏障处非阻塞观察锁是否允许该交错：允许时明确等待恢复成功再释放旧失败回调，否则让串行恢复在失败事实写完后执行。锁探测只决定测试调度，最终判断仍是同一原 check 保持 succeeded 和恰好两次原调用。这保留外部行为断言，也兼容另一种合法的条件写入修复方向。

对收紧后的同一个测试，评审再次只在独立进程内临时装入旧 `spawn`，分别使用 0 秒及每次模型结果查询 0.4 秒的模型 double 延迟。两次都确定到达最终状态断言并失败为 `unknown != succeeded`（1.899 s / 2.757 s），见 `rereview-negative-control-tightened.log`；没有靠异常退出、调用不足或超时形成 RED。脚本为 `rereview-negative-control.py`，它不落盘修改任何正式模块。此验证缺口已关闭。

第二轮独立运行证据：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe -m unittest tests.test_core_model_observations tests.test_core_model_diagnostics tests.test_core_model_checks tests.test_core_model_recovery tests.test_core_model_boundaries tests.test_model_service -v
```

`rereview-regression.log`：47 tests，73.786 s，全部通过。随后仅收紧了上述并发测试调度，生产代码未再变化；因此最后复跑受影响的整个 observations 模块：

```powershell
.venv\Scripts\python.exe -m unittest tests.test_core_model_observations -v
```

`rereview-observations-final.log`：8 tests，9.116 s，全部通过。第一轮 `.union/.../test_review_boundaries.py` 和 `boundary-probes.log` 保留为历史 RED 工件；其旧并发调度未用于宣称当前 GREEN，当前回归采用正式 observations 文件。

协调者提供的 `core-observations-red.log` 和 `core-observations-green.log` 也已读取：前者 8 项中 5 个行为失败，后者与 diagnostics/checks/recovery 合计 29 项通过。它们属于协调者证据；本节的 47 项、最终 8 项和旧实现负面对照属于此次独立执行。

第二轮最终文件 SHA-256（在最后一次 GREEN 后重读确认）：

| 文件 | SHA-256 |
| --- | --- |
| `ai_union/application/model_access.py` | `3bb6c4e951e170be3ed70c105ac3d7b0d3fdd98a2ec63731ae4dd52222a2d6d6` |
| `ai_union/application/model_checks.py` | `875d15e62b86caaa2af779e8774e2a4e4005ed0df6c02a334e25e8eb12c7c05e` |
| `tests/test_core_model_observations.py` | `aa4754ec5d9b7a95effd5c40f4559331d3de01a845b23722aa78a838eb0258ac` |

本节结论仍限于三项修复及相关 Python 受控回归。真实模型调用为 0；没有把它提升为当前 Codex Responses、modeld TypeScript、浏览器、安装或 #21 整卡验收。
