"""Private model turns in the caller's sole AU transaction; never a public view."""
import copy
import hashlib
import json

from .core_au_store import encoded
from ..errors import Rejected, require


MAX_CONTEXT_BYTES = 4 * 1024 * 1024


class WorkContextStore:
    @staticmethod
    def load(cx, work, scope):
        messages, sources, bindings = [], [], []
        has_table = cx.execute("SELECT 1 FROM sqlite_master WHERE name='work_model_turns' AND type='table'").fetchone()
        for step in work.get("steps") or []:
            digest = step.get("context_sha256")
            if digest is None:
                require(step["status"] != "used" or step.get("model_outcome") == "not_adoptable",
                        "原模型步进缺少可恢复上下文；请核对原记录，不能重读资料代替")
                continue
            require(has_table is not None, "原模型上下文缺失；不能重新派发")
            row = cx.execute("SELECT payload FROM work_model_turns WHERE step_ref=?", (step["step_ref"],)).fetchone()
            require(row is not None and hashlib.sha256(row[0].encode("utf-8")).hexdigest() == digest,
                    "原模型上下文缺失或摘要已改变；不能重新派发")
            try:
                value = json.loads(row[0])
            except (ValueError, TypeError) as error:
                raise Rejected("原模型上下文无效；不能重新派发") from error
            require(value["scope"] == scope and value["step_ref"] == step["step_ref"]
                    and value["attempt_id"] == step["attempt_id"], "原模型上下文的工作、身份或权限版本已变化")
            messages.extend(value["messages"])
            sources.extend(value["sources"])
            if value.get("materials_binding") is not None:
                bindings.append(value["materials_binding"])
        require(len(encoded(messages).encode("utf-8")) <= MAX_CONTEXT_BYTES,
                "原模型上下文超过本核心允许的大小；请保留原记录并缩小后续工作范围")
        return copy.deepcopy(messages), list(dict.fromkeys(sources)), bindings

    @staticmethod
    def save(cx, step, scope, messages, sources, materials_binding=None):
        payload = encoded({"scope": scope, "step_ref": step["step_ref"], "attempt_id": step["attempt_id"],
                           "messages": messages, "sources": sources, "materials_binding": materials_binding})
        cx.execute("CREATE TABLE IF NOT EXISTS work_model_turns(step_ref TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        cx.execute("INSERT INTO work_model_turns VALUES(?,?)", (step["step_ref"], payload))
        step["context_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
