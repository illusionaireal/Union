"""Persisted two-step tool verification; one model attempt, one dispatcher."""
import copy
import re
import time
import uuid
from urllib.parse import urlencode

from ..adapters.model_access_store import ModelAccessStore as Private
from ..domain import model_checks as rules
from ..errors import Rejected, require
from ..model_billing import calculate
from ..model_service import ServiceError
from ..model_diagnostics import failure, safe_code
from ..tool_roundtrip import complete_reply, complete_tool_call


class AuthorizationChanged(Rejected):
    pass


class ModelRefused(Rejected):
    def __init__(self, code, status=None):
        self.details = failure(code, status)
        super().__init__(self.details["message"])


def usage_from(remote):
    events = remote.get("events", [])
    basis = "unknown"
    result = {"input_tokens": None, "output_tokens": None, "cached_input_tokens": None,
              "cache_write_tokens": None, "reasoning_tokens": None}
    token_fields = tuple(result)
    metadata, charge = {}, {}

    def merge(usage, source):
        nonlocal basis
        if not isinstance(usage, dict):
            return
        accepted = False
        for key in token_fields:
            value = usage.get(key)
            if type(value) is int and value >= 0:
                result[key] = value
                accepted = True
        # Amount and currency are one observation, never independent patches.
        if (type(usage.get("cost_minor")) is int and usage["cost_minor"] >= 0
                and isinstance(usage.get("currency"), str) and re.fullmatch(r"[A-Z]{3}", usage["currency"])):
            charge.update(cost_minor=usage["cost_minor"], currency=usage["currency"],
                          cost_status="provider_reported", cost_basis="metered")
            accepted = True
        for key in ("account_ref", "resolved_model"):
            if isinstance(usage.get(key), str):
                metadata[key] = usage[key]
        if accepted:
            basis = source

    for event in events:
        if event.get("type") == "usage":
            merge(event.get("payload"), "events")
    merge((remote.get("result") or {}).get("usage"), "result")
    result.update(calculate(None, result))
    result.update(charge)
    result.update(source="modeld", basis=basis, observed_through_seq=max((event["seq"] for event in events), default=0),
                  account_ref=metadata.get("account_ref"), resolved_model=metadata.get("resolved_model"))
    return result


