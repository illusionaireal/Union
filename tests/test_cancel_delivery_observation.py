"""Original cancel recovery: real Core HTTP/SQLite; one fake dispatch per case."""
from contextlib import closing
import json
import sqlite3
import threading

from ai_union.adapters.core_au_store import encoded
from ai_union.adapters.governance_store import digest
from ai_union.errors import Rejected
from tests.model_access_support import ModelAccessCase
from tests import test_core_work as support


class CancelDeliveryObservationTests(ModelAccessCase):
    adopt_default = support.CoreWorkTests.adopt_default
    allow_listing = support.CoreWorkTests.allow_listing
    work_command = support.CoreWorkTests.work_command
    work = support.CoreWorkTests.work
    works = support.CoreWorkTests.works
    prepare_materials = support.CoreWorkTests.prepare_materials
    work_with_listing = support.CoreWorkTests.work_with_listing
    start_attempt = support.CoreWorkTests.start_attempt
    work_step = support.CoreWorkTests.work_step
    cancel_in_flight = support.CoreWorkTests.cancel_in_flight

    def prepare_delivery(self):
        self.cancellations, self.client = self.cancel_in_flight()
        self.directory, _ = self.app.governance.locate(self.au_id)
        self.original = self.cancel_response[1]["receipt"]
        self.principal = self.original["actor_principal_id"]

    def query(self, request_id=None, token="current"):
        return self.request("/api/v1/governance/receipts?organization_id=" + self.au_id
                            + "&id=" + (request_id or self.cancel_request["id"]), token=token)

    def change_observation(self, *, principal=None, observed=None, rehash=False):
        with closing(sqlite3.connect(self.directory / "state.sqlite3")) as cx, cx:
            row = cx.execute("SELECT id,principal_id,observed,hash FROM delivery_observations").fetchone()
            record = dict(zip(("id", "principal_id", "observed", "hash"), row))
            if principal is not None:
                record["principal_id"] = principal
            if observed is not None:
                record["observed"] = encoded(observed)
            if rehash:
                record["hash"] = digest({k: v for k, v in record.items() if k != "hash"})
            cx.execute("UPDATE delivery_observations SET principal_id=?,observed=?,hash=? WHERE id=?",
                       tuple(record[k] for k in ("principal_id", "observed", "hash", "id")))

    def assert_recovery_refused(self):
        self.assertNotEqual(self.query()[0], 200, "GET trusted a corrupt delivery observation")
        self.assertNotEqual(self.request("/api/v1/work/commands", self.cancel_request)[0], 200,
                            "same-ID POST trusted a corrupt delivery observation")
        self.assertEqual(len(self.cancellations), 1)
        self.assertEqual(len(self.client.bodies), 1)

    def test_changed_observation_with_original_hash_refuses_get_and_replay(self):
        self.prepare_delivery()
        self.change_observation(observed={"cancel_accepted": False, "message": "changed"})
        self.assert_recovery_refused()

    def test_observation_bound_to_different_principal_is_not_silently_ignored(self):
        self.prepare_delivery()
        self.change_observation(principal="different-principal", rehash=True)
        self.assert_recovery_refused()

    def test_malformed_observation_cannot_override_original_receipt(self):
        self.prepare_delivery()
        for observed in ({"cancel_accepted": "true", "message": "wrong type"},
                         {"cancel_accepted": True, "message": "extra", "kind": "run_loop"},
                         {"cancel_accepted": True}, ["invalid shape"]):
            with self.subTest(observed=observed):
                self.change_observation(observed=observed, rehash=True)
                self.assert_recovery_refused()

    def test_observation_cannot_attach_to_a_non_cancel_command(self):
        self.prepare_delivery()
        with closing(sqlite3.connect(self.directory / "state.sqlite3")) as cx, cx:
            request_id = next(row[0] for row in cx.execute("SELECT id,payload FROM governance_commands")
                              if json.loads(row[1])["kind"] == "start_work")
            record = {"id": request_id, "principal_id": self.principal,
                      "observed": encoded(self.original["delivery"])}
            cx.execute("INSERT INTO delivery_observations VALUES(?,?,?,?)",
                       (*record.values(), digest(record)))
        self.assertNotEqual(self.query(request_id)[0], 200)

    def test_original_get_can_read_while_another_connection_holds_the_writer(self):
        self.prepare_delivery()
        finished, result = threading.Event(), []

        def read():
            try:
                result.append(self.query())
            finally:
                finished.set()

        with closing(sqlite3.connect(self.directory / "state.sqlite3")) as cx:
            cx.execute("BEGIN IMMEDIATE")
            reader = threading.Thread(target=read)
            reader.start()
            try:
                read_before_release = finished.wait(5)
            finally:
                cx.rollback()
                reader.join(15)
        self.assertTrue(read_before_release, "GET waited for an unrelated AU writer")
        self.assertEqual(result[0][0], 200)
        self.assertEqual(result[0][1]["receipt"], self.original)

    def test_delivery_record_cannot_be_overwritten(self):
        self.prepare_delivery()
        self.app.work.store.record_delivery(self.directory, self.cancel_request["id"],
                                            self.principal, self.original["delivery"])
        with self.assertRaises(Rejected):
            self.app.work.store.record_delivery(self.directory, self.cancel_request["id"], self.principal,
                                                {"cancel_accepted": False, "message": "replacement"})
        self.assertEqual(self.query()[1]["receipt"], self.original)

    def test_missing_observation_preserves_unknown_without_resending_or_creating_table(self):
        self.prepare_delivery()
        with closing(sqlite3.connect(self.directory / "state.sqlite3")) as cx, cx:
            cx.execute("DROP TABLE delivery_observations")
        self.stop()
        self.start()
        status, readback, _ = self.query()
        self.assertEqual(status, 200)
        self.assertIsNone(readback["receipt"]["cancel_accepted"])
        self.assertNotIn("delivery", readback["receipt"])
        status, replay, _ = self.request("/api/v1/work/commands", self.cancel_request)
        self.assertEqual(status, 200)
        self.assertEqual(replay["receipt"], readback["receipt"])
        self.assertEqual(len(self.cancellations), 1)
        with closing(sqlite3.connect(self.directory / "state.sqlite3")) as cx:
            self.assertIsNone(cx.execute("SELECT 1 FROM sqlite_master WHERE name='delivery_observations'").fetchone())

    def test_other_principal_and_changed_payload_cannot_use_original_recovery(self):
        self.prepare_delivery()
        token, _ = self.participant("different-reader")
        self.assertEqual(self.query(token=token)[0], 403)
        self.assertEqual(self.request("/api/v1/work/commands", self.cancel_request, token=token)[0], 403)
        self.assertEqual(self.request("/api/v1/work/commands", self.cancel_request | {"base_version": 0})[0], 409)
        self.assertEqual(self.query()[1]["receipt"], self.original)
        self.assertEqual(len(self.cancellations), 1)
