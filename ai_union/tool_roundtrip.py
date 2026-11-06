"""Shared finite tool-exchange rules; the owning runtime supplies authority/I/O."""
import json

from .errors import require


def complete_tool_call(message, name, arguments):
    calls = message.get("tool_calls", [])
    require(isinstance(calls, list) and len(calls) == 1, "模型必须返回一个完整的所选工具调用")
    call = calls[0]
    require(isinstance(call, dict) and isinstance(call.get("id"), str) and 0 < len(call["id"]) <= 160
            and call.get("type") == "function" and isinstance(call.get("function"), dict), "工具调用身份无效")
    function = call["function"]
    require(function.get("name") == name and isinstance(function.get("arguments"), str), "模型调用了未提供的工具")
    from .model_api import strict_json
    require(strict_json(function["arguments"]) == arguments, "模型没有正确调用所选资料工具")
    return call


def complete_reply(message, challenge):
    require(not message.get("tool_calls") and isinstance(message.get("content"), str)
            and challenge in message["content"], "模型没有读取工具结果并继续回应")
    return message["content"]
