"""Authenticated, versioned local governance; only the AU store writes AU facts."""
import copy
import time

from ..adapters.au_catalog import resolve_directory
from ..adapters.core_au_store import CoreAUStore, encoded
from ..adapters.governance_store import GovernanceStore
from ..domain import governance as rules
from ..domain import responsibility
from ..engine import identifier, now
from ..errors import CoreError, Rejected, require


class GovernanceService:
    def __init__(self, app):
        self.app = app
        self.store = GovernanceStore()

    def locate(self, au_id):
        entry, intent = self.app.creation.catalog.located_entry(au_id)
        directory, profile = resolve_directory(self.app.root, entry, creation=intent)
        if profile != "core_v1":
            raise CoreError("unsupported_capability", "此接口仅支持核心 V1 AU")
        return directory, intent

    def project(self, value, principal):
        state = value["au"]
        if not rules.reader_role(state, principal):
            raise CoreError("not_authorized")
        if state["schema_version"] in rules.SUPPORTED_SCHEMAS:
            clock = time.time()
            status = rules.effective_status(state, clock)
            gaps = []
            with self.app.read_catalog() as cx:
                principals = {row[0] for row in cx.execute("SELECT principal_id FROM owner_account")}
            try:
                rules.validate_live_targets(state, principals)
            except Rejected as error:
                gaps.append(str(error))
            if gaps and status == "active":
                status = "unavailable"
            value["governance_status"] = status
            value["readiness_gaps"] = gaps
            value["capabilities"]["local_submission"] = status == "active" and "record_memory" in state["charter"]["allowed_operations"]
            value["access"] = {"principal_id": principal, "service_instance": self.app.instance,
                               "role": rules.reader_role(state, principal),
                               "commands": rules.commands(state, principal, clock) + responsibility.commands(state, principal, clock)}
            if gaps:
                unavailable_commands = {"activate_governance", "renew_governance", "begin_local_action", "accept_local_result"}
                value["access"]["commands"] = [kind for kind in value["access"]["commands"] if kind not in unavailable_commands]
        return value

    def command(self, token, request):
        principal = self.app.creation.principal(self.app.session(token))
        try:
            rules.exact(request, {"id", "organization_id", "base_version", "kind", "data"})
            identifier(request["id"])
            identifier(request["organization_id"])
            require(type(request["base_version"]) is int and request["base_version"] >= 0, "须提供有效 AU 版本")
            require(isinstance(request["kind"], str) and isinstance(request["data"], dict) and len(encoded(request)) <= 200000, "命令格式无效或过大")
        except (Rejected, TypeError, ValueError) as error:
            raise CoreError("invalid_request", str(error)) from error
        with self.app.mutex, self.app.catalog() as accounts:
            require(self.app.identity.principal_in(accounts, token) == principal, "登录主体已变化")
            directory, intent = self.locate(request["organization_id"])
            with self.store.transaction(directory) as cx:
                value = CoreAUStore.read_in(cx, request["organization_id"], creation=intent)
                state = value["au"]
                schema = state["schema_version"]
                previous = self.store.existing(cx, request, principal)
                if previous is not None:
                    return previous
                local = request["kind"] in responsibility.FIELDS
                if local:
                    responsibility.authorize(state, request["kind"], principal)
                else:
                    rules.authorize(state, request["kind"], principal)
                try:
                    if local:
                        responsibility.validate_input(request["kind"], request["data"])
                        for key, value in request["data"].items():
                            if key.endswith("_id") and not (key == "parent_id" and value is None):
                                identifier(value)
                    else:
                        rules.validate_input(request["kind"], request["data"], principal)
                    if "config" in request["data"]:
                        config = request["data"]["config"]
                        principals = [config["final_decision_principal_id"], config["unavailability"].get("successor_principal_id")]
                        for target in filter(None, principals):
                            require(accounts.execute("SELECT 1 FROM owner_account WHERE principal_id=?", (target,)).fetchone(), "目标核心身份未登记")
                    if request["kind"] == "nominate_governor" and request["data"]["principal_id"]:
                        require(accounts.execute("SELECT 1 FROM owner_account WHERE principal_id=?", (request["data"]["principal_id"],)).fetchone(), "目标核心身份未登记")
                except Rejected as error:
                    raise CoreError("invalid_request", str(error)) from error
                if request["kind"] == "submit_local_result" and state.get("attempts", {}).get(request["data"]["attempt_id"], {}).get("principal_id") != principal:
                    raise CoreError("not_authorized")
                self.store.ensure_commands(cx)
                state = copy.deepcopy(state)
                charter = state.pop("charter")
                prior_policy = state["policy_version"]
                receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")}
                receipt.update(actor_principal_id=principal, created_at=now(), status="succeeded", effect="applied", message="本地治理操作已保存")
                changed = False
                try:
                    require(request["base_version"] == state["version"], "AU 版本已变化；请读取最新状态后检查原输入")
                    principals = {row[0] for row in accounts.execute("SELECT principal_id FROM owner_account")}
                    if local:
                        refusal = responsibility.apply(state, charter, request["kind"], request["data"], principal, time.time(), principals)
                        if refusal:
                            receipt.update(status="rejected", effect="evidence_only", message=refusal)
                    else:
                        charter = rules.apply(state, charter, request["kind"], request["data"], principal, time.time(), principals)
                    state["version"] += 1
                    changed = True
                except Rejected as error:
                    receipt.update(status="rejected", effect="none", message=str(error))
                receipt["version"] = state["version"]
                if schema == 1 and changed:
                    self.store.initialize(cx)
                if changed and state["schema_version"] == 2 and "read_document" in charter["allowed_tools"]:
                    from ..domain.model_access import initialize
                    from ..adapters.model_access_store import ModelAccessStore
                    initialize(state)
                    ModelAccessStore.initialize(cx)
                self.store.save(cx, state, charter, request, receipt, prior_policy, changed=changed)
                return receipt

    def receipt(self, token, au_id, request_id):
        principal = self.app.creation.principal(self.app.session(token))
        try:
            identifier(au_id)
            identifier(request_id)
        except Rejected as error:
            raise CoreError("invalid_request", str(error)) from error
        directory, intent = self.locate(au_id)
        receipt = self.store.receipt(directory, au_id, request_id, principal, intent)
        # A cancel delivery observation is a separate durable fact of the same
        # command; the merged view distinguishes acceptance from delivery.
        observation = self.store.delivery_observation(directory, request_id, principal)
        if receipt.get("kind") == "cancel_step" and receipt.get("cancel_accepted") is None:
            # A cancel acceptance always has an expected observation; an unreadable
            # or tampered one is not a trustworthy fact, so the read must fail.
            if observation is None:
                raise CoreError("storage_unavailable", "送达观察缺失或未通过完整性校验；请稍后重试查询")
            receipt = dict(receipt)
            receipt["cancel_accepted"] = observation["cancel_accepted"]
            receipt["message"] = observation["message"]
            receipt["delivery"] = observation
        return receipt
