"""S02 public behavior: real identity, HTTP and AU transactions; explicit model double."""
from contextlib import closing
import copy
import json
import sqlite3

from tests.model_access_support import ModelAccessCase
from tests.test_core_creation import creation


class CoreModelConfigurationTests(ModelAccessCase):
    def test_core_governor_saves_without_inference_and_reopens_same_connection(self):
        initial = self.read()["au"]
        original = self.app.creation.catalog.intent_for_au(self.au_id)
        before = self.models()
        self.assertEqual(before["protocol"], "core.models.v1")
        self.assertEqual(before["connections"], [])
        receipt, request = self.saved()
        after = self.models()
        self.assertEqual(after["connections"][0]["revision"], 1)
        self.assertEqual(after["connections"][0]["model"], "model-a")
        self.assertFalse(after["connections"][0]["is_default"])
        self.assertEqual(self.provider.requests, {})
        self.assertEqual(self.app.creation.catalog.intent_for_au(self.au_id), original)
        au = self.read()["au"]
        self.assertEqual(au["schema_version"], 3)
        self.assertEqual(au["resources"], initial["resources"])
        self.assertEqual(au["governance_root"], initial["governance_root"])
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], receipt)
        self.stop(); self.start()
        self.assertEqual(self.models()["connections"], after["connections"])
        self.assertEqual(self.provider.requests, {})

    def test_ordinary_core_participant_can_configure_own_au_without_platform_role(self):
        self.token, self.principal = self.participant("ordinary")
        self.au_id = self.create(creation("ordinary-au"))["organization_id"]
        self.provider.au_id = self.au_id
        self.activate()
        self.assertFalse(self.app.session(self.token).get("platform_admin", False))
        self.saved()
        self.assertEqual(len(self.models()["connections"]), 1)

    def test_outsider_cross_au_grant_and_stale_version_cannot_save(self):
        outsider, _ = self.participant("outsider")
        before = self.dump()
        data = {"connection_id": "connection-a", "expected_revision": 0, "name": "Denied", "profile": "modeld_grant",
                "model": "model-a", "max_output_tokens": 256, "grant_ref": "grant-a", "grant_revision": 1}
        status, _, _ = self.model_command("save_connection", data, token=outsider, version=self.read()["au"]["version"])
        self.assertEqual(status, 403)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.request("/api/v1/models?organization_id=" + self.au_id, token=outsider)[0], 403)
        status, value, _ = self.model_command("save_connection", data, version=0)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected")
        self.assertEqual(self.provider.posts, [])
        self.provider.au_id = "different-au"
        receipt, _ = self.model_success("save_connection", data)
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "rejected")
        self.assertEqual(self.models()["connections"], [])

    def test_api_secret_never_enters_au_and_original_save_is_idempotent(self):
        receipt, request = self.saved(profile="openai_compatible")
        self.assertNotIn(request["data"]["api_key"], self.dump())
        self.assertNotIn(request["data"]["api_key"], json.dumps(self.models()))
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], receipt)
        changed = copy.deepcopy(request); changed["data"]["api_key"] += "-changed"
        self.assertEqual(self.request("/api/v1/models/commands", changed)[0], 409)
        self.assertEqual(len(self.provider.posts), 1)

    def test_lost_save_is_reconciled_by_original_registration_without_another_post(self):
        self.provider.lost_save = True
        receipt, request = self.saved(profile="openai_compatible")
        pending = self.wait_operation(receipt["operation_id"])
        self.assertEqual(pending["status"], "unknown")
        self.assertEqual(self.models()["connections"], [])
        self.model_success("reconcile_connection", {"operation_id": receipt["operation_id"]})
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "succeeded")
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(len(self.models()["connections"]), 1)

    def test_adoption_and_disable_do_not_call_model_or_reuse_old_verification(self):
        self.saved()
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1, "enabled": True, "make_default": True})
        first = self.models()["connections"][0]
        self.assertTrue(first["is_default"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": first["revision"], "enabled": False, "make_default": False})
        disabled = self.models()["connections"][0]
        self.assertFalse(disabled["enabled"])
        self.assertFalse(disabled["is_default"])
        self.assertEqual(self.provider.requests, {})

    def test_model_configuration_failure_rolls_back_schema_and_original_governance(self):
        with closing(sqlite3.connect(self.database())) as cx, cx:
            cx.execute("CREATE TRIGGER fail_model_state BEFORE UPDATE ON state BEGIN SELECT RAISE(ABORT, 'controlled failure'); END")
        before = self.dump()
        status, _, _ = self.model_command("grant_model_resources", {"max_calls": 4, "allow_unknown_cost": True, "reason": "bounded"})
        self.assertEqual(status, 503)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.read()["au"]["schema_version"], 2)
