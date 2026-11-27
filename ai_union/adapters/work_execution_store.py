"""Private original request and model facts in the caller's existing AU transaction."""
import copy
import hashlib
import json
import math

from .core_au_store import encoded
from ..errors import Rejected, require

MAX_EXECUTION_BYTES = 8 * 1024 * 1024
MAX_WIRE_DEPTH = 64


def _wire_number(value):
    """JS JSON.parse uses binary64; its shortest decimal uses fixed [-6, 21)."""
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise Rejected("模型 wire 数值超出有限 binary64 范围；未派发") from error
    require(math.isfinite(number), "模型 wire 不支持非有限数值；未派发")
    if number == 0:
        return "0"
    negative = "-" if number < 0 else ""
    text = repr(abs(number)).lower()
    mantissa, _, power = text.partition("e")
    whole, _, fraction = mantissa.partition(".")
    digits = (whole + fraction).lstrip("0")
    exponent = int(power or "0") - len(fraction)
    while digits.endswith("0"):
        digits = digits[:-1]
        exponent += 1
    position = len(digits) + exponent
    if 0 < position <= 21:
        if position >= len(digits):
            result = digits + "0" * (position - len(digits))
        else:
            result = digits[:position] + "." + digits[position:]
    elif -6 < position <= 0:
        result = "0." + "0" * -position + digits
    else:
        result = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
        result += "e" + ("+" if position > 0 else "") + str(position - 1)
    return negative + result


def _wire_string(value):
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise Rejected("模型 wire 含孤立 Unicode 代理字符；当前 UTF-8 通道不能发送") from error
    return json.dumps(value, ensure_ascii=False)


def _canonical_wire(value, depth=0):
    require(depth <= MAX_WIRE_DEPTH, "模型 wire 嵌套过深或含循环；未派发")
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) in (int, float):
        return _wire_number(value)
    if isinstance(value, str):
        return _wire_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_canonical_wire(item, depth + 1) for item in value) + "]"
    require(isinstance(value, dict) and all(isinstance(key, str) for key in value),
            "模型 wire 必须使用 JSON 类型与文本对象键；未派发")
    quoted = {key: _wire_string(key) for key in value}
    keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
    return "{" + ",".join(quoted[key] + ":" + _canonical_wire(value[key], depth + 1) for key in keys) + "}"


def wire_digest(body):
    """Match modeld's JS canonical after JSON.parse, including binary64 and UTF16."""
    payload = _canonical_wire(body).encode("utf-8")
    require(len(payload) <= MAX_EXECUTION_BYTES, "模型 wire 超过有界存储上限；未派发")
    return hashlib.sha256(payload).hexdigest()


