# Astra 规划：服务端与 HTTP 观察边界

2026-10-31 13:31起（UTC+8），基线dev@fe20291。实际规划代理GPT-6 Astra，实施GPT-6.1 Sol；规划者只读核查，未执行测试。以下记录实际返回的取舍。

最高优先级是028 A01–A06服务端/实际HTTP交集：真实临时Server、cookie会话作用域、两AU同名成员/会话、正式Engine状态及真实SDK检查点，联合验证完整JSON资料边界和稳定fixture只读性。已有snapshot算法回归不逐条复制。

最小实施六组：
1. 全局与限域board/observer、401/403和目录过滤。
2. 两AU复用m1/m2及session ID，只有一方有根checkpoint，引用与存在性不串读。
3. 伪造观察参数不扩权；observer不能写；未实现runtime控制路由404、未知命令拒绝。
4. 真实SqliteSaver.put写入私有正文/metadata，配置密钥、工作区、失败、feedback分别设置哨兵，检查整个响应含非空回执。
5. 正式Engine状态链覆盖ready/依赖等待、暂停、活跃run、活性丢失、unknown和预算，反复GET不执行、不恢复。
6. 旧库读取不建表；当前工作区/章程/任职变化反映到观察，历史checkpoint不自动接续。

GET前后核对业务表定义、全部内容、预算及checkpoint文件集合/非SHM字节；SDK setup/get_tuple、模型、容器、runner和recover设失败哨兵。正常观察序号/采集时间可变化，SHM与任意并发WAL零写入不作保证。HTTP测试独立类复用现有Server清理机制，避免继承重复执行旧测试。

未出现生产缺陷时允许只交测试/证据，不为产生diff改正确代码。仅实际失败可导向最小生产修复；权限/资料边界变化需独立工程复核。

A06：has_checkpoint=true只证明根记录存在，requires_validation不授予当前权限或承诺安全重放。已有实际SDK章程变更回归；连接/工作区revision和任职变化的真实会话复用仍应单独核对，缺失则明确未验。先定向HTTP、相关工程回归、完整Python/npm，再独立复核。U-041不因该子集通过而关闭。

平台只提供公共观察，不预设AU业务岗位、成员或管理流程；fixture不是公司运行、VPS或真实供应商证据。工程模型实际解析型号、token和费用没有回执，保持未知。
