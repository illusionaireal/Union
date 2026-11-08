"""Independent offline acceptance probes for the exact S03 candidate in argv[1]."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from ai_union.adapters.core_au_store import CoreAUStore
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work import CoreWorkTests
from tests.test_work_transport import FakeClient, CONNECTION


class ReviewProbes(CoreWorkTests):
    def arrange_work(self):
        self.work_with_listing()
        directory = self.prepare_materials()
        self.start_attempt()
        return directory

    def test_reservation_is_committed_before_external_dispatch(self):
        self.arrange_work()
        owner = self
        observations = []

        class ObservingTransport:
            def chat(self, package, messages, tools):
                directory, intent = owner.app.governance.locate(owner.au_id)
                with owner.app.work.store.transaction(directory) as cx:
                    state = CoreAUStore.read_in(cx, owner.au_id, creation=intent)["au"]
                    work = state["work_runtime"]["works"]["work-overview"]
                    observations.append(json.loads(json.dumps(work.get("steps", []))))
                return {"content": "Controlled result", "tool_calls": []}, {"input_tokens": 11, "output_tokens": 4}

        self.app.work.transport = ObservingTransport()
        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(len(observations), 1)
        self.assertTrue(observations[0], "transport was entered with no durable step or reservation")
        self.assertEqual(observations[0][0]["status"], "reserved")

    def test_authorized_document_text_reaches_second_model_turn(self):
        directory = self.arrange_work()
        nonce = "review-public-document-nonce-c3247"
        (directory / "nested" / "a.md").write_text(nonce, encoding="utf-8")
        transport = self.with_transport(
            {"content": None, "tool_calls": [{"id": "review-call-1", "type": "function",
             "function": {"name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]},
            {"content": "Prearranged fixture answer", "tool_calls": []},
        )
        status, value, _ = self.run_loop()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(len(transport.calls), 2)
        self.assertNotIn(nonce, json.dumps(transport.calls[0]))
        self.assertIn(nonce, json.dumps(transport.calls[1]), "the tool read the file but discarded its body")
        self.assertIn("review-call-1", json.dumps(transport.calls[1]["messages"]))

    def test_completed_then_revoked_request_retains_execution_fact(self):
        self.arrange_work()
        client = FakeClient()
        original = client.request

        def revoked(request_id, au_id):
            remote = original(request_id, au_id)
            remote["action_authorized"] = False
            return remote

        client.request = revoked
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, CONNECTION,
                                                      sleep=lambda _: None, clock=lambda: 0)
        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(len(client.bodies), 1, "fake modeld accepted one request")
        card = self.works()["works"][0]
        self.assertEqual(card["results"], [], "revocation must prevent result adoption")
        self.assertTrue(card["steps"], "completed inference was reported as never executed and its usage lost")
        self.assertEqual(card["budget"]["used"] + card["budget"]["reserved"], 1)


names = [name for name in ReviewProbes.__dict__ if name.startswith("test_")]
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(ReviewProbes(name) for name in names))
raise SystemExit(not result.wasSuccessful())
