# A06 子集：实际证据与边界

测试：[tests/test_session_revisions.py](../../tests/test_session_revisions.py)。每例独立临时AU。组织/成员和模型内容是fixture；Engine、Runner、DeepAgents/LangGraph、SDK检查点和回环HTTP实际执行，容器仅run_container替身。无手填session或checkpoint。

| 测试 | 验证事实 | 不据此宣称 |
| --- | --- | --- |
| unchanged_binding... | SDK先workspace工具形成非空回执、再write_file留下草稿，continued/paused；重开Engine后同session真正续接，HTTP可见旧哨兵 | 真实模型质量或真实容器操作 |
| connection_revision... | 同work_id/version、member/assignment、章程/policy及workspace revision不变，只同连接revision增加；新session/key、下一HTTP和新SDK历史无旧草稿，旧历史/回执不变 | 旧Executor连接快照热撤销、在途连接切换 |
| workspace_revision... | 只workspace revision增加，其他绑定字段不变；新session隔离且保留历史 | 全部配置竞态安全、实际Docker权限 |
| formal_handoff... | 正式交接同步改变member/assignment/work_version，当前成员新会话不借旧草稿、旧任职失效、历史保留 | 单独证明某个hash字段，跨AU成员身份迁移 |
| disabled_connection... | 正式禁用后锁内新factory在请求、预算、run及全部session表新增前拒绝，旧SDK历史不变 | 正在使用旧Executor的热更新保障 |
| disabled_workspace... | 工具不再提供；恶意替身仍返回该调用，SDK拒绝，容器0次、无新命令回执或成果，用量保留 | 组织不能进行合法文本工作、零模型请求 |
| inflight_position_revocation... | 工具已提供，HTTP回调经正式岗位更新撤workspace权限；真实工具执行前报准确撤权原因，容器0次、无新命令回执/成果，预算及用量保留 | 所有治理/权限变更组合和任意并发的完整验收 |

SDK最新checkpoint可能只有增量；以get_tuple确认根记录存在，并用list读取全部历史检查点/待写数据，不把最新channel_values当完整草稿。旧thread的checkpoint和writes逐行比较，组织session与相关旧run/用量不变；新thread同库写入正常。禁用workspace和在途撤权仍只发生一次受控HTTP请求/一次预算占用；拒绝后的correction在max_steps=1按现有Runner收口为blocked，不是模型又调用一次。

上述补上036发现的三类SDK证据缺口，但A06全部、实际恢复、A03心跳时间过期/旧实例迟到、WAL TOCTOU/跨库原子性、Chromium A11和U-041整体仍未通过。
