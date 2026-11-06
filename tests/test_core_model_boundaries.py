"""Public V1 model boundaries cannot widen legacy/local authority or history."""
from contextlib import closing
import copy
import json
import sqlite3
import time
import uuid
from unittest.mock import patch

from tests.model_access_support import ModelAccessCase
from tests.test_core_creation import creation


class CoreModelBoundaryTests(ModelAccessCase):
    def ready(self):
        self.saved()
        self.allow_documents()
        self.resource_grant()

    def test_prepared_au_refusal_has_an_original_receipt_without_adopting_schema(self):
        self.au_id = self.create(creation("prepared-model-refusal"))["organization_id"]
        before = self.read()["au"]
        status, value, request = self.model_command("grant_model_resources", {
            "max_calls": 2, "allow_unknown_cost": True, "reason": "Not authorized by governance yet"})
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected")
        self.assertEqual(self.request("/api/v1/models/receipts?organization_id=" + self.au_id + "&id=" + request["id"])[1]["receipt"], value["receipt"])
        self.assertEqual(self.read()["au"], before)
        self.assertEqual(self.provider.posts, [])

    def test_initial_schema_one_creation_cannot_hide_the_new_tool_permission(self):
        request = creation("initial-read-document")
        request["data"]["charter"]["allowed_tools"].append("read_document")
        before = self.app.organizations()
        status, value, _ = self.request("/api/commands", request)
        self.assertEqual(status, 400, value)
        self.assertEqual(self.app.organizations(), before)

    def test_explicit_read_document_adoption_updates_schema_and_keeps_original_history(self):
        origin = self.app.creation.catalog.intent_for_au(self.au_id)
        before = self.read()
        self.assertEqual(before["au"]["schema_version"], 2)
        self.allow_documents()
        after = self.read()
        self.assertEqual(after["au"]["schema_version"], 3)
        self.assertEqual(after["history"][:-1], before["history"])
        self.assertEqual(self.app.creation.catalog.intent_for_au(self.au_id), origin)
        self.assertEqual(self.models()["connections"], [])
        charter = copy.deepcopy(after["au"]["charter"])
        charter["allowed_tools"].remove("read_document")
        self.success("amend_charter", {"charter": charter, "reason": "Withdraw the new permission"})
        self.assertEqual(self.read()["au"]["schema_version"], 3)

    def test_refused_read_document_adoption_does_not_initialize_model_storage(self):
        charter = copy.deepcopy(self.read()["au"]["charter"])
        charter["board_can_amend"] = False
        self.success("amend_charter", {"charter": charter, "reason": "Close supported amendment procedure"})
        before = self.read()["au"]
        charter["allowed_tools"].append("read_document")
        self.reject("amend_charter", {"charter": charter, "reason": "New permission cannot authorize itself"})
        self.assertEqual(self.read()["au"], before)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertIsNone(cx.execute("SELECT name FROM sqlite_master WHERE name='model_attempts'").fetchone())

    def test_model_mandate_never_authorizes_a_local_record_action(self):
        self.ready()
        with patch.object(self.app.models, "spawn"):
            receipt, _ = self.start_check()
        check = self.models()["checks"][0]
        self.reject("begin_local_action", {"attempt_id": "wrong-action", "work_id": check["work_id"], "mandate_id": check["mandate_id"]})
        self.assertNotIn("wrong-action", self.read()["au"]["attempts"])
        self.assertEqual(self.provider.requests, {})

    def test_check_ids_cannot_overwrite_an_existing_work_or_its_history(self):
        self.ready()
        request_id = str(uuid.uuid4())
        suffix = uuid.uuid5(uuid.NAMESPACE_URL, self.au_id + ":" + request_id).hex
        work_id = "model-work-" + suffix
        self.appoint()
        self.work(work=work_id)
        self.success("update_work", {"work_id": work_id, "title": "Existing obligation", "instruction": "Keep original scope",
            "status": "stopped", "reason": "Existing history must survive"})
        before = self.read()["au"]
        status, value, _ = self.model_command("start_model_check", {
            "connection_id": "connection-a", "expected_revision": 1, "binding_id": None,
            "document_name": "sample.txt", "document_text": "Only this document"}, request_id=request_id)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(self.read()["au"], before)
        self.assertEqual(self.provider.requests, {})

    def test_api_key_in_connection_metadata_is_rejected_before_persistence(self):
        before = self.dump()
        status, value, _ = self.model_command("save_connection", {
            "connection_id": "api-a", "expected_revision": 0, "name": "controlled-private-key", "profile": "openai_compatible",
            "model": "model-a", "max_output_tokens": 256, "base_url": "https://models.example.invalid/v1", "api_key": "controlled-private-key"})
        self.assertEqual(status, 400, value)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.provider.posts, [])

    def test_revoked_remote_grant_cannot_be_adopted_as_default(self):
        self.saved()
        self.provider.revoked = True
        status, value, request = self.model_command("set_connection", {
            "connection_id": "connection-a", "expected_revision": 1, "enabled": True, "make_default": True})
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertFalse(self.models()["connections"][0]["is_default"])
        self.assertEqual(self.provider.requests, {})
        self.provider.revoked = False
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], value["receipt"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1, "enabled": True, "make_default": True})
        self.assertTrue(self.models()["connections"][0]["is_default"])

    def test_connection_can_be_disabled_when_governance_is_no_longer_active(self):
        self.saved()
        self.success("exit_governance", {"reason": "End active governance"})
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
            "enabled": False, "make_default": False})
        self.assertFalse(self.models()["connections"][0]["enabled"])
        self.assertEqual(self.provider.requests, {})

    def assert_changed_authority_is_rejected(self, stage):
        for number, change in enumerate(("appointment", "work", "mandate", "goal", "charter", "connection", "resources", "governance")):
            with self.subTest(stage=stage, change=change):
                if number:
                    self.au_id = self.create(creation(str(uuid.uuid4())))["organization_id"]
                    self.provider.au_id = self.au_id
                    self.activate()
                self.ready()
                previous_calls = len(self.provider.requests)
                original_request = self.provider.request
                changed = False

                def boundary(request_id, au_id):
                    nonlocal changed
                    if not changed and len(self.provider.requests) - previous_calls == stage + 1:
                        changed = True
                        check = self.models()["checks"][0]
                        if change == "appointment":
                            self.success("update_appointment", {"binding_id": check["binding_id"], "duty": "Changed responsibility", "reason": "Scope changed"})
                        elif change == "work":
                            self.success("update_work", {"work_id": check["work_id"], "title": "Changed work", "instruction": "New instructions",
                                "status": "open", "reason": "Scope changed"})
                        elif change == "mandate":
                            self.success("revoke_mandate", {"mandate_id": check["mandate_id"], "reason": "Withdraw authorization"})
                        elif change == "goal":
                            self.success("set_goal", {"goal": "Changed objective", "reason": "New objective"})
                        elif change == "charter":
                            charter = copy.deepcopy(self.read()["au"]["charter"])
                            charter["text"] += " Amended scope."
                            self.success("amend_charter", {"charter": charter, "reason": "New rules"})
                        elif change == "connection":
                            self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                "enabled": False, "make_default": False})
                        elif change == "resources":
                            self.resource_grant(6)
                        else:
                            self.success("exit_governance", {"reason": "Stop current governance"})
                    return original_request(request_id, au_id)

                with patch.object(self.provider, "request", side_effect=boundary):
                    receipt, _ = self.start_check()
                    check = self.wait_for("checks", receipt["check_id"])
                self.assertEqual(check["status"], "not_adopted", check)
                self.assertEqual(len(self.provider.requests) - previous_calls, stage + 1)
                self.assertTrue(all(a["usage"]["input_tokens"] == 25 for a in check["attempts"]))
                self.assertIsNone(check["output"])
                with closing(sqlite3.connect(self.database())) as cx:
                    self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], stage)

    def test_current_versions_are_checked_before_tool_execution(self):
        self.assert_changed_authority_is_rejected(0)

    def test_current_versions_are_checked_before_result_adoption(self):
        self.assert_changed_authority_is_rejected(1)
