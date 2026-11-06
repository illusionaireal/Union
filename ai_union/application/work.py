"""Start V1 work through the sole governance transaction; no execution side effects."""
import copy

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
        return {"protocol": rules.PROTOCOL, "organization_id": au_id, "version": state["version"],
                "access": {"principal_id": principal, "can_start": can_start},
                "works": rules.projection(state),
                "capabilities": {"work_registration": True, "execution": "not_started",
                                 "autonomous_business": False}}

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
                    receipt.update(rules.apply(local, charter, request["kind"], request["data"], principal, request["id"]))
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
