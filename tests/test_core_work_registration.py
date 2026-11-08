"""U105: existing registration/receipt transaction through real HTTP and SQLite.

No production model request is authorized. Connection setup uses the explicit double.
"""
import sqlite3
from unittest.mock import patch

from tests.model_access_support import ModelAccessCase
from tests.test_core_work import work_data


class WorkRegistrationTests(ModelAccessCase):
    def setUp(self):
        super().setUp()
        self.saved()
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                               "enabled": True, "make_default": True})
        self.allow_documents()
        self.before = self.read()["au"]["version"]
        self.original = {"id": "u105-original", "organization_id": self.au_id,
                         "base_version": self.before, "kind": "start_work", "data": work_data()}

    def receipt(self, token="current"):
        return self.request("/api/v1/governance/receipts?organization_id=" + self.au_id
                            + "&id=" + self.original["id"], token=token)

    def test_original_registration_reopens_with_all_bindings_and_no_dispatch(self):
        status, result, _ = self.request("/api/v1/work/commands", self.original)
        self.assertEqual(status, 200, result)
        original = result["receipt"]
        self.assertEqual(original["status"], "succeeded")
        self.stop()
        self.start()
        self.assertEqual(self.receipt()[1]["receipt"], original)
        status, replay, _ = self.request("/api/v1/work/commands", self.original)
        self.assertEqual(status, 200, replay)
        self.assertEqual(replay["receipt"], original)
        state = self.read()["au"]
        self.assertEqual(state["version"], self.before + 1)
        for table in ("members", "bindings", "definitions", "mandates", "works"):
            self.assertEqual(len(state["work_runtime"][table]), 1)
        item = self.request("/api/v1/work?organization_id=" + self.au_id)[1]["works"][0]
        self.assertEqual(item["id"], original["work_id"])
        self.assertEqual(item["definition"]["version"], 1)
        self.assertEqual(item["mandate"]["version"], 1)
        self.assertEqual(item["budget"], {"max_calls": 4, "reserved": 0, "used": 0})
        self.assertEqual(item["attempts"], [])
        self.assertEqual(self.provider.requests, {})

    def test_foreign_principal_cannot_register_or_read_original_receipt(self):
        token, _ = self.participant("registration-outsider")
        status, _, _ = self.request("/api/v1/work/commands", self.original, token=token)
        self.assertEqual(status, 403)
        self.assertEqual(self.read()["au"]["version"], self.before)
        self.request("/api/v1/work/commands", self.original)
        self.assertEqual(self.receipt(token)[0], 403)
        self.assertEqual(self.provider.requests, {})

    def test_stale_version_or_connection_revision_leaves_no_work(self):
        for field in ("version", "connection"):
            with self.subTest(field=field):
                request = dict(self.original, id="u105-" + field, data=dict(self.original["data"]))
                if field == "version":
                    request["base_version"] -= 1
                else:
                    request["data"]["expected_revision"] += 1
                status, result, _ = self.request("/api/v1/work/commands", request)
                self.assertEqual(status, 200, result)
                self.assertEqual(result["receipt"]["status"], "rejected")
                self.assertEqual(self.read()["au"].get("work_runtime", {}).get("works", {}), {})
        self.assertEqual(self.provider.requests, {})

    def test_commit_failure_rolls_back_work_and_original_receipt_together(self):
        with patch.object(self.app.work.store, "save", side_effect=sqlite3.OperationalError("controlled commit failure")):
            status, _, _ = self.request("/api/v1/work/commands", self.original)
        self.assertGreaterEqual(status, 400)
        self.assertEqual(self.read()["au"]["version"], self.before)
        self.assertEqual(self.read()["au"].get("work_runtime", {}).get("works", {}), {})
        self.assertEqual(self.receipt()[0], 403)
        self.assertEqual(self.provider.requests, {})
