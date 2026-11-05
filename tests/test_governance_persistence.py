"""Historical authority, exact receipts and interrupted writes remain reviewable."""
from contextlib import closing
import copy
import hashlib
import json
import socket
import sqlite3
import threading
from unittest.mock import patch

from tests.governance_support import GovernanceCase
from tests.test_core_creation import creation


class GovernancePersistenceTests(GovernanceCase):
    def setUp(self):
        super().setUp()
        self.prepare()
        self.activate()

    def test_historical_charter_corruption_is_rejected_even_after_a_later_amendment(self):
        charter = copy.deepcopy(self.read()["au"]["charter"])
        charter["text"] = "Second effective charter"
        self.success("amend_charter", {"charter": charter, "reason": "Second charter"})
        charter["text"] = "Third effective charter"
        self.success("amend_charter", {"charter": charter, "reason": "Third charter"})
        with closing(sqlite3.connect(self.database())) as cx, cx:
            original = cx.execute("SELECT data FROM charters WHERE version=2").fetchone()[0]
            cx.execute("UPDATE charters SET data=? WHERE version=2", (json.dumps(charter),))
        try:
            status, value, _ = self.request("/api/v1/aus/" + self.au_id)
            self.assertEqual((status, value.get("code")), (409, "incompatible_state"), "Historical rules are part of effective-authority evidence")
        finally:
            with closing(sqlite3.connect(self.database())) as cx, cx:
                cx.execute("UPDATE charters SET data=? WHERE version=2", (original,))

    def test_command_payload_and_receipt_corruption_are_detected_before_read_or_replay(self):
        receipt, request = self.success("set_goal", {"goal": "Original adopted objective", "reason": "Known original request"})
        for column in ("payload", "receipt"):
            with self.subTest(column=column):
                with closing(sqlite3.connect(self.database())) as cx, cx:
                    original = cx.execute(f"SELECT {column} FROM governance_commands WHERE id=?", (receipt["id"],)).fetchone()[0]
                    damaged = json.loads(original)
                    if column == "payload":
                        damaged["data"]["goal"] = "An objective never adopted"
                    else:
                        damaged["actor_principal_id"] = "misattributed-subject"
                    cx.execute(f"UPDATE governance_commands SET {column}=? WHERE id=?", (json.dumps(damaged), receipt["id"]))
                try:
                    status, value, _ = self.request("/api/v1/aus/" + self.au_id)
                    self.assertEqual((status, value.get("code")), (409, "incompatible_state"))
                    self.assertEqual(self.request("/api/v1/governance/commands", request)[0], 409)
                finally:
                    with closing(sqlite3.connect(self.database())) as cx, cx:
                        cx.execute(f"UPDATE governance_commands SET {column}=? WHERE id=?", (original, receipt["id"]))

    def test_current_state_cannot_be_rewritten_without_its_adoption_evidence(self):
        with closing(sqlite3.connect(self.database())) as cx, cx:
            original = cx.execute("SELECT data FROM state").fetchone()[0]
            damaged = json.loads(original)
            damaged["goal"] = "Host edited goal without governance adoption"
            cx.execute("UPDATE state SET data=?", (json.dumps(damaged),))
        try:
            self.assertEqual(self.request("/api/v1/aus/" + self.au_id)[0], 409)
        finally:
            with closing(sqlite3.connect(self.database())) as cx, cx:
                cx.execute("UPDATE state SET data=?", (original,))

    def test_response_loss_after_commit_recovers_original_receipt_without_reexecution(self):
        version = self.read()["au"]["version"]
        request = {"id": "lost-response", "organization_id": self.au_id, "base_version": version,
                   "kind": "set_goal", "data": {"goal": "Committed once", "reason": "Response interruption"}}
        committed, release = threading.Event(), threading.Event()
        real_command = self.app.governance.command
        def commit_then_hold(token, value):
            receipt = real_command(token, value)
            committed.set()
            release.wait(5)
            return receipt
        with patch.object(self.app.governance, "command", side_effect=commit_then_hold):
            try:
                with self.assertRaises((TimeoutError, socket.timeout)):
                    self.request("/api/v1/governance/commands", request, timeout=0.15)
                self.assertTrue(committed.wait(2))
            finally:
                release.set()
        path = f"/api/v1/governance/receipts?organization_id={self.au_id}&id=lost-response"
        status, value, _ = self.request(path)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded")
        self.assertEqual(self.read()["au"]["version"], version + 1)
        before = self.dump()
        self.assertEqual(self.request("/api/v1/governance/commands", request)[1]["receipt"], value["receipt"])
        self.assertEqual(self.dump(), before)

    def test_wrong_catalog_mapping_cannot_mutate_another_governed_au(self):
        first = self.au_id
        first_intent = self.app.creation.catalog.intent_for_au(first)
        self.au_id = self.create(creation("other-governed-au"))["organization_id"]
        self.activate()
        other_intent = self.app.creation.catalog.intent_for_au(self.au_id)
        other_bytes = self.database().read_bytes()
        self.au_id = first
        version = self.read()["au"]["version"]
        with self.app.catalog() as cx:
            cx.execute("UPDATE organizations SET folder=? WHERE id=?", (other_intent["folder"], first))
        try:
            status, result, _ = self.command("set_goal", {"goal": "Wrong AU", "reason": "Directory is not identity"}, version=version)
            self.assertEqual((status, result.get("code")), (409, "incompatible_state"))
            self.assertEqual((self.root / other_intent["folder"] / "state.sqlite3").read_bytes(), other_bytes)
        finally:
            with self.app.catalog() as cx:
                cx.execute("UPDATE organizations SET folder=? WHERE id=?", (first_intent["folder"], first))

    def test_nonnullable_object_ids_are_rejected_before_any_persistent_change(self):
        self.appoint(); self.work(); self.grant()
        self.success("begin_local_action", {"attempt_id": "existing-attempt", "work_id": "work-a", "mandate_id": "mandate-a"})
        examples = {
            "appoint": {"member_id": "member-b", "principal_id": self.principal, "name": "Second", "binding_id": "binding-b", "duty": "Internal record"},
            "create_work": {"work_id": "work-b", "title": "Second", "instruction": "Record facts", "responsible_binding_id": "binding-a"},
            "grant_mandate": {"mandate_id": "mandate-b", "work_id": "work-a", "binding_id": "binding-a", "parent_id": None, "actions": ["record_memory"], "can_delegate": False},
            "begin_local_action": {"attempt_id": "next-attempt", "work_id": "work-a", "mandate_id": "mandate-a"},
            "submit_local_result": {"attempt_id": "existing-attempt", "content": "Bounded internal facts"},
        }
        for kind, data in examples.items():
            for field in data:
                if not field.endswith("_id") or field == "parent_id":
                    continue
                with self.subTest(kind=kind, field=field), closing(sqlite3.connect(self.database())) as cx, closing(sqlite3.connect(":memory:")) as snapshot:
                    cx.backup(snapshot)
                    before = self.dump()
                    try:
                        status, value, _ = self.command(kind, data | {field: None})
                        self.assertEqual((status, value.get("code")), (400, "invalid_request"))
                        self.assertEqual(self.dump(), before)
                    finally:
                        snapshot.backup(cx)
        self.grant("another-root")
        self.assertIsNone(self.read()["au"]["mandates"]["another-root"]["parent_id"])
