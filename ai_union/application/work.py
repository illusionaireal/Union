"""Start V1 work through the sole governance transaction; no execution side effects."""
import copy

import hashlib

from ..adapters import documents
from ..adapters.core_au_store import CoreAUStore, encoded
from ..domain import governance, work as rules
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require


class WorkService:
    def __init__(self, app):
        self.app = app
        self.store = app.governance.store

    def read(self, token, au_id):
        try:
            identifier(au_id)
        except (Rejected, TypeError) as error:
            raise CoreError("invalid_request", str(error)) from error
        value = self.app.core_au(token, au_id)
        principal = self.app.creation.principal(self.app.session(token))
        state = value["au"]
        models = state.get("model_access") or {}
        default = (models.get("connections") or {}).get(models.get("default_connection_id") or "")
        can_start = (principal == governance.current(state) and value.get("governance_status") == "active"
                     and default is not None and default["enabled"])
        works = rules.projection(state)
        for item in works:
            item["materials"] = self.materials(item["materials_root"])
        return {"protocol": rules.PROTOCOL, "organization_id": au_id, "version": state["version"],
                "access": {"principal_id": principal, "can_start": can_start},
                "works": works,
                "capabilities": {"work_registration": True, "execution": "not_started",
                                 "autonomous_business": False}}

    def materials(self, reference):
        """Report host availability of the referenced read-only root; never reads content."""
        if reference is None:
            return {"reference": None, "available": False, "documents": 0}
        try:
            listed = documents.list_documents(documents.root_for(self.app.root, reference))
        except (Rejected, CoreError, OSError):
            return {"reference": reference, "available": False, "documents": 0}
        return {"reference": reference, "available": True, "documents": len(listed)}

    def command(self, token, incoming):
        principal = self.app.creation.principal(self.app.session(token))
        request = copy.deepcopy(incoming)
        try:
            governance.exact(request, {"id", "organization_id", "base_version", "kind", "data"})
            identifier(request["id"])
            identifier(request["organization_id"])
            require(type(request["base_version"]) is int and request["base_version"] >= 0, "须提供当前 AU 版本")
            require(isinstance(request["kind"], str) and isinstance(request["data"], dict)
                    and len(encoded(request)) <= 200000, "命令格式无效或过大")
        except (Rejected, TypeError, ValueError) as error:
            raise CoreError("invalid_request", str(error)) from error
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            directory, intent = self.app.governance.locate(request["organization_id"])
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                rules.authorize(state, principal)
                try:
                    rules.validate_input(request["kind"], request["data"])
                except (Rejected, TypeError, ValueError) as error:
                    raise CoreError("invalid_request", str(error)) from error
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
                    "actor_principal_id": principal, "created_at": now(), "status": "succeeded",
                    "effect": "applied", "message": "已登记有责任成员的工作；执行尚未开始"}
                changed = False
                cx.execute("SAVEPOINT work_command")
                try:
                    require(request["base_version"] == state["version"], "AU 版本已变化；请读取最新状态检查原输入")
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    rules.effective(state, principals)
                    local = copy.deepcopy(state)
                    if request["kind"] == "invoke_tool":
                        receipt.update(self.invoke(local, request["data"]))
                        receipt["message"] = "已按该工作的有效授权调用只读资料工具并留存回执；未调用模型"
                    elif request["kind"] == "submit_result":
                        receipt["result"] = rules.submit_result(local, request["data"], principal)
                        receipt["message"] = "已登记候选成果与来源；尚未采用"
                    elif request["kind"] == "adopt_result":
                        receipt["result"] = rules.adopt_result(local, request["data"], principal)
                        receipt["message"] = "已采用该成果并记录采用人"
                    elif request["kind"] == "reserve_step":
                        receipt["step"] = rules.reserve_step(local, request["data"])
                        receipt["message"] = "已为该次执行预约一次调用；尚未调用模型"
                    elif request["kind"] == "settle_step":
                        receipt["step"] = rules.settle_step(local, request["data"])
                        receipt["message"] = "已结算该次步进"
                    elif request["kind"] == "start_attempt":
                        receipt["attempt"] = rules.start_attempt(local, request["data"], principal)
                        receipt["message"] = "已开始一次执行尝试；尚未调用模型"
                    elif request["kind"] == "finish_attempt":
                        receipt["attempt"] = rules.finish_attempt(local, request["data"])
                        receipt["message"] = "已结束该次执行尝试并记录结果类别"
                    else:
                        receipt.update(rules.apply(local, charter, request["kind"], request["data"], principal,
                                                   request["id"]))
                    local["version"] = state["version"] + 1
                    state = local
                    changed = True
                except Rejected as error:
                    cx.execute("ROLLBACK TO work_command")
                    receipt.update(status="rejected", effect="none", message=str(error))
                cx.execute("RELEASE work_command")
                receipt["version"] = state["version"]
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=changed)
        return receipt

    def invoke(self, state, data):
        """Run one authorized read-only tool through the host adapter; no model call."""
        work, _mandate, attempt = rules.tool_target(state, data)
        root = documents.root_for(self.app.root, work["materials_root"])
        if data["tool"] == "list_documents":
            listed = documents.list_documents(root)
            result, detail = {"documents": listed}, {"count": len(listed)}
        else:
            text_value, digest, size = documents.read_text(root, data["arguments"]["path"])
            result, detail = {"text": text_value, "sha256": digest, "bytes": size}, {"sha256": digest, "bytes": size}
        entry = rules.record_tool_call(work, data["tool"], data["arguments"], detail, attempt["id"])
        return {"tool_call": entry, "result": result}

    def result_content(self, token, au_id, result_id):
        """Read one adopted or candidate result body; the digest is re-checked on read."""
        try:
            identifier(au_id)
            identifier(result_id)
        except (Rejected, TypeError) as error:
            raise CoreError("invalid_request", str(error)) from error
        value = self.app.core_au(token, au_id)
        for work in rules.records(value["au"])["works"].values():
            for result in work.get("results") or []:
                if result["id"] != result_id:
                    continue
                digest = hashlib.sha256(result["content"].encode("utf-8")).hexdigest()
                if digest != result["sha256"]:
                    raise CoreError("incompatible_state", "成果正文与登记摘要不一致；不能作为正式成果读取")
                return {"protocol": rules.PROTOCOL, "organization_id": au_id,
                        "result": {key: item for key, item in result.items() if key != "content"},
                        "content": result["content"]}
        raise CoreError("invalid_request", "此 AU 中没有该成果标识")
