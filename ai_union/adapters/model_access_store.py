"""Private request/material storage. GovernanceStore alone writes AU facts."""
import hashlib
import json

from .core_au_store import encoded
from ..errors import require


def request_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


class ModelAccessStore:
    @staticmethod
    def initialize(cx):
        cx.execute("CREATE TABLE IF NOT EXISTS model_attempts(id TEXT PRIMARY KEY, check_id TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, result TEXT)")
        cx.execute("CREATE TABLE IF NOT EXISTS model_materials(check_id TEXT PRIMARY KEY, name TEXT NOT NULL, content TEXT NOT NULL, sha256 TEXT NOT NULL, challenge TEXT NOT NULL)")
        cx.execute("CREATE TABLE IF NOT EXISTS model_tool_receipts(check_id TEXT PRIMARY KEY, call_id TEXT NOT NULL, arguments TEXT NOT NULL, result TEXT NOT NULL)")

    @staticmethod
    def validate(cx, state):
        tables = {row[0] for row in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require({"model_attempts", "model_materials", "model_tool_receipts"} <= tables, "模型私有记录不完整")
        checks = state["model_access"]["checks"]
        for row in cx.execute("SELECT id,check_id,payload,digest FROM model_attempts"):
            payload = json.loads(row[2])
            require(row[1] in checks and row[0] in checks[row[1]]["attempt_ids"] and payload["id"] == row[0]
                    and payload["au_id"] == state["id"] and request_digest(payload) == row[3], "原模型意图身份或摘要不一致")

    @staticmethod
    def material(cx, check_id):
        row = cx.execute("SELECT name,content,sha256,challenge FROM model_materials WHERE check_id=?", (check_id,)).fetchone()
        require(row is not None and hashlib.sha256(row[1].encode("utf-8")).hexdigest() == row[2], "原资料缺失或摘要已改变")
        return {"document_id": check_id, "name": row[0], "content": row[1], "sha256": row[2], "challenge": row[3]}

    @staticmethod
    def save_material(cx, check_id, name, content, challenge):
        cx.execute("INSERT INTO model_materials VALUES(?,?,?,?,?)", (check_id, name, content, hashlib.sha256(content.encode("utf-8")).hexdigest(), challenge))

    @staticmethod
    def attempt(cx, attempt_id):
        row = cx.execute("SELECT payload,digest,result FROM model_attempts WHERE id=?", (attempt_id,)).fetchone()
        require(row is not None, "原模型请求不存在")
        return {"payload": json.loads(row[0]), "digest": row[1], "result": json.loads(row[2]) if row[2] else None}

    @staticmethod
    def reserve(cx, check_id, body):
        cx.execute("INSERT INTO model_attempts VALUES(?,?,?,?,NULL)", (body["id"], check_id, encoded(body), request_digest(body)))

    @staticmethod
    def observe(cx, attempt_id, remote):
        prior = ModelAccessStore.attempt(cx, attempt_id)
        require(remote.get("id") == attempt_id and remote.get("au_id") == prior["payload"]["au_id"]
                and remote.get("request_digest") == prior["digest"], "原模型回执身份或请求摘要不匹配")
        events = {item["seq"]: item for item in (prior["result"] or {}).get("events", [])}
        for item in remote.get("events", []):
            require(isinstance(item, dict) and item.get("request_id") == attempt_id
                    and type(item.get("seq")) is int and item["seq"] > 0, "原模型事件身份或序号无效")
            require(item["seq"] not in events or events[item["seq"]] == item, "同一模型事件序号的原内容发生冲突")
            events[item["seq"]] = item
        observed = remote | {"events": [events[key] for key in sorted(events)]}
        previous_result = (prior["result"] or {}).get("result")
        if previous_result is not None:
            require(remote.get("result") is None or remote["result"] == previous_result, "原模型结果内容发生冲突")
            observed["result"] = previous_result
        cx.execute("UPDATE model_attempts SET result=? WHERE id=?", (encoded(observed), attempt_id))
        return observed

    @staticmethod
    def tool_result(cx, check_id, call):
        previous = cx.execute("SELECT call_id,arguments,result FROM model_tool_receipts WHERE check_id=?", (check_id,)).fetchone()
        if previous:
            require(previous[0] == call["id"] and previous[1] == call["function"]["arguments"], "工具回执身份或参数冲突")
            return json.loads(previous[2])
        result = ModelAccessStore.material(cx, check_id)
        cx.execute("INSERT INTO model_tool_receipts VALUES(?,?,?,?)", (check_id, call["id"], call["function"]["arguments"], encoded(result)))
        return result

    @staticmethod
    def tool_message(cx, check_id):
        row = cx.execute("SELECT call_id,result,arguments FROM model_tool_receipts WHERE check_id=?", (check_id,)).fetchone()
        require(row is not None, "缺少原工具回执，不能重跑工具以掩盖缺口")
        material = ModelAccessStore.material(cx, check_id)
        require(row[1] == encoded(material) and json.loads(row[2]) == {"document_id": check_id}, "原工具回执内容或参数完整性校验失败")
        first = cx.execute("SELECT result FROM model_attempts WHERE check_id=? ORDER BY rowid LIMIT 1", (check_id,)).fetchone()
        require(first and first[0], "缺少原模型工具调用依据")
        from ..tool_roundtrip import complete_tool_call
        call = complete_tool_call(json.loads(first[0])["result"]["message"], "read_document", {"document_id": check_id})
        require(call["id"] == row[0] and call["function"]["arguments"] == row[2], "工具回执与原模型调用不匹配")
        return {"role": "tool", "name": "read_document", "tool_call_id": row[0], "content": row[1]}