class WorkExecutionStore:
    @staticmethod
    def save_loop(cx, loop, request):
        payload = encoded(request)
        cx.execute("CREATE TABLE IF NOT EXISTS work_execution_loops(command_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        cx.execute("INSERT INTO work_execution_loops VALUES(?,?)", (request["id"], payload))
        loop["execution_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def load_loop(cx, loop):
        require(loop.get("execution_sha256"), "原循环缺少可验证命令快照；不能另起循环代替")
        require(cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='work_execution_loops'").fetchone(),
                "原循环命令快照缺失")
        row = cx.execute("SELECT payload FROM work_execution_loops WHERE command_id=?", (loop["command_id"],)).fetchone()
        require(row is not None and hashlib.sha256(row[0].encode("utf-8")).hexdigest() == loop["execution_sha256"]
                and loop["execution_sha256"] == loop["command_sha256"], "原循环命令快照摘要不匹配")
        request = json.loads(row[0])
        require(request["id"] == loop["command_id"] and request["kind"] == "run_loop", "原循环命令身份不匹配")
        return request

    @staticmethod
    def request_snapshot(step, request, plan, wire_body=None):
        """Pure actual encoding for both prefix admission and the original save."""
        if wire_body is not None:
            connection = plan["connection"]
            require(isinstance(wire_body, dict) and wire_body.get("au_id") == request["organization_id"]
                    and wire_body.get("id") == step["model_request_id"]
                    and wire_body.get("run_id") == step["model_request_id"]
                    and wire_body.get("connection_id") == connection["id"]
                    and wire_body.get("connection_revision") == connection["revision"]
                    and wire_body.get("grant_ref") == connection["grant_ref"]
                    and wire_body.get("grant_revision") == connection["grant_revision"]
                    and wire_body.get("model_id") == connection["model"]
                    and wire_body.get("messages") == plan["messages"] and wire_body.get("tools") == plan["tools"]
                    and wire_body.get("generation") == {"maxOutputTokens": connection["max_output_tokens"]},
                    "宿主模型 wire 输入与原 AU、请求、模型授权或消息快照不匹配；未派发")
        wire_payload = _canonical_wire(wire_body).encode('utf-8') if wire_body is not None else None
        request_sha256 = hashlib.sha256(wire_payload).hexdigest() if wire_payload is not None else None
        value = {"request": copy.deepcopy(request), "plan": copy.deepcopy(plan),
                 "model_request_id": step["model_request_id"], "step_ref": step["step_ref"],
                 "attempt_id": step["attempt_id"], "wire_body": copy.deepcopy(wire_body)}
        payload = encoded(value)
        return payload, request_sha256, len(wire_payload or b''), len(payload.encode('utf-8'))

    @classmethod
    def save_request(cls, cx, step, request, plan, wire_body=None):
        payload, request_sha256, wire_bytes, snapshot_bytes = cls.request_snapshot(step, request, plan, wire_body)
        require(wire_bytes <= MAX_EXECUTION_BYTES, '模型 wire 超过有界存储上限；未派发')
        require(snapshot_bytes <= MAX_EXECUTION_BYTES, "原执行快照超过有界存储上限")
        cx.execute("CREATE TABLE IF NOT EXISTS work_execution_requests(step_ref TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        cx.execute("INSERT INTO work_execution_requests VALUES(?,?)", (step["step_ref"], payload))
        step["execution_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        step["request_sha256"] = request_sha256

    @staticmethod
    def _load(cx, table, step, field):
        require(step.get(field) is not None, "原执行缺少可验证私有快照；只能核对原请求，不能重派或采用")
        require(cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone(),
                "原执行私有快照缺失；不能重派或采用")
        row = cx.execute("SELECT payload FROM " + table + " WHERE step_ref=?", (step["step_ref"],)).fetchone()
        require(row is not None and hashlib.sha256(row[0].encode("utf-8")).hexdigest() == step[field],
                "原执行私有快照摘要已变化；不能重派或采用")
        try:
            value = json.loads(row[0])
        except (ValueError, TypeError) as error:
            raise Rejected("原执行私有快照格式无效") from error
        require(value["step_ref"] == step["step_ref"] and value["attempt_id"] == step["attempt_id"]
                and value["model_request_id"] == step["model_request_id"], "原执行私有快照身份不匹配")
        return value

    @classmethod
    def load_request(cls, cx, step):
        value = cls._load(cx, "work_execution_requests", step, "execution_sha256")
        require(hashlib.sha256(encoded(value["request"]).encode("utf-8")).hexdigest() == step["command_sha256"]
                and value["request"]["id"] == step["command_id"]
                and value["plan"]["context_scope"] == step["context_scope"]
                and value["plan"]["connection"] == step["connection"], "原执行命令或授权快照不匹配")
        if value["wire_body"] is not None:
            require(wire_digest(value["wire_body"]) == step["request_sha256"]
                    and value["wire_body"]["id"] == step["model_request_id"]
                    and value["wire_body"]["au_id"] == value["request"]["organization_id"],
                    "原模型输入摘要或范围不匹配")
        return value

    @classmethod
    def save_observed(cls, cx, step, message, usage, *, action_authorized=True):
        value = {"step_ref": step["step_ref"], "attempt_id": step["attempt_id"],
                 "model_request_id": step["model_request_id"], "request_sha256": step.get("request_sha256"),
                 "message": copy.deepcopy(message), "usage": copy.deepcopy(usage),
                 "action_authorized": action_authorized}
        payload = encoded(value)
        require(len(payload.encode("utf-8")) <= MAX_EXECUTION_BYTES, "完整模型观察超过有界存储上限")
        if step.get("observed_sha256"):
            require(cls.load_observed(cx, step) == value, "原完整模型观察已保存，不能覆盖")
            return
        cx.execute("CREATE TABLE IF NOT EXISTS work_execution_observations(step_ref TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        cx.execute("INSERT INTO work_execution_observations VALUES(?,?)", (step["step_ref"], payload))
        step["observed_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def load_observed(cls, cx, step):
        value = cls._load(cx, "work_execution_observations", step, "observed_sha256")
        require(value["request_sha256"] == step.get("request_sha256"), "原完整模型观察的输入摘要不匹配")
        return value
