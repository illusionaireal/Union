"""Cancellation delivery fault probes; actual Core HTTP/SQLite, fake modeld only.

Usage: python cancel-delivery-probes.py <exact-source-export>
Expected RED on abfa9ee. The supplied product source is never modified.
"""
import copy
import json
import sqlite3
import sys
import unittest
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work import CoreWorkTests
from tests.test_work_transport import CONNECTION, FakeClient


class CancelDeliveryProbes(CoreWorkTests):
    def scenario(self, *, wrong_identity=None, fail_commit=False):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        directory, _ = self.app.governance.locate(self.au_id)
        database = directory / "state.sqlite3"
        provider = self.provider
        observed = {"cancellations": [], "at_transport": []}

        class Client(FakeClient):
            before_read = None

            def call(self, method, path, body=None, **kwargs):
                route = urlsplit(path)
                if method == "POST" and route.path.endswith("/cancel"):
                    request_id = unquote(route.path.split("/")[-2])
                    au_id = parse_qs(route.query).get("au_id", [None])[0]
                    observed["cancellations"].append((request_id, au_id))
                    # Independent connection: visibility, not Python in-memory state.
                    cx = sqlite3.connect(database, timeout=0)
                    try:
                        state = json.loads(cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0])
                        step = state["work_runtime"]["works"]["work-overview"]["steps"][0]
                        receipt_count = cx.execute(
                            "SELECT COUNT(*) FROM governance_commands WHERE id=?",
                            (observed["command"]["id"],)).fetchone()[0]
                        try:
                            cx.execute("BEGIN IMMEDIATE")
                            writer_available = True
                            cx.rollback()
                        except sqlite3.OperationalError:
                            writer_available = False
                        observed["at_transport"].append({
                            "intent": bool(step.get("cancel_requested_at")),
                            "receipt_count": receipt_count,
                            "writer_available": writer_available,
                        })
                    finally:
                        cx.close()
                    response = {"id": request_id, "au_id": au_id, "state": "cancel_requested"}
                    if wrong_identity:
                        response[wrong_identity] = "different-original-identity"
                    return response
                if method == "POST" and route.path == "/v1/requests":
                    return super().call(method, path, body, **kwargs)
                return provider.call(method, path, body, **kwargs)

            def request(self, request_id, au_id):
                callback, self.before_read = self.before_read, None
                if callback:
                    callback(request_id, au_id)
                return super().request(request_id, au_id)

        client = Client(states=["interrupted"])
        original_transaction = self.app.work.store.transaction

        @contextmanager
        def failed_transaction(path):
            with original_transaction(path) as cx:
                yield cx
                # A storage failure at exit must happen before any external delivery.
                raise sqlite3.OperationalError("injected cancellation commit failure")

        def cancel_during_read(request_id, au_id):
            work = self.works()["works"][0]
            step = work["steps"][0]
            self.assertEqual(step["status"], "reserved")
            self.assertTrue(step["command_id"])
            self.assertEqual((step["model_request_id"], self.au_id), (request_id, au_id))
            command = {"id": "cancel-delivery-original", "organization_id": au_id,
                       "base_version": self.works()["version"], "kind": "cancel_step",
                       "data": {"work_id": work["id"], "step_id": step["step_ref"],
                                "reason": "Cancel original request; retain unknown occupancy"}}
            observed["command"] = copy.deepcopy(command)
            fault = patch.object(self.app.work.store, "transaction", failed_transaction) if fail_commit else nullcontext()
            with fault:
                status, value, _ = self.request("/api/v1/work/commands", command)
            observed["post"] = {"http": status, "value": copy.deepcopy(value)}

        client.before_read = cancel_during_read
        self.app.work.transport = ModeldWorkTransport(
            client, self.au_id, CONNECTION, sleep=lambda _: None, clock=lambda: 0)
        with patch("ai_union.model_service.ModelServiceClient", return_value=client):
            status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(len(client.bodies), 1, "no extra model dispatch is allowed")
        work = self.works()["works"][0]
        self.assertEqual(work["steps"][0]["status"], "unknown")
        self.assertEqual(work["budget"]["reserved"], 1)
        observed["after"] = copy.deepcopy(work["steps"][0])
        if not fail_commit:
            self.assertEqual(observed["post"]["http"], 200, observed["post"])
            self.assertEqual(observed["post"]["value"]["receipt"]["status"], "succeeded")
        print(json.dumps({"transport": observed["at_transport"],
                          "cancel_posts": len(observed["cancellations"]),
                          "post_http": observed["post"]["http"],
                          "post_accepted": observed["post"]["value"].get("receipt", {}).get("cancel_accepted"),
                          "saved_intent": bool(observed["after"].get("cancel_requested_at"))}), file=sys.stderr)
        return observed

    def test_cancel_intent_is_committed_before_external_delivery(self):
        value = self.scenario()
        self.assertEqual(len(value["at_transport"]), 1)
        self.assertTrue(value["at_transport"][0]["intent"],
                        "external cancel began before the intent was committed")

    def test_external_cancel_does_not_hold_the_au_writer(self):
        value = self.scenario()
        self.assertEqual(len(value["at_transport"]), 1)
        self.assertTrue(value["at_transport"][0]["writer_available"],
                        "external cancellation still holds the AU write transaction")

    def test_delivered_receipt_survives_original_get_and_restart(self):
        value = self.scenario()
        first = value["post"]["value"]["receipt"]
        self.assertTrue(first["cancel_accepted"], "fixture must reach a claimed delivered cancellation")
        self.stop()
        self.start()
        query = urlencode({"organization_id": self.au_id, "id": value["command"]["id"]})
        status, readback, _ = self.request("/api/v1/governance/receipts?" + query)
        self.assertEqual(status, 200, readback)
        self.assertEqual(readback["receipt"], first,
                         "original GET after restart contradicts the delivered POST receipt")

    def test_wrong_model_request_response_cannot_confirm_delivery(self):
        value = self.scenario(wrong_identity="id")
        self.assertIsNot(value["post"]["value"]["receipt"].get("cancel_accepted"), True,
                         "wrong model request identity was accepted")

    def test_wrong_au_response_cannot_confirm_delivery(self):
        value = self.scenario(wrong_identity="au_id")
        self.assertIsNot(value["post"]["value"]["receipt"].get("cancel_accepted"), True,
                         "wrong AU identity was accepted")

    def test_commit_failure_cannot_send_cancel_and_lose_its_intent(self):
        value = self.scenario(fail_commit=True)
        self.assertEqual(value["post"]["http"], 503, "the injected storage failure must reach the caller")
        self.assertFalse(value["after"].get("cancel_requested_at"))
        self.assertEqual(value["cancellations"], [],
                         "cancel was sent but the transaction rolled back its only durable intent")


if __name__ == "__main__":
    names = [name for name in CancelDeliveryProbes.__dict__ if name.startswith("test_")]
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(CancelDeliveryProbes(name) for name in names))
    raise SystemExit(not result.wasSuccessful())
