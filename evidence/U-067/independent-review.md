# S03 自动执行候选独立复核

2026-11-08，复核人 codex-home；实现作者 DSH。固定提交 bdbc382f40c6d476503879a0f6f743cca3886463，原提交已发布为 [草稿 PR #17](https://github.com/illusionaireal/Union/pull/17)。同步目录中更新的提交/未提交工作没有被覆盖，本结论不冒充更新版本的复核。

发现三个阻止当前候选合并的问题，均由离线验收探针复现：

1. transport 入口重新打开 AU 数据库时 steps=[]，模型请求派发前没有持久化预约；apply_step/fail_step 在派发后才预约。必须先原子记录预约和原请求关联，再执行；重启/重入核对原请求。本次不声称 modeld 幂等已被绕过或发生重复供应商计费。
2. read_document 读取的正文被丢弃，第二轮请求缺少授权文件中的公开标记、上一轮 assistant 工具请求及 tool 结果。每轮只重建 system/user，因此预置第二次答案的 fake 不能证明模型使用了实际资料。
3. fake modeld 已接受请求并 completed，但随后 action_authorized=false 时应用记录“未执行”、steps=[]、预算 used/reserved=0。禁止采用结果的同时必须保留已经执行、usage 或待核对事实；派发前拒绝、完成后撤权和未知结果需要区分。

复现：将固定提交导出为独立目录，使用安装好项目依赖的 Python，运行 `python independent-review-probes.py <exact-source-directory>`。三个测试均 RED，3 failures、0 errors、3.062 秒。通过项目 HTTP 接口与真实本地持久化，模型使用 fake；没有修改候选源码制造失败，没有真实模型调用。

详细反馈与完整脚本已发布到 [PR 评论](https://github.com/illusionaireal/Union/pull/17#issuecomment-6714422601)。当前候选保持 draft，由原 owner 修复后再进行当前 head CI 与独立复核，不关闭 U-067。

用户本轮 OpenCode Go 的两次调用已经用于 U-075 验收，合计 578 输入 / 121 输出 tokens；不能再次借用旧 readiness 文档中的余额描述触发 S03 真实调用。离线实现与修复可继续。

2026-11-09追加：原三个缺口已经合入修复；#40后来提出的fe556aa仍基于旧代码。
在其准确源码上重现原三个失败，并新增线端请求ID、未知预约与重启回执三个
反例，当前8ea2b4d通过新增探针。见[U-086候选复核](../U-086/README.md)；
该结论不表示当前集成重新出现旧缺陷。相邻[115源码复核](../U-085/2026-11-09-source-review.md)
也保留了局部页面/HTTP历史与完整真实出口的区别。