class ModelCheckRunner:
    def __init__(self, service):
        self.service = service

    @staticmethod
    def guard(state, charter, check, principals):
        try:
            return rules.authority(state, charter, check, time.time(), principals)
        except Rejected as error:
            raise AuthorizationChanged(str(error)) from error

    def model_grant(self, client, au_id, config):
        try:
            return self.service.check_grant(client, au_id, config)
        except Rejected as error:
            raise AuthorizationChanged(str(error)) from error

    def run(self, au_id, check_id):
        service = self.service
        original = service.state(au_id)["model_access"]["checks"][check_id]
        principal = original["principal_id"]
        try:
            client = service.backend()
            while True:
                state = service.state(au_id)
                check = state["model_access"]["checks"][check_id]
                if check["status"] == "succeeded":
                    return
                stage = check["stage"]
                require(stage in (0, 1), "原模型阶段不支持继续")
                config = state["model_access"]["connections"][check["connection_id"]]
                if stage >= len(check["attempt_ids"]):
                    self.model_grant(client, au_id, config)
                    if service.stopping:
                        raise ServiceError("host_stopped_before_next_attempt")
                    service.mutate(au_id, principal, "attempt_reserved", lambda s, c, cx, ps: self.reserve(s, c, cx, ps, check_id))
                    check = service.state(au_id)["model_access"]["checks"][check_id]
                attempt_id = check["attempt_ids"][stage]
                if check["attempts"][stage]["state"] == "prepared":
                    self.model_grant(client, au_id, config)
                    body = service.mutate(au_id, principal, "attempt_dispatching",
                        lambda s, c, cx, ps: self.dispatch(s, c, cx, ps, check_id, stage))
                    try:
                        client.call("POST", "/v1/requests", body)
                    except ServiceError as error:
                        if error.status in (400, 401, 403, 404, 405, 413, 422):
                            raise ModelRefused(error.code, error.status) from error
                        # The original ID is the only permitted recovery path.
                remote = self.collect(client, au_id, check_id, attempt_id, state["resources"]["timeout_seconds"])
                if remote["state"] == "failed":
                    raise ModelRefused(remote.get("error"))
                if remote["state"] != "completed":
                    raise ServiceError(safe_code(remote.get("error")))
                if remote.get("action_authorized") is False:
                    raise AuthorizationChanged("模型服务授权已失效；原结果仅供费用核对")
                self.model_grant(client, au_id, config)
                service.mutate(au_id, principal, "tool_accepted" if stage == 0 else "check_accepted",
                    lambda s, c, cx, ps: self.accept(s, c, cx, ps, check_id, stage, remote))
        except (ServiceError, Rejected, OSError, ValueError, TypeError, KeyError) as error:
            status = "not_adopted" if isinstance(error, AuthorizationChanged) else "unknown" if isinstance(error, (ServiceError, OSError)) else "failed"
            if isinstance(error, ModelRefused):
                details = error.details
            elif isinstance(error, AuthorizationChanged):
                details = failure("authorization_changed") | {"message": str(error)}
            elif isinstance(error, Rejected):
                details = failure("invalid_model_result") | {"message": str(error)}
            else:
                details = failure(error.code, error.status) if isinstance(error, ServiceError) else failure()
            def record(state, charter, cx, principals):
                check = state["model_access"]["checks"][check_id]
                check.update(status=status, **details)
                if check["attempts"]:
                    check["attempts"][-1]["diagnostic"] = copy.deepcopy(details["diagnostic"])
                if check["attempts"] and check["attempts"][-1]["state"] == "dispatching":
                    check["attempts"][-1]["state"] = status
            service.mutate(au_id, principal, "check_unconfirmed", record)

    def reserve(self, state, charter, cx, principals, check_id):
        check = state["model_access"]["checks"][check_id]
        config = self.guard(state, charter, check, principals)
        stage = check["stage"]
        require(stage == len(check["attempt_ids"]) and stage < 2, "原调用已预约，不能重复创建")
        attempt_id = "model-" + uuid.uuid5(uuid.NAMESPACE_URL, state["id"] + ":" + check_id + ":" + str(stage)).hex
        if stage == 0:
            messages = [{"role": "system", "content": check["agent_definition"]["instructions"]},
                        {"role": "user", "content": "验证指定模型连接。请读取资料 " + check["document_name"] + "，document_id=" + check_id}]
            tools = [{"type": "function", "function": {"name": "read_document", "description": "只读本次验证已明确选择并保存的资料，不访问其他宿主文件。",
                "parameters": {"type": "object", "properties": {"document_id": {"type": "string", "enum": [check_id]}},
                               "required": ["document_id"], "additionalProperties": False}}}]
        else:
            first = Private.attempt(cx, check["attempt_ids"][0])
            messages = first["payload"]["messages"] + [first["result"]["result"]["message"], Private.tool_message(cx, check_id)]
            tools = []
        body = {"id": attempt_id, "run_id": attempt_id, "au_id": state["id"], "connection_id": config["id"],
            "connection_revision": config["revision"], "grant_ref": config["grant_ref"], "grant_revision": config["grant_revision"],
            "model_id": config["model"], "messages": copy.deepcopy(messages), "tools": tools,
            "generation": {"maxOutputTokens": config["max_output_tokens"]},
            "deadlines": {"first_event_ms": 180000, "idle_ms": 120000, "task_ms": state["resources"]["timeout_seconds"] * 1000}}
        Private.reserve(cx, check_id, body)
        check["attempt_ids"].append(attempt_id)
        check["attempts"].append({"id": attempt_id, "stage": stage, "state": "prepared", "purpose": "connection_check", "usage": usage_from({})})
        check.update(status="running", message="正在调用模型；刷新不会重复派发", diagnostic=None)

    def dispatch(self, state, charter, cx, principals, check_id, stage):
        check = state["model_access"]["checks"][check_id]
        self.guard(state, charter, check, principals)
        if self.service.stopping:
            raise ServiceError("host_stopped_before_dispatch")
        require(check["attempts"][stage]["state"] == "prepared", "原请求不能再次派发")
        check["attempts"][stage]["state"] = "dispatching"
        return Private.attempt(cx, check["attempt_ids"][stage])["payload"]

    def collect(self, client, au_id, check_id, attempt_id, timeout):
        deadline = time.monotonic() + timeout
        directory, _ = self.service.app.governance.locate(au_id)
        with self.service.store.transaction(directory) as cx:
            previous = Private.attempt(cx, attempt_id)["result"]
        events = copy.deepcopy((previous or {}).get("events", []))
        known_events = {item["seq"]: item for item in events}
        cursor = max((item["seq"] for item in events), default=0)

        def persist(remote, complete):
            nonlocal previous
            observation = remote | {"events": events, "events_complete": complete}
            if observation != previous:
                check = self.service.state(au_id)["model_access"]["checks"][check_id]
                previous = self.service.mutate(au_id, check["principal_id"], "attempt_observed",
                    lambda state, charter, cx, principals: self.observe(state, cx, check_id,
                        check["attempt_ids"].index(attempt_id), observation))
            return previous

        while True:
            remote = client.request(attempt_id, au_id)
            require(remote.get("id") == attempt_id and remote.get("au_id") == au_id, "原模型回执范围不匹配")
            if remote.get("error") is not None:
                remote["error"] = safe_code(remote["error"])
            try:
                while True:
                    page = client.events(attempt_id, au_id, cursor).get("events", [])
                    require(isinstance(page, list), "原模型事件格式无效")
                    before_page = cursor
                    for item in page:
                        require(isinstance(item, dict) and item.get("request_id") == attempt_id
                                and type(item.get("seq")) is int and item["seq"] > 0, "原模型事件范围或顺序无效")
                        if item["seq"] in known_events:
                            require(known_events[item["seq"]] == item, "同一模型事件序号的原内容发生冲突")
                            continue
                        require(item["seq"] > cursor, "原模型事件范围或顺序无效")
                        events.append(item)
                        known_events[item["seq"]] = item
                        cursor = item["seq"]
                    persist(remote, len(page) < 500)
                    if len(page) < 500:
                        break
                    require(cursor > before_page, "原模型事件分页未前进")
            except (ServiceError, Rejected, ValueError, TypeError):
                # A later invalid/failed event does not erase the valid prefix.
                persist(remote, False)
                raise
            if remote.get("state") in ("completed", "failed", "interrupted"):
                return previous
            check = self.service.state(au_id)["model_access"]["checks"][check_id]
            if check["stop_requested"] or self.service.stopping or time.monotonic() >= deadline:
                try:
                    client.call("POST", "/v1/requests/" + attempt_id + "/cancel?" + urlencode({"au_id": au_id}), {})
                except ServiceError:
                    pass
                raise ServiceError("local_wait_stopped_remote_unknown")
            time.sleep(0.05)

    @staticmethod
    def observe(state, cx, check_id, stage, remote):
        check = state["model_access"]["checks"][check_id]
        observed = Private.observe(cx, check["attempt_ids"][stage], remote)
        check["attempts"][stage].update(state=observed["state"], usage=usage_from(observed))
        return observed

    def accept(self, state, charter, cx, principals, check_id, stage, remote):
        check = state["model_access"]["checks"][check_id]
        self.guard(state, charter, check, principals)
        require(remote["state"] == "completed" and remote.get("action_authorized") is not False, "原结果无当前使用资格")
        message = remote["result"]["message"]
        if stage == 0:
            call = complete_tool_call(message, "read_document", {"document_id": check_id})
            Private.tool_result(cx, check_id, call)
            check.update(stage=1, message="已读取所选资料；将原工具结果交回模型")
        else:
            material = Private.material(cx, check_id)
            output = complete_reply(message, material["challenge"])
            check.update(stage=2, status="succeeded", output=output, message="模型已读取工具结果并完成回应；不代表任意目标自主工作", waiting=None, diagnostic=None)
            connection = state["model_access"]["connections"][check["connection_id"]]
            connection["last_check"] = {"check_id": check_id, "revision": connection["revision"], "profile": connection["profile"], "at": time.time()}
            work = state["work"][check["work_id"]]
            work.update(status="delivered", version=work["version"] + 1)
