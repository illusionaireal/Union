"""Check cancellation cannot erase call occupancy; synthetic HTTP/SQLite only.

Usage: python cancel-boundary-probes.py <exact-source-directory>
The supplied source is imported without edits. Rejection of unsupported cancel_step
is a safety control only, never evidence that cancellation is implemented.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work import CoreWorkTests, work_data
from tests.test_work_transport import CONNECTION, FakeClient


class CancelBoundaryProbes(CoreWorkTests):
    def make_call(self, state="interrupted"):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        status, value, _ = self.work(data=work_data(max_calls=1))
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.prepare_materials()
        self.start_attempt()
        client = FakeClient(states=[state])
        self.app.work.transport = ModeldWorkTransport(
            client, self.au_id, CONNECTION, sleep=lambda _: None, clock=lambda: 0)
        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(len(client.bodies), 1)
        work = self.works()["works"][0]
        self.assertEqual(work["steps"][0]["status"],
                         "used" if state == "completed" else "unknown")
        self.assertEqual(work["budget"]["max_calls"], 1)
        return client, copy.deepcopy(work)

    def cancel(self, work):
        status, value, _ = self.work_command(self.au_id, "cancel_step", {
            "work_id": work["id"], "step_id": work["steps"][0]["step_ref"],
            "reason": "Request local cancellation; remote execution remains unconfirmed"})
        self.assertIn(status, (200, 400), value)
        if status == 400:
            self.assertIn("不支持的核心工作命令", value.get("error", ""), value)
        print("cancel HTTP=%s receipt=%s" % (status, value.get("receipt", {}).get("status")),
              file=sys.stderr)

    def test_local_cancel_keeps_unknown_call_occupied(self):
        client, before = self.make_call()
        self.cancel(before)
        after = self.works()["works"][0]
        step = after["steps"][0]
        self.assertEqual(step["status"], "unknown", "local cancel released an unconfirmed call")
        self.assertEqual(after["budget"], {"max_calls": 1, "reserved": 1, "used": 0})
        for key in ("step_ref", "attempt_id", "model_request_id", "cost_status"):
            self.assertEqual(step.get(key), before["steps"][0].get(key), key)
        self.assertEqual(len(client.bodies), 1)

    def test_local_cancel_does_not_reopen_the_one_call_budget(self):
        client, before = self.make_call()
        self.cancel(before)
        status, value, _ = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(len(client.bodies), 1,
                         "cancel reopened max_calls=1 and a second model request was dispatched")
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(len(self.works()["works"][0]["steps"]), 1)

    def test_reopen_keeps_the_original_unknown_reservation(self):
        _, before = self.make_call()
        self.cancel(before)
        self.stop()
        self.start()
        after = self.works()["works"][0]
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["steps"][0]["step_ref"], before["steps"][0]["step_ref"])
        self.assertEqual(after["steps"][0]["status"], "unknown")
        self.assertEqual(after["budget"], {"max_calls": 1, "reserved": 1, "used": 0})

    def test_cancel_cannot_erase_completed_usage_or_result(self):
        client, before = self.make_call("completed")
        self.assertEqual(before["steps"][0]["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(len(before["results"]), 1)
        self.cancel(before)
        after = self.works()["works"][0]
        self.assertEqual(after["steps"], before["steps"])
        self.assertEqual(after["results"], before["results"])
        self.assertEqual(after["budget"], {"max_calls": 1, "reserved": 0, "used": 1})
        self.assertEqual(len(client.bodies), 1)


if __name__ == "__main__":
    names = [name for name in CancelBoundaryProbes.__dict__ if name.startswith("test_")]
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(CancelBoundaryProbes(name) for name in names))
    raise SystemExit(not result.wasSuccessful())
