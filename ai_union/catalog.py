"""Read-only model metadata. Unknown stays unknown; this module never guesses.

The catalog is a versioned snapshot, not a provider client: it performs no network
calls, holds no credentials and grants no execution capability. Callers must treat
a missing record as "capability not established", never as "unsupported".
"""
import json
import os
from pathlib import Path

from .engine import Rejected, require

SCHEMA_VERSION = 1
MODALITIES = {"text", "image", "audio", "video", "pdf"}
COST_FIELDS = {"input", "output", "cache_read", "cache_write"}
FIELDS = {"provider", "model", "context_window", "max_output_tokens", "tool_call",
          "reasoning", "input_modalities", "output_modalities", "cost",
          "source", "revision"}
SECRET_HINTS = ("key", "token", "secret", "password", "credential", "authorization")
ENV = "UNION_MODEL_CATALOG"


def _reference(value, label, limit=200):
    require(isinstance(value, str) and 0 < len(value) <= limit and all(ord(c) > 32 for c in value),
            "模型目录" + label + "无效")
    return value


def _positive(value, label):
    require(type(value) is int and value > 0, "模型目录" + label + "必须为正整数")
    return value


def _modalities(value, label):
    require(isinstance(value, list) and value, "模型目录" + label + "必须为非空列表")
    require(all(isinstance(item, str) and item in MODALITIES for item in value),
            "模型目录" + label + "含不支持的模态")
    require(len(set(value)) == len(value), "模型目录" + label + "有重复模态")
    return list(value)


def _cost(value):
    require(isinstance(value, dict) and set(value) <= COST_FIELDS, "模型目录成本字段不支持")
    for key, item in value.items():
        require(type(item) in (int, float) and item >= 0, "模型目录成本必须为非负数")
    return dict(value)


def validate_record(value):
    """Reject anything that cannot be read back unambiguously.

    Credentials are never part of the catalog: a record that looks like it carries
    one is refused instead of being silently stripped.
    """
    require(isinstance(value, dict), "模型目录记录必须为对象")
    unsupported = set(value) - FIELDS
    require(not any(any(hint in name.lower() for hint in SECRET_HINTS) for name in unsupported),
            "模型目录不得包含凭据字段")
    require(not unsupported, "模型目录含不支持的字段")
    require({"provider", "model"} <= set(value), "模型目录记录缺少 provider/model")
    result = {"provider": _reference(value["provider"], "provider"), "model": _reference(value["model"], "model")}
    for name in ("context_window", "max_output_tokens"):
        if name in value:
            result[name] = _positive(value[name], name)
    if "context_window" in result and "max_output_tokens" in result:
        require(result["max_output_tokens"] <= result["context_window"], "输出上限不能超过上下文窗口")
    for name in ("tool_call", "reasoning"):
        if name in value:
            require(type(value[name]) is bool, "模型目录" + name + "必须为布尔值")
            result[name] = value[name]
    for name in ("input_modalities", "output_modalities"):
        if name in value:
            result[name] = _modalities(value[name], name)
    if "cost" in value:
        result["cost"] = _cost(value["cost"])
    for name in ("source", "revision"):
        if name in value:
            result[name] = _reference(value[name], name)
    return result


class Catalog:
    """Immutable lookup over validated records."""

    def __init__(self, records=(), version=SCHEMA_VERSION):
        require(version == SCHEMA_VERSION, "模型目录版本不支持")
        self.version = version
        self.records = tuple(validate_record(record) for record in records)
        keys = [(record["provider"].lower(), record["model"]) for record in self.records]
        require(len(set(keys)) == len(keys), "模型目录存在重复的 provider/model")
        self._by_key = {key: record for key, record in zip(keys, self.records)}

    def __len__(self):
        return len(self.records)

    def get(self, model, provider=None):
        """Return a copy, or None when the answer is not established.

        A bare model id that matches several providers is ambiguous, so it stays
        unknown instead of picking one.
        """
        if not isinstance(model, str) or not model:
            return None
        if provider is not None:
            record = self._by_key.get((str(provider).lower(), model))
            return dict(record) if record else None
        matches = [record for record in self.records if record["model"] == model]
        return dict(matches[0]) if len(matches) == 1 else None

    def capability(self, model, name, provider=None):
        """True/False only when the record states it; None means not established."""
        record = self.get(model, provider)
        if record is None:
            return None
        if name in ("tool_call", "reasoning"):
            return record.get(name)
        if name in MODALITIES:
            return name in record.get("input_modalities", [])
        return None

    def provider_models(self, provider):
        target = str(provider).lower()
        return sorted(record["model"] for record in self.records if record["provider"].lower() == target)


EMPTY = Catalog()


def load(path=None):
    """Load a snapshot from an explicit path or UNION_MODEL_CATALOG.

    No configured snapshot means an empty catalog: execution continues and every
    capability answer is None, which is reported as unknown rather than assumed.
    """
    location = path or os.environ.get(ENV)
    if not location:
        return EMPTY
    file = Path(location)
    require(file.is_file(), "模型目录文件不存在")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        require(False, "模型目录文件无法解析")
    require(isinstance(data, dict) and set(data) == {"version", "models"}, "模型目录文件字段不完整或不支持")
    require(isinstance(data["models"], list), "模型目录 models 必须为列表")
    return Catalog(data["models"], data["version"])


def metadata(model, provider=None):
    """Best-effort lookup for read paths.

    A configured snapshot that cannot be read is reported as unknown rather than
    breaking connection listing. Configuration paths call load() and see the error.
    """
    try:
        return load().get(model, provider)
    except Rejected:
        return None
