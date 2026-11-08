"""Start V1 work through the sole governance transaction; no execution side effects."""
import copy

import hashlib
import json

from ..adapters import documents
from ..adapters.core_au_store import CoreAUStore, encoded
from ..adapters.work_context_store import WorkContextStore
from ..domain import governance, work as rules
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require
from ..work_transport import UnadoptableWorkResult


class WorkService:
    def __init__(self, app):
        self.app = app
        self.store = app.governance.store
        self.transport = None
        self.transport_factory = None

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
        works = rules.projection(state, instance=self.app.instance)
        for item in works:
            item["materials"] = self.materials(item["materials_root"])
        usage = {"input_tokens": 0, "output_tokens": 0}
        for item in works:
            for key in usage:
                usage[key] += item["usage"][key]
        return {"protocol": rules.PROTOCOL, "organization_id": au_id, "version": state["version"],
                "access": {"principal_id": principal, "can_start": can_start},
                "works": works, "usage": usage, "cost_status": "unknown",
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
        if isinstance(incoming, dict) and incoming.get("kind") == "run_step":
            return self.run_step(token, incoming)
        if isinstance(incoming, dict) and incoming.get("kind") == "run_loop":
            return self.run_loop(token, incoming)
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
                    elif request["kind"] == "deliver_work":
                        receipt["work"] = rules.deliver_work(local, request["data"], principal)
                        receipt["message"] = "已按采用的成果把该工作记为完成"
                    elif request["kind"] == "adopt_result":
                        receipt["result"] = rules.adopt_result(local, request["data"], principal)
                        receipt["message"] = "已采用该成果并记录采用人"
                    elif request["kind"] == "reconcile_step":
                        receipt["step"] = rules.reconcile_step(local, request["data"])
                        receipt["message"] = "已按核对结果处理该次未知步进"
                    elif request["kind"] == "reserve_step":
                        receipt["step"] = rules.reserve_step(local, request["data"], instance=self.app.instance)
                        receipt["message"] = "已为该次执行预约一次调用；尚未调用模型"
                    elif request["kind"] == "settle_step":
                        receipt["step"] = rules.settle_step(local, request["data"])
                        receipt["message"] = "已结算该次步进"
                    elif request["kind"] == "start_attempt":
                        receipt["attempt"] = rules.start_attempt(local, request["data"], principal,
                                                                  instance=self.app.instance)
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
        work, _mandate, attempt = rules.tool_target(state, data, instance=self.app.instance)
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

    def run_step(self, token, incoming):
        """One automatic model turn: decide outside the lock, apply inside one transaction."""
        principal = self.app.creation.principal(self.app.session(token))
        request = copy.deepcopy(incoming)
        try:
            governance.exact(request, {"id", "organization_id", "base_version", "kind", "data"})
            identifier(request["id"])
            identifier(request["organization_id"])
            require(type(request["base_version"]) is int and request["base_version"] >= 0, "须提供当前 AU 版本")
            rules.validate_input(request["kind"], request["data"])
        except (Rejected, TypeError, ValueError) as error:
            raise CoreError("invalid_request", str(error)) from error
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            directory, intent = self.app.governance.locate(request["organization_id"])
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                rules.authorize(state, principal)
                require(request["base_version"] == state["version"], "AU 版本已变化；请读取最新状态检查原输入")
                try:
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    rules.effective(state, principals)
                    plan = rules.step_plan(state, state["charter"], request["data"]["work_id"],
                                           instance=self.app.instance)
                    work = rules.records(state)["works"][plan["work_id"]]
                    history, plan["sources"], bindings = WorkContextStore.load(cx, work, plan["context_scope"])
                    if any(item["role"] == "tool" for item in history):
                        root = documents.root_for(self.app.root, plan["materials_root"])
                        binding = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
                        require(bindings and all(item == binding for item in bindings),
                                "宿主资料目录绑定已变化；原上下文不可继续派发")
                    plan["messages"].extend(history)
                except Rejected as error:
                    plan = None
                    refusal = str(error)
            if plan is None:
                return self.reject_step(directory, intent, request, principal, refusal)
        transport = getattr(self, "transport", None)
        if transport is None:
            factory = getattr(self, "transport_factory", None)
            if factory is not None:
                try:
                    transport = factory(request["organization_id"], plan.get("connection"))
                except Rejected as error:
                    return self.reject_step(directory, intent, request, principal,
                                            "宿主未能建立模型通道：" + str(error)[:280])
                except Exception as error:  # noqa: BLE001 - a channel that cannot be built never ran anything
                    return self.reject_step(directory, intent, request, principal,
                                            "宿主建立模型通道失败：" + str(error)[:280])
        if transport is None or not hasattr(transport, "chat"):
            return self.reject_step(directory, intent, request, principal, "宿主尚未配置模型执行通道；请先在宿主接入模型通道")
        try:
            message, usage = transport.chat(copy.deepcopy(plan["package"]), copy.deepcopy(plan["messages"]),
                                            copy.deepcopy(plan["tools"]))
        except UnadoptableWorkResult as error:
            return self.record_channel_outcome(directory, intent, request, principal, str(error), completed=error)
        except Rejected as error:
            return self.reject_step(directory, intent, request, principal,
                                    "模型通道拒绝本次请求；本轮未执行，未产生步进事实：" + str(error)[:280])
        except Exception as error:  # noqa: BLE001 - an unconfirmed call keeps a reservation to reconcile
            return self.record_channel_outcome(directory, intent, request, principal,
                                     "模型通道结果未知；已保留该次调用预约等待核对，不自动重放：" + str(error)[:280])
        calls = (message or {}).get("tool_calls") or []
        if calls and plan["materials_root"] is None:
            return self.reject_step(directory, intent, request, principal, "模型请求只读工具，但该工作未绑定授权资料目录")
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                rules.authorize(state, principal)
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
                    "actor_principal_id": principal, "created_at": now(), "status": "succeeded",
                    "effect": "applied", "message": "已执行一次自动模型步进"}
                changed = False
                cx.execute("SAVEPOINT work_step")
                try:
                    require(request["base_version"] == state["version"], "AU 版本已变化；请读取最新状态检查原输入")
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    rules.effective(state, principals)
                    local = copy.deepcopy(state)
                    work = rules.records(local)["works"][request["data"]["work_id"]]
                    current_plan = rules.step_plan(local, charter, work["id"], instance=self.app.instance)
                    assistant, parsed_calls = self.model_turn(message, current_plan)
                    require(len(work.get("tool_calls") or []) + len(parsed_calls) <= rules.MAX_TOOL_CALLS,
                            "该工作的工具调用回执已达上限")
                    content = assistant["content"] or ""
                    executed = []
                    outputs = []
                    for call, arguments in parsed_calls:
                        name = call["function"]["name"]
                        rules.tool_target(local, {"work_id": work["id"], "tool": name}, self.app.instance)
                        if name == "list_documents":
                            root = documents.root_for(self.app.root, work["materials_root"])
                            listed = documents.list_documents(root)
                            executed.append({"tool": name, "arguments": {},
                                             "count": len(listed)})
                            outputs.append({"documents": listed, "count": len(listed)})
                        elif name == "read_document":
                            root = documents.root_for(self.app.root, work["materials_root"])
                            text, digest, size = documents.read_text(root, arguments.get("path"))
                            executed.append({"tool": name, "arguments": {"path": arguments.get("path")},
                                             "sha256": digest, "bytes": size})
                            outputs.append({"path": arguments["path"], "content": text, "sha256": digest, "bytes": size})
                        else:
                            raise Rejected("模型请求了本核心不支持的只读工具")
                    payload = {"work_id": request["data"]["work_id"], "content": "" if parsed_calls else content,
                               "tool_calls": executed, "sources": plan["sources"],
                               "result_id": "result-" + request["id"].replace("-", "")[:12],
                               "title": "自动成果：" + work["title"], "usage": usage if isinstance(usage, dict) else {}}
                    receipt.update(rules.apply_step(local, charter, payload, principal, self.app.instance))
                    turn_messages = [assistant]
                    new_receipts = work.get("tool_calls", [])[-len(outputs):] if outputs else []
                    for (call, _), output, tool_receipt in zip(parsed_calls, outputs, new_receipts):
                        turn_messages.append({"role": "tool", "name": call["function"]["name"],
                                              "tool_call_id": call["id"],
                                              "content": encoded(output | {"step_ref": tool_receipt["step_ref"]})})
                    WorkContextStore.save(cx, work["steps"][-1], current_plan["context_scope"], turn_messages,
                                          [item["step_ref"] for item in new_receipts],
                                          hashlib.sha256(str(root).encode("utf-8")).hexdigest() if outputs else None)
                    local["version"] = state["version"] + 1
                    state = local
                    changed = True
                except Rejected as error:
                    cx.execute("ROLLBACK TO work_step")
                    receipt.update(status="rejected", effect="none", message=str(error))
                cx.execute("RELEASE work_step")
                receipt["version"] = state["version"]
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=changed)
        return receipt

    @staticmethod
    def model_turn(message, plan):
        """Validate the complete batch before a read; retain only protocol fields."""
        require(isinstance(message, dict), "模型结果不是完整消息")
        content = message.get("content")
        require(content is None or isinstance(content, str), "模型正文须为文本")
        calls = message.get("tool_calls") or []
        require(isinstance(calls, list) and len(calls) <= 10, "模型工具批次须完整且至多 10 项")
        allowed = {item["function"]["name"] for item in plan["tools"]}
        normalized, parsed, ids = [], [], set()
        for call in calls:
            require(isinstance(call, dict) and isinstance(call.get("id"), str)
                    and 0 < len(call["id"]) <= 256 and call["id"] not in ids
                    and call.get("type") == "function", "模型工具调用标识缺失、重复或类型无效")
            function = call.get("function")
            require(isinstance(function, dict) and function.get("name") in allowed
                    and isinstance(function.get("arguments"), str), "模型工具不在当前允许范围或参数无效")
            try:
                arguments = json.loads(function["arguments"])
            except ValueError as error:
                raise Rejected("模型工具参数不是合法 JSON") from error
            keys = {"path"} if function["name"] == "read_document" else set()
            require(isinstance(arguments, dict) and set(arguments) == keys, "模型工具参数不符合只读工具契约")
            if keys:
                require(isinstance(arguments["path"], str), "资料路径须为文本")
            value = {"id": call["id"], "type": "function", "function": {
                "name": function["name"], "arguments": function["arguments"]}}
            ids.add(call["id"])
            normalized.append(value)
            parsed.append((value, arguments))
        assistant = {"role": "assistant", "content": content, "tool_calls": normalized}
        if message.get("_native") is not None:
            require(isinstance(message["_native"], dict)
                    and message["_native"].get("au_id") == plan["context_scope"]["au_id"],
                    "模型原生上下文不属于当前 AU")
            assistant["_native"] = copy.deepcopy(message["_native"])
        return assistant, parsed

    def run_loop(self, token, incoming):
        """Drive automatic turns until the model answers or the turn cap is reached."""
        principal = self.app.creation.principal(self.app.session(token))
        request = copy.deepcopy(incoming)
        try:
            governance.exact(request, {"id", "organization_id", "base_version", "kind", "data"})
            identifier(request["id"])
            identifier(request["organization_id"])
            require(type(request["base_version"]) is int and request["base_version"] >= 0, "须提供当前 AU 版本")
            rules.validate_input(request["kind"], request["data"])
        except (Rejected, TypeError, ValueError) as error:
            raise CoreError("invalid_request", str(error)) from error
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            directory, intent = self.app.governance.locate(request["organization_id"])
            with self.store.transaction(directory) as cx:
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                current = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                work = rules.records(current)["works"].get(request["data"]["work_id"])
                require(work is not None, "工作不存在或不属于此 AU")
                remaining = work["max_calls"] - rules.budget(work)["reserved"] - rules.budget(work)["used"]
                require(remaining > 0, "该工作的调用上限已用尽")
                turn_cap = min(3, remaining)
        version = request["base_version"]
        turns = 0
        tool_calls = 0
        produced = False
        usage_total = {"input_tokens": 0, "output_tokens": 0}
        status = "succeeded"
        model_outcome = None
        message = "自动循环结束：模型没有给出成果，已用满本轮轮次"
        for index in range(turn_cap):
            step_request = {"id": request["id"] + "-t" + str(index + 1),
                            "organization_id": request["organization_id"], "base_version": version,
                            "kind": "run_step", "data": dict(request["data"])}
            step = self.run_step(token, step_request)
            if step.get("status") != "succeeded":
                status = step.get("status", "rejected")
                message = step.get("message", "自动循环被拒绝")
                break
            if step.get("model_outcome") == "unknown":
                status = "unknown"
                message = "自动循环在模型结果未知时停止；已保留该次调用预约等待核对，不自动重放"
                break
            turns += 1
            tool_calls += int(step.get("tool_calls") or 0)
            for key in usage_total:
                usage_total[key] += int((step.get("usage") or {}).get(key) or 0)
            if step.get("model_outcome") == "not_adoptable":
                status, model_outcome = "rejected", "not_adoptable"
                message = step["message"]
                version = step["version"]
                break
            if step.get("result"):
                produced = True
                message = "自动循环结束：已产出候选成果"
                break
            version = int(step.get("version") or version + 1)
        receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
            "actor_principal_id": principal, "created_at": now(), "status": status,
            "effect": "applied" if turns else "none", "message": message, "turns": turns,
            "tool_calls": tool_calls, "result": produced, "version": version,
            "usage": usage_total, "cost_status": "unknown"}
        if status == "unknown":
            receipt["model_outcome"] = "unknown"
        elif model_outcome is not None:
            receipt["model_outcome"] = model_outcome
        return self.store_receipt(directory, intent, request, principal, receipt)

    def record_channel_outcome(self, directory, intent, request, principal, message, *, completed=None):
        """Keep unknown calls reserved, and completed unadoptable calls used."""
        with self.app.mutex:
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                rules.authorize(state, principal)
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                local = copy.deepcopy(state)
                data = {"work_id": request["data"]["work_id"], "reason": message}
                if completed is None:
                    details = rules.fail_step(local, data, instance=self.app.instance)
                    details = {"step": details["step"], "model_outcome": "unknown"}
                else:
                    details = rules.record_unadoptable_step(local, data | {
                        "model_request_id": completed.request_id, "usage": completed.usage}, instance=self.app.instance)
                local["version"] = state["version"] + 1
                state = local
                receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
                    "actor_principal_id": principal, "created_at": now(), "status": "succeeded",
                    "effect": "applied", "message": message, **details,
                    "tool_calls": 0, "result": False, "version": state["version"], "cost_status": "unknown"}
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=True)
        return receipt

    def store_receipt(self, directory, intent, request, principal, receipt):
        """Persist only the receipt of this request; AU facts stay untouched."""
        with self.app.mutex:
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=False)
        return receipt

    def reject_step(self, directory, intent, request, principal, message):
        """Record a refused step without changing AU facts (the model was not credited)."""
        state = None
        with self.app.mutex:
            with self.store.transaction(directory) as cx:
                current = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                state = current["version"]
        receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
            "actor_principal_id": principal, "created_at": now(), "status": "rejected",
            "effect": "none", "message": message, "version": state}
        return self.store_receipt(directory, intent, request, principal, receipt)
