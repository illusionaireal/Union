"""The modeld-backed work channel: request shapes, definite refusal and unknown outcomes."""
import unittest

from ai_union.errors import Rejected
from ai_union.model_service import ServiceError
from ai_union.work_transport import ModeldWorkTransport

CONNECTION = {"id": "connection-a", "revision": 2, "grant_ref": "grant-a", "grant_revision": 3,
              "model": "model-a", "max_output_tokens": 1024, "task_ms": 30000}
PACKAGE = {"kind": "work_step", "work_id": "work-overview", "attempt_id": "work-overview#a1",
           "run_id": "work-overview#s1"}


class FakeClient:
    def __init__(self, *, post_error=None, states=None, result=None):
        self.post_error = post_error
        self.states = list(states or ["completed"])
        self.result = result if result is not None else {"message": {"role": "assistant", "content": "正文"},
                                                         "usage": {"input_tokens": 11, "output_tokens": 4}}
        self.bodies = []
        self.events_calls = 0

    def call(self, method, path, body=None, **kwargs):
        if method == "POST":
            if self.post_error is not None:
                raise self.post_error
            self.bodies.append(body)
            return {"state": "queued"}
        raise AssertionError("unexpected call " + method + " " + path)

    def request(self, request_id, au_id):
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return {"id": request_id, "au_id": au_id, "state": state,
                "result": self.result if state == "completed" else None}

    def events(self, request_id, au_id, after=0):
        self.events_calls += 1
        return {"events": [{"request_id": request_id, "seq": after + 1, "type": "delta"}]}


class ModeldWorkTransportTests(unittest.TestCase):
    def transport(self, client):
        return ModeldWorkTransport(client, "au-1", CONNECTION, sleep=lambda _: None, clock=lambda: 0)

    def test_a_completed_request_returns_the_message_and_usage(self):
        client = FakeClient()
        message, usage = self.transport(client).chat(PACKAGE, [{"role": "user", "content": "目标"}],
                                                     [{"type": "function", "function": {"name": "read_document"}}])
        self.assertEqual(message["content"], "正文")
        self.assertEqual(usage, {"input_tokens": 11, "output_tokens": 4})
        body = client.bodies[0]
        self.assertEqual(body["id"], "work-overview-s1", "the step reference is made request-safe")
        self.assertEqual((body["au_id"], body["connection_id"], body["model_id"]), ("au-1", "connection-a", "model-a"))
        self.assertEqual(body["generation"], {"maxOutputTokens": 1024})
        self.assertEqual(body["deadlines"]["task_ms"], 30000)

    def test_a_definite_refusal_is_rejected_and_produces_no_step_fact(self):
        client = FakeClient(post_error=ServiceError("rejected", 422))
        with self.assertRaises(Rejected) as caught:
            self.transport(client).chat(PACKAGE, [], [])
        self.assertIn("未执行", str(caught.exception))

    def test_a_server_side_failure_stays_unknown_instead_of_rejected(self):
        client = FakeClient(post_error=ServiceError("unavailable", 503))
        with self.assertRaises(ServiceError):
            self.transport(client).chat(PACKAGE, [], [])

    def test_an_interrupted_request_is_not_silently_treated_as_a_result(self):
        client = FakeClient(states=["interrupted"])
        with self.assertRaises(ServiceError):
            self.transport(client).chat(PACKAGE, [], [])

    def test_a_revoked_grant_cannot_be_used_to_accept_the_result(self):
        client = FakeClient()
        original = client.request

        def revoked(request_id, au_id):
            remote = original(request_id, au_id)
            remote["action_authorized"] = False
            return remote

        client.request = revoked
        with self.assertRaises(Rejected):
            self.transport(client).chat(PACKAGE, [], [])


    def test_the_host_factory_builds_a_channel_from_the_private_configuration(self):
        from unittest.mock import patch
        from ai_union import work_transport

        with patch("ai_union.model_service.ModelServiceClient") as client:
            build = work_transport.modeld_factory("host-private.json", timeout_seconds=30)
            transport = build("au-1", CONNECTION)
        self.assertIsInstance(transport, work_transport.ModeldWorkTransport)
        self.assertEqual(transport.au_id, "au-1")
        self.assertEqual(transport.timeout_seconds, 30)
        client.assert_called_once_with("host-private.json")

    def test_the_host_factory_refuses_a_work_without_a_connection(self):
        from ai_union import work_transport
        with self.assertRaises(Rejected):
            work_transport.modeld_factory("host-private.json")("au-1", None)

if __name__ == "__main__":
    unittest.main()
