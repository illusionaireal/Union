"""Authenticated V1 model configuration; external I/O follows durable intent."""
import copy
import hashlib
import secrets
import threading
import time
import uuid
from urllib.parse import urlencode

from ..adapters.core_au_store import CoreAUStore, encoded
from ..adapters.model_access_store import ModelAccessStore
from ..domain import governance, model_access as rules, model_checks, model_profiles
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require
from ..model_service import ServiceError
from ..model_diagnostics import failure


def contains_secret(value, secret):
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(contains_secret(key, secret) or contains_secret(item, secret) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_secret(item, secret) for item in value)
    return False


class ModelAccessService:
    def __init__(self, app):
        self.app = app
        self.store = app.governance.store
        self.stopping = False
        self.running = set()
        from .model_checks import ModelCheckRunner
        self.check_runner = ModelCheckRunner(self)

    @staticmethod
    def backend():
        from ..model_service import ModelServiceClient
        return ModelServiceClient()

    def read(self, token, au_id):
        value = self.app.core_au(token, au_id)
        principal = self.app.creation.principal(self.app.session(token))
        state = value["au"]
        models = state.get("model_access", {"connections": {}, "checks": {}, "operations": {},
            "default_connection_id": None, "resource_grant": None})
        can_configure = principal == governance.current(state) and value.get("governance_status") == "active" and not value.get("readiness_gaps")
        return {"protocol": "core.models.v1", "organization_id": au_id, "version": state["version"],
            "access": {"principal_id": principal, "service_instance": self.app.instance, "can_configure": can_configure},
            "governance_status": value.get("governance_status", "prepared"),
            "document_read_allowed": "read_document" in state["charter"]["allowed_tools"],
            "capabilities": {"profiles": list(model_profiles.PROFILES), "tools": ["read_document"],
                             "profile_scope": model_profiles.scope(), "autonomous_business": False},
            "connections": [copy.deepcopy(v) | {"is_default": k == models["default_connection_id"]} for k, v in models["connections"].items()],
            "operations": [{k: v[k] for k in ("id", "status", "message")} | {"diagnostic": copy.deepcopy(v.get("diagnostic"))}
                           for v in models["operations"].values()],
            "checks": list(copy.deepcopy(models["checks"]).values()),
            "resources": {"grant": copy.deepcopy(models["resource_grant"]), "reserved_calls": rules.occupied_calls(models),
                          "plan_max_calls": state["resources"]["max_calls"]}}

    def receipt(self, token, au_id, request_id):
        return self.app.governance.receipt(token, au_id, request_id)

    def command(self, token, incoming):
        principal = self.app.creation.principal(self.app.session(token))
        request = copy.deepcopy(incoming)
        secret = None
        try:
            governance.exact(request, {"id", "organization_id", "base_version", "kind", "data"})
            identifier(request["id"]); identifier(request["organization_id"])
            require(type(request["base_version"]) is int and request["base_version"] >= 0, "须提供当前 AU 版本")
            require(isinstance(request["data"], dict) and isinstance(request["kind"], str), "命令格式无效")
            if request["kind"] == "save_connection" and model_profiles.requires_api_key(request["data"].get("profile")):
                secret = request["data"].pop("api_key", None)
                require(isinstance(secret, str) and 1 <= len(secret) <= 4096 and all(33 <= ord(c) <= 126 for c in secret), "须提供合法 API Key")
                require("api_key_sha256" not in request["data"], "不接受客户端凭据摘要")
                require(not contains_secret(request, secret), "密钥不能放入连接名称、模型或其他公开字段")
                request["data"]["api_key_sha256"] = hashlib.sha256(secret.encode()).hexdigest()
            require(len(encoded(request)) <= 200000, "命令过大")
        except (Rejected, ValueError, TypeError, KeyError) as error:
            raise CoreError("invalid_request", str(error)) from error
        kind, data = request["kind"], request["data"]
        default_error = self.default_grant_error(token, principal, request)
        job = None
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
                    rules.validate_input(kind, data)
                    for key, value in data.items():
                        if (key.endswith("_id") or key == "grant_ref") and not (key == "binding_id" and value is None):
                            identifier(value)
                except (Rejected, ValueError, TypeError) as error:
                    raise CoreError("invalid_request", str(error)) from error
                charter = state.pop("charter")
                self.store.ensure_commands(cx)
                receipt = self.new_receipt(request, principal)
                changed = False
                cx.execute("SAVEPOINT model_command")
                try:
                    require(request["base_version"] == state["version"], "AU 版本已变化；请读取最新状态检查原输入")
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    stopping_connection = kind == "set_connection" and data["enabled"] is False
                    if kind not in ("reconcile_connection", "reconcile_model_check", "cancel_model_check") and not stopping_connection:
                        rules.active(state, principal, time.time(), principals)
                    else:
                        require(state["schema_version"] == 3, "没有可核对的模型操作")
                    ModelAccessStore.initialize(cx)
                    if kind == "start_model_check":
                        check = model_checks.prepare(state, charter, data, principal, request["id"], time.time(), principals)
                        ModelAccessStore.save_material(cx, check["id"], data["document_name"], data["document_text"], secrets.token_hex(12))
                        receipt["check_id"] = check["id"]
                        job = (self.check_runner.run, request["organization_id"], check["id"])
                    elif kind in ("reconcile_model_check", "cancel_model_check"):
                        check = state["model_access"]["checks"].get(data["check_id"])
                        require(check and check["status"] in ("queued", "running", "unknown", "cancel_requested"), "没有待核对或可停止的原模型验证")
                        if kind == "cancel_model_check":
                            check.update(stop_requested=True, status="cancel_requested", message="已记录本地停止；远端取消与费用尚须核对")
                        else:
                            check.update(status="running", message="查询原请求，恢复未确认的验证", diagnostic=None)
                        receipt["check_id"] = check["id"]
                        job = (self.check_runner.run, request["organization_id"], check["id"])
                    else:
                        require(default_error is None, default_error)
                        receipt.update(rules.apply(state, kind, data, principal, request["id"]))
                    state["version"] += 1
                    changed = True
                    if kind in ("save_connection", "reconcile_connection"):
                        job = (self.save_connection, request["organization_id"], receipt["operation_id"], secret, kind == "reconcile_connection")
                except Rejected as error:
                    cx.execute("ROLLBACK TO model_command")
                    job = None
                    receipt.update(status="rejected", effect="none", message=str(error))
                cx.execute("RELEASE model_command")
                receipt["version"] = state["version"]
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=changed)
        if job:
            self.spawn(*job)
        return receipt

    def default_grant_error(self, token, principal, request):
        """Read current remote authority outside locks; commit rechecks local versions."""
        data = request["data"]
        if request["kind"] != "set_connection" or data.get("make_default") is not True:
            return None
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            directory, intent = self.app.governance.locate(request["organization_id"])
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)["au"]
                if self.store.existing(cx, request, principal) is not None:
                    return None
                rules.authorize(state, principal)
                if state["schema_version"] != 3 or request["base_version"] != state["version"]:
                    return None
                try:
                    rules.validate_input(request["kind"], data)
                    config = copy.deepcopy(rules.connection(state, data["connection_id"], data["expected_revision"]))
                except (Rejected, KeyError, TypeError):
                    return None  # The command transaction records the precise refusal.
        try:
            self.check_grant(self.backend(), request["organization_id"], config)
        except (ServiceError, Rejected, OSError):
            return "无法确认当前模型服务授权有效；本次未采用默认连接"
        return None

    @staticmethod
    def new_receipt(request, principal):
        return {k: request[k] for k in ("id", "organization_id", "base_version", "kind")} | {
            "actor_principal_id": principal, "created_at": now(), "status": "succeeded", "effect": "applied", "message": "模型操作已保存；执行结果另行显示"}

    def mutate(self, au_id, principal, kind, callback):
        """Internal factual transitions have no public command entry or extra authority."""
        with self.app.mutex, self.app.catalog() as accounts:
            directory, intent = self.app.governance.locate(au_id)
            with self.store.transaction(directory) as cx:
                state = CoreAUStore.read_in(cx, au_id, creation=intent)["au"]
                charter = state.pop("charter")
                request = {"id": str(uuid.uuid4()), "organization_id": au_id, "base_version": state["version"], "kind": "model_fact:" + kind, "data": {}}
                principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                result = callback(state, charter, cx, principals)
                state["version"] += 1
                receipt = self.new_receipt(request, principal) | {"version": state["version"]}
                self.store.save(cx, state, charter, request, receipt, state["policy_version"], changed=True)
                return result

    def state(self, au_id):
        directory, intent = self.app.governance.locate(au_id)
        return CoreAUStore().read(directory, au_id, creation=intent)["au"]

    def recover(self):
        """Startup marks orphaned local jobs; it never dispatches or queries a model."""
        for entry in self.app._catalog_entries():
            _, profile = self.app._resolve_entry(entry)
            if profile != "core_v1":
                continue
            state = self.state(entry["id"])
            if state["schema_version"] != 3:
                continue
            for table in ("operations", "checks"):
                for key, record in state["model_access"][table].items():
                    if record["status"] not in ("saving", "queued", "running", "cancel_requested"):
                        continue
                    def interrupted(current, charter, cx, principals, table=table, key=key):
                        current["model_access"][table][key].update(status="unknown",
                            message="宿主作业已中断；请核对原操作。系统未重新发送模型或保存请求")
                    self.mutate(entry["id"], record["principal_id"], "host_interrupted", interrupted)

    def spawn(self, function, au_id, key, *args):
        with self.app.mutex:
            if (au_id, key) in self.running:
                return
            self.running.add((au_id, key))
            def run():
                try:
                    function(au_id, key, *args)
                finally:
                    with self.app.mutex:
                        self.running.discard((au_id, key))
            thread = None
            try:
                thread = threading.Thread(target=run, daemon=True)
                self.app.jobs.append(thread)
                thread.start()
            except (RuntimeError, OSError):
                try:
                    # Keep the job owned until its failed start is durable. An
                    # explicit recovery cannot finish and then be overwritten by
                    # this older outcome after the mutex is released.
                    models = self.state(au_id)["model_access"]
                    table = "checks" if key in models["checks"] else "operations"
                    principal = models[table][key]["principal_id"]
                    self.mutate(au_id, principal, "worker_start_failed", lambda state, charter, cx, principals:
                        state["model_access"][table][key].update(status="unknown", **failure("worker_start_failed")))
                finally:
                    self.running.discard((au_id, key))
                    if thread in self.app.jobs:
                        self.app.jobs.remove(thread)

    @staticmethod
    def check_grant(client, au_id, config):
        grant = client.call("GET", "/v1/grants/" + config["grant_ref"], admin=True)
        require(grant.get("id") == config["grant_ref"] and grant.get("au_id") == au_id
                and grant.get("revision") == config["grant_revision"] and not grant.get("revoked_at")
                and config["model"] in grant.get("model_ids", []), "模型服务授权不属于本 AU、已撤销或版本已变化")
        return grant

    def save_connection(self, au_id, operation_id, secret, reconcile):
        operation = self.state(au_id)["model_access"]["operations"][operation_id]
        principal, config = operation["principal_id"], operation["config"]
        try:
            client = self.backend()
            if model_profiles.requires_api_key(config["profile"]):
                if reconcile:
                    registered = client.call("GET", "/v1/api-connections/" + operation_id + "?" + urlencode({"au_id": au_id, "principal_id": principal}), admin=True)
                else:
                    self.mutate(au_id, principal, "saving", lambda state, charter, cx, principals: self.check_operation(state, operation, principals))
                    registered = client.call("POST", "/v1/api-connections", {"id": operation_id, "au_id": au_id,
                        "principal_id": principal, "name": config["name"], "base_url": config["base_url"], "api_key": secret, "model_id": config["model"]}, admin=True)
                require(registered.get("id") == operation_id and registered.get("au_id") == au_id and registered.get("principal_id") == principal
                        and registered.get("model_id") == config["model"] and registered.get("profile") == "openai_compatible", "模型服务原保存回执范围不一致")
                config = config | {"grant_ref": registered["grant_ref"], "grant_revision": registered["grant_revision"]}
            self.check_grant(client, au_id, config)
            def adopt(state, charter, cx, principals):
                target = state["model_access"]["operations"][operation_id]
                try:
                    self.check_operation(state, operation, principals)
                    state["model_access"]["connections"][config["connection_id"]] = {k: v for k, v in config.items() if k not in ("connection_id", "expected_revision")} | {
                        "id": config["connection_id"], "revision": config["expected_revision"] + 1, "enabled": True, "last_check": None}
                    target.update(status="succeeded", message="连接已保存；尚未调用模型", diagnostic=None)
                except Rejected as error:
                    target.update(status="rejected", message="原保存未采用：" + str(error))
            self.mutate(au_id, principal, "connection_saved", adopt)
        except (ServiceError, Rejected, OSError, KeyError, ValueError, TypeError) as error:
            unknown = isinstance(error, (ServiceError, OSError)) and getattr(error, "status", None) not in (400, 401, 403, 404, 413, 422)
            details = failure(error.code, error.status) if isinstance(error, ServiceError) else failure(
                "model_service_unavailable" if isinstance(error, OSError) else "authorization_changed" if isinstance(error, Rejected) else None)
            self.mutate(au_id, principal, "connection_unconfirmed", lambda state, charter, cx, principals:
                state["model_access"]["operations"][operation_id].update(status="unknown" if unknown else "rejected", **details))

    @staticmethod
    def check_operation(state, operation, principals):
        rules.active(state, operation["principal_id"], time.time(), principals)
        require(all(state[k] == v for k, v in operation["versions"].items()), "原保存的治理/目标/章程版本已变化")
        config = operation["config"]
        old = state["model_access"]["connections"].get(config["connection_id"])
        require((old["revision"] if old else 0) == config["expected_revision"], "连接已经被其他操作修改")
