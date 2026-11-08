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
            "streaming": _claim("controlled", "V1页面可观测原请求已保存的部分文本，重连只查询原ID；共同投影已受控验证，此profile真实流式能力未验。", EVENT_EVIDENCE),
            "long_job_new_input": _claim("unsupported", "长任务执行期间追加输入尚未实现；刷新后用原请求查询。"),
            "cancel_and_query": _claim("controlled", "取消意图、原请求查询和 unknown 保留已受控验证，未做真实中断恢复。", REAL_EVIDENCE),
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
            "text_answer": _claim("controlled", "通过 Responses 单次内核接入；尚未完成此连接方式的真实供应商验收。", "tests/test_core_responses_profile.py"),
            "tool_roundtrip": _claim("controlled", "所选资料工具、原生上下文续传和两阶段回答经过受控验证。", "services/modeld/test/responses.test.ts"),
            "usage_reporting": _claim("controlled", "每次调用独立记录 token，未返回金额时保持未知。", "tests/test_core_responses_profile.py"),
            "streaming": _claim("controlled", "V1页面可观测原请求已保存的部分文本，重连只查询原ID；共同投影已受控验证，此profile真实流式能力未验。", EVENT_EVIDENCE),
            "long_job_new_input": _claim("unsupported", "尚未实现执行期间追加输入。"),
            "cancel_and_query": _claim("controlled", "复用原请求取消和 unknown 核对，不保证远端已取消；真实中断恢复待验收。", RECOVERY_EVIDENCE),
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
