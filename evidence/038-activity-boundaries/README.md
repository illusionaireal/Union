# 038：A03心跳时间过期与接管回执验证

2026-10-31 19:34起（UTC+8），基线dev@3e908fd。GPT-6 Astra完成只读规划→GPT-6.1 Sol执行→独立GPT-6 Astra受控子集复核通过。工程代理不是AU成员或VPS常驻链；工程模型解析型号、token与费用没有回执，保持未知。

## 实际检查与进度

开始dev领先origin/dev 14提交，tracked干净；仅用户docs/research/未跟踪资料，保留未动。本轮读branch/status/log、README/PROJECT/TASKS、STATUS/HANDOFF、开发与管理手册、主账、028、代码/测试与CI定义。只读远端核对dev仍b39c06c76e3b83a6d5413b45f58a9c736e2f15bc、main仍e11c389366814060ea4475a359c9b62036ccd176。combined-status返回statuses=[]、workflow_runs=[]；后者只覆盖PR触发首批结果，不能推断全部Actions不存在或通过。Ubuntu/Windows工程检查和Linux浏览器作业定义仍在；定义不证明实际运行。本地未上传，无本地新SHA远端CI，见[检查摘要](inspection.json)。

43任务、16done仍是10文档/6受控，没有real/sustained完成或accepted结果里程碑；逐项内容/代码依据复核[031完成声明映射](../031-member-work-state/completion-audit.md)，结合当前全量回归，[completion-audit.json](completion-audit.json)重新核对每项范围/产物和哈希。文件存在/哈希不是历史真实业务事实，不以16/43换算产品完成度。

[19:37原公司本地只读诊断](company-status.json)：原身份bootstrap/paused、0成员/工作/成果/模型调用，未配置模型/开发工作区，无Docker CLI，费用unknown。Playwright Chromium与常用浏览器命令不可用。未检查远端生产；真实公司筹建、交付、持久运行和VPS开发链仍未验。

## 规划与变更

[Astra完整规划](plan.md)先核对机制：现有TTL为0<=age<=5且真实锁held；owner仅用于观察匹配。**没有独立持久epoch/owner-token回执fencing**。正常Runner启动在锁内recover旧running→unknown，以run状态/工作版本和任职防止旧回执污染新执行。

[新增四项测试](../../tests/test_activity_receipts.py)使用真实首拍文件/UID/本地锁/Thread/Engine/Runner，模块局部受控时钟与冻结续拍等待；直接测age0/5/5.001/负age，原owner/锁不退出。过期只失去活性证据、不取消合法原回执、不解锁或重派；实际Runner启动恢复及正式核对后，新run期间旧work/progress回执拒绝、旧fail_run无效，历史/预算/资产保持，仅新成果交付。详见[矩阵](matrix.md)。

没有生产缺陷或生产代码改动，本轮增加测试及验收/交接。fixture只预约运行而没有外部调用，confirmed_not_executed依据据此记录；结果/用量/新执行器是显式模拟，不是供应商或公司成果。平台未增加业务岗位、流程、权限、取消/租约或托管控制。

## 测试与验收

| 检查 | 结果与日志 |
| --- | --- |
| 首轮4项 | 2通过/2失败，仅测试遗漏usage标准化费用字段；[日志](focused-first.log) |
| 修正测试预期后 | 4通过，0.122秒；[日志](focused-final.log) |
| Python全量 | 256通过，71.673秒；[日志](python-tests.log) |
| 独立Astra | 83通过，6.107秒；[复核](review.md)、[日志](independent-review-tests.log) |
| npm完整检查 | 退出0：管理8项、历史82任务/181依赖、动作安全9项、前端31项、类型与构建通过；[日志](npm-check.log) |
| 实际浏览器 | 未运行；不以组件检查替代A11 |

测试预期按既有usage加cost:null/cost_status:unknown，没有生产红绿修复。读取前后比较业务表定义/全部数据与资产字节；观察不recover，仍running的过期run不会自动变unknown，只有真实Runner启动恢复另行改变。Python使用.union/validation-20261031-0940/bin/python，当前可执行，未重装依赖。

## 阻塞与下一小时

U-041保持blocked、completion=null，在制3/3、就绪0、阻塞7、done16不提升。A03本地过期/接管子集通过不等于完整A03/U-041、后台续拍可靠性、真实进程崩溃、供应商迟到网络响应、跨进程/主机fencing或VPS恢复通过。WAL TOCTOU/跨库非原子、已有Executor热配置/在途配置、真实恢复、实际Chromium及整体独立验收仍未过。真实模型授权、Docker/镜像、持久主机/SSH和New API资源阻塞保留，U-042未实现。

下一小时首项：Astra冻结确定性checkpoint sidecar预检至connect竞态用例，Sol复现并记录实际文件变化，再按保守只读契约最小修复；不先扩大托管。本轮未推送、发布、付费、合并main或改生产。
