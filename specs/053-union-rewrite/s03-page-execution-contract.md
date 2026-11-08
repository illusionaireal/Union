# U-084：页面运行已登记的 AI 工作（编码前冻结）

基线86f283a；在线执行卡#38，上级#22；一个完整出口，4–8小时。
父卡负责人、真实验收和其余依赖不变。旧手工记账控件继续隐藏。

- 核心/tasks在已有的身份、服务实例和AU投影下显示自动运行控件。无活动
  attempt时明确“准备本轮执行”(start_attempt)，准备成功刷新后才可显式
  “运行AI工作”(run_loop)。后者实际复用现有自动循环，不是手工记账。
- 每个工作分别持有原请求；POST前重验session与工作读取权限/版本，将ID、
  kind、base_version及主体/服务/AU/工作身份写入sessionStorage，再POST一次。
  不保存目标、资料、正文或密钥。存储失败不POST；准备与运行不自动串行派发。
- 重复点击/响应丢失/刷新后不生成替代ID、不自动POST；只查询治理原回执。
  404、错配回执或unknown保留原引用；unknown绝不当作未执行或释放预约。
  原引用即使已确认也保留，避免同一工作/尝试重复运行，后续新轮次另行设计。
- 验证回执id、kind、AU、base_version、actor及状态/版本；采用前再读当前
  session。主体、服务或AU变化后旧异步结果不得展示；撤权清除旧工作及下载。
  无权限、已结束、有未知预约或无剩余预算的工作不提供新派发。
- run_loop是长请求，客户端不以统一5秒读取超时人为终止等待；页面可重开并
  查询同一请求，不扩展真实模型任务deadline或取消权限。
- 严格RED→最小GREEN；真实HTTP/SQLite+明确modeld替身、DOM与实际浏览器
  分别记录，npm/Python全量和精确head CI，以及另一角色的权限边界复核。
  受控通过不等于父卡真实模型/资料/中断/持续验收通过。

## 2026-11-08 独立复核：尚无回执的查询边界

治理回执接口为保护原签发者，对尚未提交的回执和无权取得的回执统一返回
403；不能从此响应单独推断当前 AU 读取权已撤销。长循环尚在执行时，页面
必须保留原 ID 和查询入口，不创建替代请求、不重新 POST。

遇此响应后，独立重验当前 session 与当前 AU 工作投影（协议、主体、AU），
并在显示查询提示前再次检查 session。重验通过只说明当前读取权有效，
不说明回执存在、执行成功或未执行；显示“原回执尚不可取得”并允许稍后
查询。session/工作读取明确拒绝或身份错配则清除旧工作和下载。403 后的
读取不采用任何回执正文、不释放预约、不修改服务端的统一错误及授权合同。

本次协助只含该恢复缺陷、DOM反例及真实HTTP/浏览器受控验证，预计1–2小时，
是原#38的独立复核修复；owner仍为chatGPT-online，父#22和真实出口保持。
候选实施者codex-home不能自称本修复的独立权限复核者，须由另一工程角色采用。

## Foreground review: readable original lookup without new execution permission

A current authorized work read may have can_start=false. Existing scoped original
references must still offer receipt lookup, including after reload and a receipt-only
403. Permission to start a new attempt or loop is gated separately and revalidated
on submission. Actual read/session/scope denial still clears the view. No ID change,
POST replay, reservation release or server authorization change is permitted.
