# 044 实施计划

前置：用户确认凭据读取与一次真实调用（见 spec「需要用户决定」）。未确认前只做第 2、3 步的代码与测试，不触碰凭据、不产生调用。

## 1. 宿主准备（需授权）

- [ ] 以 root 读取原生服务 active 凭据，写入 `/volume1/docker/union-dev/ui-private/model-credentials/opencode-go.token`（目录 0700、文件 0600、uid 10001）。
- [ ] 校验：非符号链接、非空、≤4096 字节、权限正确、内容不进终端与日志。
- [ ] 重建 `ai-union-console`，追加 `UNION_MODEL_CREDENTIAL_DIR=/private/model-credentials`，其余环境变量与挂载保持不变；保留旧容器作为回滚点。
- [ ] 失败即停：文件不可写、权限不符、容器未起来都不继续。

## 2. 后端：受限请求头

- [ ] `model_api.py` 的 `validate_config` 增加 `headers`：≤2 个、名字白名单（当前仅 `x-opencode-org-id`）、值 ASCII 可见且 ≤128、拒绝鉴权/传输控制头。
- [ ] `model_protocols.encode_request` 合并连接头；Bearer 由凭据生成且不可被覆盖。
- [ ] 保留“wire 中出现凭据即拒绝派发”的守卫。
- [ ] 单元测试：允许/拒绝矩阵、旧连接兼容、导出不含头（头值非机密但统一不导出）、回执只记录头名。

## 3. 后端：从 Go 目录创建连接

- [ ] `subscriptions.py` 暴露创建入口：校验模型 id 属于原生目录的 `opencode-go` 且 `enabled`；`x-opencode-org-id` 由服务端从原生目录读取，不接受客户端输入。
- [ ] 组装连接：`base_url`、`protocol=openai_chat_completions`、`model`、`api_key_file=opencode-go.token`、`headers`、`billing.basis=subscription`、`context` 取目录上限。
- [ ] 归属当前组织，不自动设为默认，不自动测试；同名或同模型重复创建拒绝。
- [ ] 测试：权限（仅平台管理员）、模型白名单、重复拒绝、凭据缺失时的明确错误。

## 4. 前端

- [ ] Go 卡片：选中模型后出现“用此模型创建连接”，提交后跳到已保存连接并提示“需要显式测试才验证能力”。
- [ ] 失败分类提示：401（凭据可能已轮换）、limited=true、端点不可达、模型不存在。
- [ ] 移除“只读/不会发起调用”的免责文案，改为真实动作说明。
- [ ] 组件测试：创建成功、重复拒绝、401 提示、非平台管理员不可见。

## 5. 真实验收（需授权窗口）

- [ ] 用用户确认的模型发一次 `max_tokens≈1` 的请求；记录请求数=1、耗时、返回类别、token 用量。
- [ ] 失败时按 401/429/未知分类记录，不重试；不创建组织、不写业务成果。
- [ ] 结果写入 `evidence/048-go-subscription-connection/`，包含实际回执与限制。

## 6. 复核与收口

- [ ] 独立复核凭据落位、头白名单、失败语义、导出边界。
- [ ] 主账：U-060 从 backlog 转为 done（controlled），并记录真实调用次数。
- [ ] 更新 `docs/MODEL_ACCESS.md`（Go 连接的使用与限制）、`docs/FRONTEND.md`（选模型→建连接）。

## 回滚

1. 删除或停用新建连接（组织数据不受影响）。
2. 删除 token 文件与 `UNION_MODEL_CREDENTIAL_DIR`，重建容器回到旧配置（旧容器已在第 1 步保留）。
3. 代码回退：`headers` 为可选字段，旧连接无需迁移；回退只需还原该提交。

## 风险

- 端点可能不接受普通 Bearer，或需要额外头（一次真实调用即可判定，失败即停，不保留半成品入口）。
- 订阅凭据会轮换；401 需宿主重新导出，属人工维护步骤。
- 用订阅端点跑组织任务是否符合订阅条款由用户判断；本方案不替用户决定。
- 多个历史 Go 连接可能造成选择歧义，本轮不清理。
