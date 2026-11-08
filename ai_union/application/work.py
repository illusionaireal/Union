"""Start V1 work through the sole governance transaction; no execution side effects."""
import copy

import hashlib
import json

from ..adapters import documents
from ..adapters.core_au_store import CoreAUStore, encoded
from ..adapters.governance_store import commands_in
from ..adapters.work_context_store import WorkContextStore
from ..domain import governance, work as rules
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require
from ..work_transport import UnadoptableWorkResult
from . import work_dispatch as dispatch


class WorkService:
    def __init__(self, app):
        self.app = app
        self.store = app.governance.store
        self.transport = None
        self.transport_factory = None
        self.active_steps = {}
        self.active_loops = set()

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
        can_manage_results = principal == governance.current(state) and value.get("governance_status") == "active"
        can_start = can_manage_results and default is not None and default["enabled"]
        works = rules.projection(state, instance=self.app.instance)
        for item in works:
            item["materials"] = self.materials(item["materials_root"])
        usage = {"input_tokens": 0, "output_tokens": 0}
        for item in works:
            for key in usage:
                usage[key] += item["usage"][key]
        return {"protocol": rules.PROTOCOL, "organization_id": au_id, "version": state["version"],
                "access": {"principal_id": principal, "can_start": can_start,
                           "can_manage_results": can_manage_results},
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
        if request["kind"] == "reconcile_step":
            try:
                rules.validate_input(request["kind"], request["data"])
            except (Rejected, TypeError, ValueError) as error:
                raise CoreError("invalid_request", str(error)) from error
            automatic = self.reconcile_automatic(token, request, principal)
            if automatic is not None:
                return automatic
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
                        self.close_completed_result_attempt(cx, local, request["data"])
                        receipt["message"] = "已采用该成果并记录采用人"
                    elif request["kind"] == "reconcile_step":
                        receipt["step"] = rules.reconcile_step(local, request["data"])
                        receipt["message"] = "已按核对结果处理该次未知步进"
                    elif request["kind"] == "cancel_step":
                        step = next(
                            (s for s in rules.records(local)["works"].get(request["data"]["work_id"], {})
                             .get("steps") or [] if s["step_ref"] == request["data"]["step_id"]), None)
                        if step is not None and step.get("command_id"):
                            receipt["step"] = rules.cancel_intent(local, request["data"])
                            receipt["message"] = "取消意图已提交；线端送达观察另行持久化，执行事实仍按原请求核对"
                            receipt["model_request_id"] = step["model_request_id"]
                            receipt["cancel_accepted"] = None
                            receipt["cancel_connection"] = copy.deepcopy(step.get("connection") or {})
                        else:
                            receipt["step"] = rules.cancel_step(local, request["data"])
                            receipt["message"] = "已记录本地取消；远端结果未知，预约已释放且费用保持未知"
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
        if receipt.get("cancel_accepted") is None and receipt.get("model_request_id"):
            # The committed intent is durable; delivery happens outside the AU writer
            # lock, and its observed result is stored as a second immutable fact of the
            # same command (changed=False): replay always shows the latest observation.
            channel = getattr(self, "transport", None)
            if channel is None and self.transport_factory is not None:
                try:
                    channel = self.transport_factory(request["organization_id"],
                                                     receipt.get("cancel_connection") or {})
                except Exception:  # noqa: BLE001 - a refused cancel keeps the intent only
                    channel = None
            accepted, note = False, "线端取消送达失败；意图已持久化，可重试核对"
            if channel is not None and hasattr(channel, "client"):
                from urllib.parse import urlencode
                try:
                    remote = channel.client.call(
                        "POST", "/v1/requests/" + receipt["model_request_id"]
                        + "/cancel?" + urlencode({"au_id": request["organization_id"]}), {})
                    if isinstance(remote, dict) and remote.get("id") == receipt["model_request_id"] \
                            and remote.get("au_id") == request["organization_id"]:
                        accepted = True
                        note = "取消已送达原线端请求；执行事实仍按原请求核对，预约保留"
                except Exception:  # noqa: BLE001 - delivery failure keeps the intent only
                    accepted = False
            receipt["cancel_accepted"] = accepted
            receipt["message"] = note
            observation = {"cancel_accepted": accepted, "message": note}
            directory, intent = self.app.governance.locate(request["organization_id"])
            self.store.record_delivery(directory, request["id"], principal, observation)
            receipt["delivery"] = observation
        return receipt

    def close_completed_result_attempt(self, cx, state, data):
        """Adoption may retire its proven finished loop, never unknown or later work.

        This runs after current authority/version/digest checks in the adoption
        transaction. It neither completes the Work nor releases any reservation.
        """
        work = rules.records(state)["works"][data["work_id"]]
        result = next(r for r in work["results"] if r["id"] == data["result_id"])
        attempt = next((a for a in work.get("attempts", []) if a["id"] == result["attempt_id"]), None)
        steps = [s for s in work.get("steps", []) if s["attempt_id"] == result["attempt_id"]]
        if not attempt or attempt["status"] != "running" or not steps or any(
                s["status"] in ("reserved", "unknown") for s in steps):
            return
        saved = commands_in(cx, state["id"])
        last = steps[-1]
        for loop in work.get("loops", []):
            parent = saved.get(loop["command_id"])
            if not parent or parent["request"]["kind"] != "run_loop" or parent["request"]["data"] != {"work_id": work["id"]}:
                continue
            receipt = parent["value"]
            if receipt["status"] != "succeeded" or receipt.get("result") is not True:
                continue
            command_id = loop["command_id"] + "-t" + str(receipt.get("turns"))
            step_receipt = saved.get(command_id, {}).get("value", {})
            if (last.get("command_id") == command_id and last["status"] == "used"
                    and result["id"] == "result-" + command_id.replace("-", "")[:12]
                    and step_receipt.get("status") == "succeeded" and step_receipt.get("result") is True
                    and step_receipt.get("step") == last["step_ref"]):
                rules.finish_attempt(state, {"work_id": work["id"], "attempt_id": attempt["id"],
                    "outcome": "stopped", "reason": "原自动循环 " + loop["command_id"] + " 已完成并采用成果；工作待交付"})
                return

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

    def result_content(self, token, au_id, result_id, work_id=None):
        """Read one adopted or candidate result body; the digest is re-checked on read."""
        try:
            identifier(au_id)
            identifier(result_id)
            if work_id is not None:
                identifier(work_id)
        except (Rejected, TypeError) as error:
            raise CoreError("invalid_request", str(error)) from error
        value = self.app.core_au(token, au_id)
        matches = []
        for work in rules.records(value["au"])["works"].values():
            if work_id is not None and work["id"] != work_id:
                continue
            for result in work.get("results") or []:
                if result["id"] != result_id:
                    continue
                digest = hashlib.sha256(result["content"].encode("utf-8")).hexdigest()
                if digest != result["sha256"]:
                    raise CoreError("incompatible_state", "成果正文与登记摘要不一致；不能作为正式成果读取")
                matches.append({"protocol": rules.PROTOCOL, "organization_id": au_id, "work_id": work["id"],
                                "result": {key: item for key, item in result.items() if key != "content"},
                                "content": result["content"]})
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise CoreError("invalid_request", "成果标识有多个工作匹配；请提供原工作标识")
        raise CoreError("invalid_request", "此 AU 中没有该成果标识")

    def run_step(self, token, incoming):
        if not isinstance(incoming, dict) or not all(isinstance(incoming.get(k), str) for k in ("id", "organization_id")):
            return self._run_step(token, incoming)
        key = (incoming["organization_id"], incoming["id"])
        with self.app.mutex:
            self.active_steps[key] = self.active_steps.get(key, 0) + 1
        try:
            return self._run_step(token, incoming)
        finally:
            with self.app.mutex:
                self.active_steps[key] -= 1
                if not self.active_steps[key]:
                    del self.active_steps[key]

    def _run_step(self, token, incoming):
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
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                original = dispatch.find(state, request, principal)
                if original is not None:
                    return dispatch.pending(request, principal, state, original)
                rules.authorize(state, principal)
                require(request["base_version"] == state["version"], "AU 版本已变化；请读取最新状态检查原输入")
                try:
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    rules.effective(state, principals)
                    plan = rules.step_plan(state, state["charter"], request["data"]["work_id"],
                                           instance=self.app.instance)
                    work = rules.records(state)["works"][plan["work_id"]]
                    history, plan["sources"], bindings = WorkContextStore.load(cx, work, plan["context_scope"])
                    plan["materials_binding"] = None
                    if plan["materials_root"] is not None:
                        try:
                            root = documents.root_for(self.app.root, plan["materials_root"])
                            plan["materials_binding"] = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
                        except Rejected:
                            pass  # A first turn with no material history has nothing to redisclose.
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
            self.verify_material_binding(plan)
        except Rejected as error:
            return self.reject_step(directory, intent, request, principal, str(error))
        # Building a channel does not dispatch. Commit intent before its first POST.
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                original = dispatch.find(state, request, principal)
                if original is not None:
                    return dispatch.pending(request, principal, state, original)
                rules.authorize(state, principal)
                require(state["version"] == request["base_version"], "AU 版本已变化；请读取最新状态检查原输入")
                rules.effective(state, {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")})
                reservation = dispatch.prepare(self.store, cx, state, request, principal, plan, self.app.instance)
        plan["package"]["run_id"] = reservation["model_request_id"]
        try:
            self.verify_material_binding(plan)
        except Rejected as error:
            return self.record_channel_outcome(directory, intent, request, principal,
                                               "派发前资料授权变化；未调用模型：" + str(error), refused=True)
        try:
            message, usage = transport.chat(copy.deepcopy(plan["package"]), copy.deepcopy(plan["messages"]),
                                            copy.deepcopy(plan["tools"]))
        except UnadoptableWorkResult as error:
            return self.record_channel_outcome(directory, intent, request, principal, str(error), completed=error)
        except Rejected as error:
            return self.record_channel_outcome(directory, intent, request, principal,
                                    "模型通道明确拒绝；原预约已释放，本轮未执行：" + str(error)[:280], refused=True)
        except Exception as error:  # noqa: BLE001 - an unconfirmed call keeps a reservation to reconcile
            return self.record_channel_outcome(directory, intent, request, principal,
                                     "模型通道结果未知；已保留该次调用预约等待核对，不自动重放：" + str(error)[:280])
        with self.app.mutex, self.app.catalog() as accounts:
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
                    "actor_principal_id": principal, "created_at": now(), "status": "succeeded",
                    "effect": "applied", "message": "已执行一次自动模型步进"}
                changed = False
                cx.execute("SAVEPOINT work_step")
                try:
                    self.verify_material_binding(plan)
                    require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
                    rules.authorize(state, principal)
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    rules.effective(state, principals)
                    local = copy.deepcopy(state)
                    work = rules.records(local)["works"][request["data"]["work_id"]]
                    current_plan = rules.step_plan(local, charter, work["id"], instance=self.app.instance,
                                                   reserved_step=reservation["step_ref"])
                    require(current_plan["context_scope"] == reservation["context_scope"]
                            and current_plan["connection"] == reservation["connection"]
                            and current_plan["attempt_id"] == reservation["attempt_id"]
                            and local["policy_version"] == reservation["policy_version"]
                            and local["charter_version"] == reservation["charter_version"], "原调用的有效授权或执行版本已变化")
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
                               "title": "自动成果：" + work["title"], "usage": usage if isinstance(usage, dict) else {},
                               "step_id": reservation["step_ref"]}
                    receipt.update(rules.apply_step(local, charter, payload, principal, self.app.instance))
                    turn_messages = [assistant]
                    new_receipts = work.get("tool_calls", [])[-len(outputs):] if outputs else []
                    for (call, _), output, tool_receipt in zip(parsed_calls, outputs, new_receipts):
                        turn_messages.append({"role": "tool", "name": call["function"]["name"],
                                              "tool_call_id": call["id"],
                                              "content": encoded(output | {"step_ref": tool_receipt["step_ref"]})})
                    original = dispatch.find(local, request, principal)
                    WorkContextStore.save(cx, original, current_plan["context_scope"], turn_messages,
                                          [item["step_ref"] for item in new_receipts],
                                          hashlib.sha256(str(root).encode("utf-8")).hexdigest() if outputs else None)
                    state = local
                    changed = True
                except (Rejected, CoreError) as error:
                    cx.execute("ROLLBACK TO work_step")
                    original = dispatch.find(state, request, principal)
                    dispatch.settle(original, "not_adoptable", str(error), usage if isinstance(usage, dict) else {})
                    receipt.update(status="rejected", effect="evidence_only", model_outcome="not_adoptable",
                                   message="调用已完成但结果不能采用：" + str(error),
                                   usage=original["usage"], step=original["step_ref"],
                                   model_request_id=original["model_request_id"], tool_calls=0, result=False,
                                   cost_status="unknown")
                    changed = True
                cx.execute("RELEASE work_step")
                dispatch.event(self.store, cx, state, charter, request, principal, "observed")
                receipt["version"] = state["version"]
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=False)
        return receipt

    def verify_material_binding(self, plan):
        if plan.get("materials_binding") is not None:
            root = documents.root_for(self.app.root, plan["materials_root"])
            require(hashlib.sha256(str(root).encode("utf-8")).hexdigest() == plan["materials_binding"],
                    "宿主资料目录绑定已变化；原上下文不能继续派发或采用")

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
                rules.authorize(current, principal)
                work = rules.records(current)["works"].get(request["data"]["work_id"])
                require(work is not None, "工作不存在或不属于此 AU")
                loop = next((item for item in work.get("loops", []) if item["command_id"] == request["id"]), None)
                if loop is None:
                    require(current["version"] == request["base_version"], "AU 版本已变化；请读取最新状态检查原输入")
                    rules.effective(current, {r[0] for r in accounts.execute("SELECT principal_id FROM owner_account")})
                    remaining = work["max_calls"] - rules.budget(work)["reserved"] - rules.budget(work)["used"]
                    require(remaining > 0, "该工作的调用上限已用尽")
                    loop = {"command_id": request["id"], "command_sha256": dispatch.request_digest(request),
                            "principal_id": principal, "turn_cap": min(3, remaining),
                            "first_version": current["version"] + 1}
                    work.setdefault("loops", []).append(loop)
                    charter = current.pop("charter")
                    dispatch.event(self.store, cx, current, charter, request, principal, "loop_prepared")
                key = (request["organization_id"], request["id"])
                if key in self.active_loops:
                    return dispatch.receipt(request, principal, current["version"], status="unknown", effect="none",
                        model_outcome="unknown", turns=0, tool_calls=0, result=False,
                        message="原循环仍在运行；此为中间状态，不重新派发或固化终态", cost_status="unknown")
            self.active_loops.add(key)
        try:
            return self.drive_loop(token, request, principal, directory, intent, loop)
        finally:
            with self.app.mutex:
                self.active_loops.discard(key)

    def drive_loop(self, token, request, principal, directory, intent, loop):
        version = loop["first_version"]
        turns = 0
        tool_calls = 0
        produced = False
        usage_total = {"input_tokens": 0, "output_tokens": 0}
        status = "succeeded"
        model_outcome = None
        message = "自动循环结束：模型没有给出成果，已用满本轮轮次"
        for index in range(loop["turn_cap"]):
            step_request = {"id": request["id"] + "-t" + str(index + 1),
                            "organization_id": request["organization_id"], "base_version": version,
                            "kind": "run_step", "data": dict(request["data"])}
            try:
                step = self.run_step(token, step_request)
            except Rejected as error:
                if isinstance(error, CoreError) and error.code not in (
                        "not_authenticated", "not_authorized", "unsupported_capability"):
                    raise
                # Admission can fail before run_step has a receipt. Preserve the
                # parent's completed facts, but never turn a dispatch/storage
                # failure into proof that a reserved request did not run.
                with self.app.mutex, self.store.transaction(directory) as cx:
                    current = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                    step = self.store.existing(cx, step_request, principal)
                    if step is None:
                        if dispatch.find(current, step_request, principal) is not None:
                            raise
                        step = dispatch.receipt(step_request, principal, current["version"],
                            status="rejected", effect="none",
                            message=f"自动循环在第 {index + 1} 步派发前停止；之前已完成 {turns} 次调用：{error}")
            version = step.get("version", version)
            if step.get("status") != "succeeded" and step.get("model_outcome") != "not_adoptable":
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
        if status == "rejected":
            receipt["phase"] = "loop-stopped"
        if status == "unknown":
            receipt["model_outcome"] = "unknown"
        elif model_outcome is not None:
            receipt["model_outcome"] = model_outcome
        return self.store_receipt(directory, intent, request, principal, receipt)

    def reconcile_automatic(self, token, request, principal):
        """Observe the stored model request; never POST or adopt a recovered body."""
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            directory, intent = self.app.governance.locate(request["organization_id"])
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                rules.authorize(state, principal)
                work = rules.records(state)["works"].get(request["data"]["work_id"], {})
                step = next((s for s in work.get("steps", []) if s["step_ref"] == request["data"]["step_id"]), None)
                if step is None or not step.get("command_id"):
                    return None
                original = copy.deepcopy(step)
                refusal = None
                if state["version"] != request["base_version"]:
                    refusal = "AU 版本已变化；请读取最新状态检查原输入"
                elif step["status"] not in ("reserved", "unknown"):
                    refusal = "原模型调用已经结算，不能更改执行事实"
                elif self.active_steps.get((request["organization_id"], step["command_id"]), 0):
                    refusal = "原调用仍在执行；不能把本地核对当作远端取消"
            if refusal:
                return self.reject_step(directory, intent, request, principal, refusal)
        usage = None
        message = "原模型请求仍未确认；保留预约，不重新派发"
        try:
            channel = self.transport
            if channel is None and self.transport_factory is not None:
                channel = self.transport_factory(request["organization_id"], original["connection"])
            require(channel is not None and hasattr(channel, "lookup"), "宿主通道不支持原请求查询")
            usage = channel.lookup(original["model_request_id"])
        except Exception:  # Absence/timeout/auth failure cannot prove no execution.
            pass
        with self.app.mutex:
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                work = rules.records(state)["works"][request["data"]["work_id"]]
                step = next(s for s in work["steps"] if s["step_ref"] == original["step_ref"])
                require(step["model_request_id"] == original["model_request_id"], "原请求关联已变化")
                if isinstance(usage, dict) and step["status"] in ("reserved", "unknown"):
                    message = "原模型请求已确认完成；保留用量，不采用恢复的正文"
                    dispatch.settle(step, "not_adoptable", message, usage)
                    dispatch.event(self.store, cx, state, charter, request, principal, "reconciled")
                value = dispatch.receipt(request, principal, state["version"], message=message,
                    step={k: step.get(k) for k in ("step_ref", "status", "reason")},
                    model_outcome="not_adoptable" if step["status"] == "used" else "unknown",
                    model_request_id=step["model_request_id"], usage=step.get("usage", {}),
                    tool_calls=0, result=False, cost_status="unknown")
                self.store.ensure_commands(cx)
                self.store.save(cx, state, charter, request, value, state["policy_version"], changed=False)
        return value

    def record_channel_outcome(self, directory, intent, request, principal, message, *, completed=None, refused=False):
        """Keep unknown calls reserved, and completed unadoptable calls used."""
        with self.app.mutex:
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                step = dispatch.find(state, request, principal)
                require(step is not None, "缺少原调用预约")
                outcome = "refused" if refused else "not_adoptable" if completed else "unknown"
                if completed is not None and completed.request_id != step["model_request_id"]:
                    outcome, completed = "unknown", None
                dispatch.settle(step, outcome, message, completed.usage if completed else None)
                details = {"step": step["step_ref"], "model_request_id": step["model_request_id"], "model_outcome": outcome}
                if completed is not None:
                    details["usage"] = dict(step["usage"])
                dispatch.event(self.store, cx, state, charter, request, principal, "observed")
                receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")} | {
                    "actor_principal_id": principal, "created_at": now(), "status": "rejected" if refused else "succeeded",
                    "effect": "applied", "message": message, **details,
                    "tool_calls": 0, "result": False, "version": state["version"], "cost_status": "unknown"}
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=False)
        return receipt

    def store_receipt(self, directory, intent, request, principal, receipt):
        """Persist only the receipt of this request; AU facts stay untouched."""
        with self.app.mutex:
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                # A duplicate may commit intent while this invocation is still
                # preparing its channel. Its dispatch owns the final receipt;
                # a late preflight refusal cannot declare that call unexecuted.
                original = dispatch.find(state, request, principal)
                if original is not None:
                    return dispatch.pending(request, principal, state, original)
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
