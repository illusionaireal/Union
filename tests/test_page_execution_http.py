"""U084: original loop receipt and result survive a real HTTP server restart."""
import unittest

from tests.test_core_work_http import WorkHttpChainTests
from tests.test_work_transport_http import ModeldDouble


class PageExecutionHTTPTests(WorkHttpChainTests):
    def setUp(self):
        previous = {key: getattr(ModeldDouble, key) for key in ("result", "seen", "state", "post_status")}
        self.addCleanup(lambda: [setattr(ModeldDouble, key, value) for key, value in previous.items()])
        super().setUp()

    def test_original_loop_receipt_and_result_reopen_without_model_replay(self):
        self.prepare_work()
        ModeldDouble.result = {"message": {"role": "assistant", "content": "# U084 controlled result\n"},
                              "usage": {"input_tokens": 11, "output_tokens": 4}}
        ModeldDouble.seen = []
        status, value, _ = self.work_command(self.au_id, "run_loop", {"work_id": "work-http"})
        self.assertEqual(status, 200, value)
        original = value["receipt"]
        self.assertEqual(original["status"], "succeeded", original)
        self.assertTrue(original["result"], original)
        dispatched = [x for x in ModeldDouble.seen if x[0] == "POST"]
        self.assertEqual(len(dispatched), 1)
        self.stop()
        self.start()
        status, found, _ = self.request("/api/v1/governance/receipts?organization_id=" + self.au_id
                                        + "&id=" + original["id"])
        self.assertEqual(status, 200, found)
        self.assertEqual(found["receipt"], original)
        status, work, _ = self.request("/api/v1/work?organization_id=" + self.au_id)
        self.assertEqual(status, 200, work)
        result = work["works"][0]["results"][0]
        status, body, _ = self.request("/api/v1/work/results?organization_id=" + self.au_id + "&id=" + result["id"])
        self.assertEqual(status, 200, body)
        self.assertIn("U084 controlled result", body["content"])
        self.assertEqual(len([x for x in ModeldDouble.seen if x[0] == "POST"]), 1)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([PageExecutionHTTPTests("test_original_loop_receipt_and_result_reopen_without_model_replay")])
