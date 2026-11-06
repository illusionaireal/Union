"""Fixed public model diagnostics; provider text and headers stay private."""

MESSAGES = {
    "worker_start_failed": ("后台验证未能启动；原操作已经保存", "请核对原操作后继续；系统不会重复提交原模型请求。"),
    "model_service_unavailable": ("暂时无法连接本机模型服务", "检查模型服务是否启动并恢复连接，再核对原操作。"),
    "model_service_authentication_failed": ("核心与本机模型服务之间的认证失败", "检查本机模型服务的访问配置；这不表示供应商 API 密钥错误。"),
    "model_service_rejected": ("本机模型服务拒绝了请求", "检查连接配置及当前模型授权，再核对原操作。"),
    "provider_authentication_failed": ("模型供应商拒绝了 API 密钥或账号认证", "检查供应商密钥及账号权限，修改连接后重新验证。"),
    "model_not_found": ("供应商找不到指定模型，或该账号无权使用它", "检查模型名称及账号可用模型，修改连接后重新验证。"),
    "provider_rate_limited": ("模型供应商限制了本次调用", "检查供应商额度或限流状态；先核对原请求，不自动重试。"),
    "provider_unavailable": ("模型供应商暂时不可用", "待服务恢复后核对原请求；未确认前保留调用占用。"),
    "provider_request_rejected": ("模型供应商拒绝了本次请求参数", "检查模型与协议支持范围，修改连接后重新验证。"),
    "provider_result_unconfirmed": ("原调用结果尚未确认；已知用量和原请求保留", "核对原执行；结果未知时不要重复提交模型请求。"),
    "authorization_changed": ("当前授权或版本已变化，原结果不能继续使用", "检查当前负责人、连接和资源授权；已发生用量仍会保留。"),
    "invalid_model_result": ("模型未返回本次验证需要的完整工具调用或回答", "检查模型与工具能力；原结果和已发生用量保留。"),
    "original_request_missing": ("模型服务暂未找到原请求记录", "核对原模型服务和请求；查不到不代表远端从未执行，不自动重发。"),
}

ALIASES = {
    "grant_unavailable": "authorization_changed",
    "grant_unavailable_before_dispatch": "authorization_changed",
    "grant_not_found": "authorization_changed",
    "model_not_granted": "authorization_changed",
    "api_account_scope_mismatch": "authorization_changed",
    "request_not_found": "original_request_missing",
    "api_connection_not_found": "original_request_missing",
    "incomplete_model_result": "invalid_model_result",
    "credential_in_model_content": "invalid_model_result",
    "hosted_tools_forbidden": "invalid_model_result",
    "unsupported_message_content": "invalid_model_result",
}


def safe_code(code, fallback="provider_result_unconfirmed"):
    if not isinstance(code, str):
        return fallback
    return code if code in MESSAGES else ALIASES.get(code, fallback)


def failure(code=None, status=None):
    code = safe_code(code)
    if code == "model_service_rejected":
        if status in (401, 403):
            code = "model_service_authentication_failed"
        elif status == 404:
            code = "original_request_missing"
    message, next_step = MESSAGES[code]
    return {"message": message, "diagnostic": {"code": code, "next_step": next_step}}
