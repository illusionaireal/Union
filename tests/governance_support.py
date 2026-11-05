"""Real local HTTP/database fixtures for the bounded S05 governance contract."""
from contextlib import closing
import copy
import json
import sqlite3
import unittest
import uuid

from tests import test_core_creation as core_http


class GovernanceCase(unittest.TestCase):
    setUp = core_http.CoreCreationTests.setUp
    start = core_http.CoreCreationTests.start
    stop = core_http.CoreCreationTests.stop
    request = core_http.CoreCreationTests.request
    setup_account = core_http.CoreCreationTests.setup_account
    create = core_http.CoreCreationTests.create

    def prepare(self):
        self.au_id = self.create()["organization_id"]
        self.principal = self.app.session(self.token)["principal_id"]
        return self.au_id

    def participant(self, username):
        status, value, cookie = self.request("/api/auth/register", {
            "username": username, "password": "participant-safe-password", "remember": True}, token=None)
        self.assertEqual(status, 200, value)
        return cookie.split("=", 1)[1].split(";", 1)[0], value["session"]["principal_id"]

    def config(self, successor=None):
        unavailable = {"mode": "exit_after_timeout", "timeout_seconds": 3600}
        if successor:
            unavailable.update(mode="successor_after_timeout", successor_principal_id=successor)
        return {"profile": "local_governance.v1", "final_decision_principal_id": self.principal,
                "reserved_matters": ["charter", "goal", "resources", "appointments", "mandates", "dissolution"],
                "unavailability": unavailable}

    def read(self, token="current"):
        status, result, _ = self.request("/api/v1/aus/" + self.au_id, token=token)
        self.assertEqual(status, 200, result)
        return result

    def command(self, kind, data, *, token="current", version=None, request_id=None):
        if version is None:
            version = self.read(token)["au"]["version"]
        request = {"id": request_id or str(uuid.uuid4()), "organization_id": self.au_id,
                   "base_version": version, "kind": kind, "data": copy.deepcopy(data)}
        status, result, _ = self.request("/api/v1/governance/commands", request, token)
        return status, result, request

    def success(self, kind, data, **kwargs):
        status, result, request = self.command(kind, data, **kwargs)
        self.assertEqual(status, 200, result)
        self.assertEqual(result["receipt"]["status"], "succeeded", result)
        return result["receipt"], request

    def reject(self, kind, data, **kwargs):
        status, result, request = self.command(kind, data, **kwargs)
        self.assertEqual(status, 200, result)
        self.assertEqual(result["receipt"]["status"], "rejected", result)
        return result["receipt"], request

    def database(self):
        intent = self.app.creation.catalog.intent_for_au(self.au_id)
        return self.root / intent["folder"] / "state.sqlite3"

    def dump(self):
        with closing(sqlite3.connect(self.database().as_uri() + "?mode=ro", uri=True)) as cx:
            return "\n".join(cx.iterdump())

    def activate(self, successor=None):
        self.success("adopt_governance", {"config": self.config(successor[1] if successor else None), "reason": "Adopt known local governance"})
        if successor:
            self.success("acknowledge_recovery", {"reason": "Accept the bounded recovery duty"}, token=successor[0])
        self.success("activate_governance", {"reason": "Enable internal records only"})

    def appoint(self, member="member-a", binding="binding-a", principal=None):
        self.success("appoint", {"member_id": member, "principal_id": principal or self.principal,
            "name": member, "binding_id": binding, "duty": "Maintain the specified internal record"})

    def work(self, work="work-a", binding="binding-a"):
        self.success("create_work", {"work_id": work, "title": "Internal record", "instruction": "Record checked facts",
                                    "responsible_binding_id": binding})

    def grant(self, mandate="mandate-a", work="work-a", binding="binding-a", parent=None, delegate=False, token="current"):
        self.success("grant_mandate", {"mandate_id": mandate, "work_id": work, "binding_id": binding,
                                      "parent_id": parent, "actions": ["record_memory"], "can_delegate": delegate}, token=token)


def governed_data():
    data = core_http.creation()
    if "record_memory" not in data["data"]["charter"]["allowed_operations"]:
        data["data"]["charter"]["allowed_operations"].append("record_memory")
    return data
