"""Public diagnostics contain host-owned text only, never executor/provider bodies."""

MESSAGES = {
    "api_authentication": ("模型 API 认证失败", "在模型与 API 中检查密钥、地址及模型访问权限，然后手动测试连接。"),
    "api_rate_limited": ("模型 API 触发限流", "检查供应商额度与限流状态，等待恢复后手动继续；本次没有自动重试。"),
    "api_request_rejected": ("模型 API 拒绝了请求参数", "检查模型 ID、API 地址及输出上限字段；组织协作需要模型支持工具调用。系统不再发送 response_format。"),
    "api_provider_error": ("模型 API 服务异常，执行结果未知", "先核对供应商请求记录，再在组织设置核对未知执行；不能直接重派。"),
    "api_redirect": ("模型 API 地址返回了重定向", "填写供应商的最终 API 根地址；系统不会把密钥转发到重定向地址。"),
    "api_connection": ("无法连接模型 API 或连接中断", "检查地址、网络、证书及供应商请求记录；若结果未知，先核对原执行。"),
    "api_timeout": ("模型 API 请求超时，执行结果未知", "核对供应商原请求，处理未知执行后再手动继续；可在连接配置中调整超时。"),
    "api_output_truncated": ("模型输出达到上限，结果不完整", "在模型与 API 中提高最大输出 token，或调整模型和任务长度，再手动继续。推理模型的推理也可能占用输出额度。"),
    "api_refusal": ("模型拒绝返回所需结果", "检查目标与任务内容，或更换适用模型，再手动继续。"),
    "api_unexpected_tool": ("模型请求了当前不支持的工具", "模型只能调用本轮提供的组织工具；检查模型的 Chat Completions 工具调用兼容性。"),
    "api_invalid_json": ("模型 API 返回的消息或工具调用不完整", "检查 Chat Completions 接口兼容性；工作正文支持普通文本，无需 JSON 包装。"),
    "api_action_required": ("模型已回复计划，但尚未调用组织工具", "系统会在本次剩余额度内给出一次反馈；若仍未完成，可手动继续或更换支持工具调用的模型。"),
    "api_tool_arguments": ("组织工具参数需要修正", "本次提议未生效；系统会在本次剩余额度内将原因反馈给模型一次。"),
    "api_response_too_large": ("模型 API 响应超出容量", "减少最大输出或任务长度，再手动继续。"),
    "api_secret_response": ("模型 API 响应含凭据，已拒绝记录", "核对供应商与连接配置，确认凭据没有进入模型输入或输出。"),
    "runtime_validation": ("模型输出未通过运行时校验", "查看校验原因。确认后手动继续，模型会收到上次失败事件并重新作决定。"),
    "execution_failed": ("执行失败", "原调用已保留，请核对执行记录及连接配置后手动继续。"),
    "execution_unknown": ("执行结果未知，需要核对", "先在组织设置核对原执行，不能直接重派。"),
    "dispatch_blocked": ("运行派发受阻", "检查调用额度、预算、任务状态和待核对执行。"),
}

PARAMETERS = {"response_format", "max_completion_tokens", "max_tokens", "model", "tools"}
RULES = {
    "初始化需要至少两名成员，最多二十名", "初始化需要一至三十项首批任务", "成员姓名不能重复", "任务标题不能重复",
    "负责人必须是已列出的成员姓名", "任务负责人必须是已列出的成员姓名", "任务依赖必须引用首批任务标题",
    "任务依赖存在循环，请先安排能够独立开始的工作", "本轮未授权该工具",
    "启动需要至少两名可区分成员", "启动需要至少两名实际任职成员", "启动需要工作和决策责任",
    "工作岗位缺少成果工具权限", "操作不在当前章程及岗位授权内", "岗位权限超出章程",
    "任职对象不存在", "决策岗位不存在", "调用身份没有有效任职", "已有任职必须使用交接操作",
    "岗位必须有唯一的有效任职；多席位请建立独立岗位",
    "完成声明缺少实际成果", "交付前生效权限检查失败", "请按章节顺序投稿，并先复盘上一周期反馈",
    "章节正文至少 800 字符；提纲不能作为首版章节交付", "必须在取得平台反馈后另作经营决定",
    "先创建或修改后续工作，再复盘；不能只写反思", "下一章须实际使用上一周期决定后交付的成果",
    "调用额度耗尽；需要董事会配置追加资源", "模型用量缺失，成本未知；暂停新调用并核对供应商回执",
}


def issue(code, *, http_status=None, parameter=None, rule=None):
    if code not in MESSAGES:
        return None
    message, recovery = MESSAGES[code]
    result = {"code": code, "message": message, "recovery": recovery}
    if type(http_status) is int and 100 <= http_status <= 599:
        result["http_status"] = http_status
        result["message"] += f"（HTTP {http_status}）"
    if isinstance(parameter, str) and parameter in PARAMETERS:
        result["parameter"] = parameter
    if isinstance(rule, str) and rule in RULES:
        result["rule"] = rule
        result["message"] += "：" + rule
    return result


def public_failure(value):
    """Reconstruct allowlisted diagnostics, including when reading existing records."""
    if not isinstance(value, dict) or not isinstance(value.get("code"), str):
        return None
    return issue(value["code"], http_status=value.get("http_status"), parameter=value.get("parameter"), rule=value.get("rule"))


def runtime_failure(error):
    reason = str(error)
    return issue("runtime_validation", rule=reason) if reason in RULES else issue("dispatch_blocked")
