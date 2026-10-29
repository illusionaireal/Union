# 023 资源与工具申请记录（U-034）

申请与实际授权分开。新增可选request_support内部操作/工具，仅在有效章程与当前决策岗位都允许时提供；旧章程不自动增加权限，普通任务继续交付/报告受阻。

请求包含稳定ID、资源/工具分类、需求、理由、提出身份/任职、证据、时间、待处理状态。受信board可版本化响应needs_information/accepted_for_action/declined，关联同一请求。accepted_for_action只表示接下来的人工处理意向，不授予预算、宿主工具或采购权限；实际授权仍使用已有独立入口。

模型不接收board Key，不能自行响应申请；响应及重试沿用Console幂等回执和版本检查。新记录不得绕过pause/unknown/reconcile。实现后独立权限复核。
