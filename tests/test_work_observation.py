"""U-067: post-dispatch evidence survives revocation; no real model calls."""
import copy
import json
import unittest

from ai_union.errors import Rejected
from ai_union.model_service import ServiceError
from ai_union.work_transport import ModeldWorkTransport
from tests import test_core_work as work_support
from tests.test_work_transport import FakeClient, CONNECTION, PACKAGE


def revoked_client(message=None):
    client = FakeClient(result={"message": message or {"content": "private-unadoptable-body"},
                                "usage": {"input_tokens": 11, "output_tokens": 4}})
    original = client.request

    def revoked(request_id, au_id):
        return original(request_id, au_id) | {"action_authorized": False}

    client.request = revoked
    return client


class WorkObservationTransportTests(unittest.TestCase):
    def test_completed_revoked_is_a_post_dispatch_fact_with_usage(self):
        client = revoked_client()
        channel = ModeldWorkTransport(client, "au-1", CONNECTION, clock=lambda: 0)
        with self.assertRaises(ServiceError) as caught:
            channel.chat(PACKAGE, [], [])
        error = caught.exception
        self.assertEqual(error.request_id, "work-overview-s1")
        self.assertEqual(error.usage, {"input_tokens": 11, "output_tokens": 4})
        self.assertNotIsInstance(error, Rejected)
        self.assertNotIn("private-unadoptable-body", str(error))
        self.assertEqual(len(client.bodies), 1)

    def test_invalid_post_dispatch_evidence_is_unknown_not_never_executed(self):
        for fault in ("identity", "event", "result"):
            with self.subTest(fault=fault):
                client = FakeClient()
                original = client.request
                if fault == "identity":
                    client.request = lambda request_id, au_id: original(request_id, au_id) | {"au_id": "other-au"}
                elif fault == "event":
                    client.events = lambda *args: {"events": [{"request_id": "other-request", "seq": 1}]}
                else:
                    client.result = {"message": None}
                channel = ModeldWorkTransport(client, "au-1", CONNECTION, clock=lambda: 0)
                with self.assertRaises(ServiceError):
                    channel.chat(PACKAGE, [], [])
                self.assertEqual(len(client.bodies), 1)


class WorkObservationTests(work_support.CoreWorkTests):
    # Reuse the HTTP/SQLite fixture without discovering its existing tests twice.
    def arrange_observation(self, message=None):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        client = revoked_client(message)
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, CONNECTION, clock=lambda: 0)
        return client

    def test_completed_revoked_preserves_usage_and_original_receipt_after_restart(self):
        client = self.arrange_observation()
        status, value, request = self.work_step()
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt.get("model_outcome"), "not_adoptable", value)
        self.assertNotIn("未执行", receipt["message"])
        card = self.works()["works"][0]
        self.assertEqual(card["budget"], {"max_calls": 4, "reserved": 0, "used": 1})
        step = card["steps"][0]
        self.assertEqual(step["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(step["model_request_id"], client.bodies[0]["id"])
        self.assertEqual(step["cost_status"], "unknown")
        self.assertEqual(card["results"], [])
        self.assertNotIn("private-unadoptable-body", self.dump())
        before = copy.deepcopy(card["steps"])
        self.stop()
        self.start()
        self.assertEqual(self.works()["works"][0]["steps"], before)
        status, persisted, _ = self.request(
            f"/api/v1/governance/receipts?organization_id={self.au_id}&id={request['id']}")
        self.assertEqual(status, 200, persisted)
        self.assertEqual(persisted["receipt"], receipt)
        status, value, _ = self.work_command(self.au_id, "reconcile_step", {
            "work_id": card["id"], "step_id": step["step_ref"], "status": "released", "reason": "cannot undo completed inference"})
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(self.works()["works"][0]["budget"]["used"], 1)

    def test_loop_stops_after_revoked_completion_and_never_executes_its_tools(self):
        client = self.arrange_observation({"content": "private-unadoptable-body", "tool_calls": [
            {"id": "read-after-revoke", "type": "function", "function": {
                "name": "read_document", "arguments": json.dumps({"path": "nested/a.md"})}}]})
        status, value, _ = self.run_loop()
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "rejected", value)
        self.assertEqual(receipt.get("model_outcome"), "not_adoptable", value)
        self.assertEqual(receipt["turns"], 1)
        self.assertEqual(receipt["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(len(client.bodies), 1)
        current = self.works()
        self.assertEqual(receipt["version"], current["version"])
        card = current["works"][0]
        self.assertEqual(card["tool_calls"], [])
        self.assertEqual(card["results"], [])
        self.assertEqual(card["budget"]["used"], 1)


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(WorkObservationTransportTests)
    suite.addTests(WorkObservationTests(name) for name in WorkObservationTests.__dict__ if name.startswith("test_"))
    return suite
