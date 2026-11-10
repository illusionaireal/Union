"""Single owner of the supported connection profiles and their declared capability scope.

一个 profile 的真实结果不能外推到另一个 profile。每条能力声明分别给出状态和证据路径；
不支持的项必须写明，不能在页面上隐去。
"""

STATUSES = ("verified_real", "controlled", "unsupported")

CAPABILITIES = ("text_answer", "tool_roundtrip", "usage_reporting",
                "streaming", "long_job_new_input", "cancel_and_query")

REAL_EVIDENCE = "evidence/058-s02-model-tools/README.md"
CHECK_EVIDENCE = "tests/test_core_model_checks.py"
RECOVERY_EVIDENCE = "tests/test_core_model_recovery.py"
EVENT_EVIDENCE = "tests/test_core_model_events.py"
GO_EVIDENCE = "evidence/U-075/go-deepseek-2026-11-10/README.md"
RESPONSES_EVIDENCE = "evidence/U-099/README.md"
RESPONSES_RECOVERY_EVIDENCE = "evidence/U-100/README.md"


def _claim(status, note, evidence=None):
    claim = {"status": status, "note": note}
    if status != "unsupported":
        claim["evidence"] = evidence
    return claim


PROFILES = {
    "openai_compatible": {
        "title": "OpenAI 兼容 API（自填密钥）",
        "auth": "api_key",
        "private_fields": ("base_url", "api_key_sha256"),
        "capabilities": {
            "text_answer": _claim("verified_real", "U-072 已用所选连接完成两次真实推理，回答已保存。", REAL_EVIDENCE),
            "tool_roundtrip": _claim("verified_real", "真实读取所选文本，经 read_document 回执继续回答。", REAL_EVIDENCE),
            "usage_reporting": _claim("verified_real", "真实响应记录输入/输出 token；供应商未返回金额时保留未知。", REAL_EVIDENCE),
            "streaming": _claim("verified_real", "已用 Go deepseek-v4.1-flash 验证生成中的原文本及重启后页面读取；其他服务/模型须分别验证。", GO_EVIDENCE),
            "long_job_new_input": _claim("unsupported", "长任务执行期间追加输入尚未实现；刷新后用原请求查询。"),
            "cancel_and_query": _claim("verified_real", "已用 Go deepseek-v4.1-flash 验证本地停止、原请求查询及重启；未确认远端取消，中断用量/费用仍未知，占用保留。", GO_EVIDENCE),
        },
    },
    "modeld_grant": {
        "title": "modeld 授权（本机模型服务）",
        "auth": "grant",
        "private_fields": ("grant_ref", "grant_revision"),
        "capabilities": {
            "text_answer": _claim("controlled", "以显式模型替身验证文本回答；未用真实账号验收此 profile。", CHECK_EVIDENCE),
            "tool_roundtrip": _claim("controlled", "两阶段工具往返、回执配对和迟到结果隔离已受控验证。", CHECK_EVIDENCE),
            "usage_reporting": _claim("controlled", "事件与结果用量合并、金额未知保留已受控验证。", CHECK_EVIDENCE),
            "streaming": _claim("controlled", "V1页面可观测原请求已保存的部分文本，重连只查询原ID；共同投影已受控验证，此profile真实流式能力未验。", EVENT_EVIDENCE),
            "long_job_new_input": _claim("unsupported", "此 profile 未验证长任务执行期间接收新输入。"),
            "cancel_and_query": _claim("controlled", "取消、原请求查询与 unknown 保留已受控验证。", RECOVERY_EVIDENCE),
        },
    },
    "openai_responses": {
        "title": "OpenAI Responses API（自填密钥）",
        "auth": "api_key",
        "private_fields": ("base_url", "api_key_sha256"),
        "registration_options": {"wire_api": "responses"},
        "capabilities": {
            "text_answer": _claim("verified_real", "Go GPT-6 Luna 已通过真实 Responses 双请求回答与同数据重启；其他模型/服务分别验收。", RESPONSES_EVIDENCE),
            "tool_roundtrip": _claim("verified_real", "Go GPT-6 Luna 真实读取所选资料，原生工具调用及工具回执完整传入第二轮，回答含校验码。", RESPONSES_EVIDENCE),
            "usage_reporting": _claim("verified_real", "Go GPT-6 Luna 每次真实 Responses 请求分别记录输入/输出 token；未报告的金额和币种仍未知。", RESPONSES_EVIDENCE),
            "streaming": _claim("verified_real", "Go GPT-6 Luna 已验证真实 Responses 生成中的原文本及重启后页面读取；其他模型/服务分别验收。", RESPONSES_RECOVERY_EVIDENCE),
            "long_job_new_input": _claim("unsupported", "尚未实现执行期间追加输入。"),
            "cancel_and_query": _claim("verified_real", "Go GPT-6 Luna 已验证本地停止、原请求核对及重启；未确认提供方已取消，中断用量/费用仍未知，占用保留。", RESPONSES_RECOVERY_EVIDENCE),
        },
    },
}


def supports(profile):
    """Registry 是命令校验的唯一 profile 清单，不在规则里另存第二份。"""
    return profile in PROFILES


def private_fields(profile):
    return set(PROFILES[profile]["private_fields"])


def requires_api_key(profile):
    return PROFILES.get(profile, {}).get("auth") == "api_key"


def registration_options(profile):
    """Explicit protocol routing; legacy Chat registrations retain their original payload."""
    return dict(PROFILES[profile].get("registration_options", {}))


def scope():
    return {name: {"title": profile["title"], "auth": profile["auth"],
                   "capabilities": {key: dict(value) for key, value in profile["capabilities"].items()}}
            for name, profile in PROFILES.items()}
