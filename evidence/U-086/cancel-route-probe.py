"""Functional RED for cancelling an actual automatic request, not a manual reserve.

Usage: python cancel-route-probe.py <exact-source-directory>
Expected to FAIL on 2ff90f1/310c7e1: they do not cancel an automatic work request.
Only synthetic Core HTTP/SQLite and fake modeld are used. Source is not edited.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work import CoreWorkTests
from tests.test_work_transport import CONNECTION, FakeClient


class CancelRouteProbe(CoreWorkTests):
    def test_an_inflight_automatic_step_cancels_its_original_model_request(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        cancellations, observations = [], []
        provider = self.provider

        class Client(FakeClient):
            before_read = None

            def call(self, method, path, body=None, **kwargs):
                route = urlsplit(path)
                if method == "POST" and route.path.endswith("/cancel"):
                    request_id = unquote(route.path.split("/")[-2])
                    au_id = parse_qs(route.query).get("au_id", [None])[0]
                    cancellations.append((request_id, au_id))
                    return {"id": request_id, "au_id": au_id, "state": "cancel_requested"}
                if method == "POST" and route.path == "/v1/requests":
                    return super().call(method, path, body, **kwargs)
                return provider.call(method, path, body, **kwargs)

            def request(self, request_id, au_id):
                callback, self.before_read = self.before_read, None
                if callback:
                    callback(request_id, au_id)
                return super().request(request_id, au_id)

        client = Client(states=["interrupted"])

        def cancel_during_read(request_id, au_id):
            before = self.works()["works"][0]
            step = before["steps"][0]
            self.assertEqual(step["status"], "reserved")
            self.assertTrue(step["command_id"], "fixture must use an automatic reservation")
            self.assertEqual(step["model_request_id"], request_id)
            self.assertEqual(au_id, self.au_id)
            status, value, _ = self.work_command(self.au_id, "cancel_step", {
                "work_id": before["id"], "step_id": step["step_ref"],
                "reason": "Cancel the original running AI request, preserving unknown occupancy"})
            observations.append((status, value))
            after = self.works()["works"][0]
            self.assertIn(after["steps"][0]["status"], ("reserved", "unknown"))
            self.assertEqual(after["budget"]["reserved"], 1)

        client.before_read = cancel_during_read
        self.app.work.transport = ModeldWorkTransport(
            client, self.au_id, CONNECTION, sleep=lambda _: None, clock=lambda: 0)
        with patch("ai_union.model_service.ModelServiceClient", return_value=client):
            status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(len(client.bodies), 1)
        self.assertEqual(len(observations), 1)
        print("automatic cancel HTTP=%s receipt=%s modeld_cancel_posts=%s" % (
            observations[0][0], observations[0][1].get("receipt", {}).get("status"), len(cancellations)),
            file=sys.stderr)
        self.assertEqual(cancellations, [(client.bodies[0]["id"], self.au_id)],
                         "the actual automatic request never received the requested cancellation")
        self.assertEqual(self.works()["works"][0]["budget"]["reserved"], 1,
                         "cancel_requested/interrupted do not prove nonexecution")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        CancelRouteProbe("test_an_inflight_automatic_step_cancels_its_original_model_request")]))
    raise SystemExit(not result.wasSuccessful())
