"""Review a supplied exact source tree; synthetic HTTP/SQLite and fake modeld only.

Usage: python candidate-boundary-probes.py <source-directory>
The source directory is imported, never edited. No real model configuration is read.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work import CoreWorkTests
from tests.test_work_transport import CONNECTION, FakeClient


class CandidateBoundaryProbes(CoreWorkTests):
    def interrupted_call(self):
        self.work_with_listing()
        self.prepare_materials()
        self.start_attempt()
        client = FakeClient(states=["interrupted"])
        self.app.work.transport = ModeldWorkTransport(
            client, self.au_id, CONNECTION, sleep=lambda _: None, clock=lambda: 0)
        status, value, request = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["model_outcome"], "unknown", value)
        self.assertEqual(len(client.bodies), 1)
        return client, value["receipt"], request

    def test_step_and_receipt_name_the_actual_modeld_request(self):
        client, receipt, _ = self.interrupted_call()
        step = self.works()["works"][0]["steps"][0]
        wire_id = client.bodies[0]["id"]
        self.assertEqual(step.get("model_request_id"), wire_id,
                         "a local run_id is not necessarily the modeld wire ID")
        self.assertEqual(receipt.get("model_request_id"), wire_id)

    def test_unconfirmed_interruption_cannot_be_manually_released(self):
        client, _, _ = self.interrupted_call()
        step = self.works()["works"][0]["steps"][0]
        self.work_command(self.au_id, "reconcile_step", {
            "work_id": "work-overview", "step_id": step["step_ref"],
            "status": "released", "reason": "interrupted is not proof of no execution"})
        card = self.works()["works"][0]
        self.assertEqual(card["steps"][0]["status"], "unknown",
                         "an accepted interrupted request must retain its reservation")
        self.assertEqual(card["budget"]["reserved"], 1)
        self.assertEqual(len(client.bodies), 1)

    def test_reopen_replays_receipt_without_a_second_dispatch(self):
        _, original, request = self.interrupted_call()
        self.stop()
        self.start()
        client = FakeClient()
        self.app.work.transport = ModeldWorkTransport(
            client, self.au_id, CONNECTION, sleep=lambda _: None, clock=lambda: 0)
        status, value, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"], original)
        self.assertEqual(client.bodies, [], "original command replay dispatched again")
        self.assertEqual(self.works()["works"][0]["budget"]["reserved"], 1)


if __name__ == "__main__":
    names = [name for name in CandidateBoundaryProbes.__dict__ if name.startswith("test_")]
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(CandidateBoundaryProbes(name) for name in names))
    raise SystemExit(not result.wasSuccessful())
