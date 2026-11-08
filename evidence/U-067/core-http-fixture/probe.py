"""Real V1 HTTP requests: slow completion, explicit timeout and no POST retry."""
from contextlib import contextmanager
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests import test_core_creation as core_http


class CoreHTTPFixtureTests(unittest.TestCase):
    setUp = core_http.CoreCreationTests.setUp
    start = core_http.CoreCreationTests.start
    stop = core_http.CoreCreationTests.stop
    request = core_http.CoreCreationTests.request
    setup_account = core_http.CoreCreationTests.setup_account
    create = core_http.CoreCreationTests.create

    @contextmanager
    def delayed_creation(self, delay):
        original = self.app.command
        seen = []
        finished = threading.Event()

        def delayed(token, request):
            seen.append(request["id"])
            try:
                time.sleep(delay)
                return original(token, request)
            finally:
                finished.set()

        with patch.object(self.app, "command", side_effect=delayed):
            try:
                yield seen, finished
            finally:
                if seen:
                    self.assertTrue(finished.wait(30), "original creation must finish before cleanup")

    def saved_receipt(self, request_id):
        status, result, _ = self.request("/api/v1/receipts?id=" + request_id)
        self.assertEqual(status, 200, result)
        receipt = result["receipt"]
        self.assertEqual(receipt["id"], request_id)
        self.assertEqual(receipt["status"], "succeeded")
        with self.app.read_catalog() as cx:
            rows = cx.execute("SELECT id FROM organizations").fetchall()
        self.assertEqual([row["id"] for row in rows], [receipt["organization_id"]])
        return receipt

    def test_default_wait_returns_the_one_original_persisted_creation(self):
        request = core_http.creation("slow-core-create")
        with self.delayed_creation(5.5) as (seen, _):
            receipt = self.create(request)
        self.assertEqual(seen, [request["id"]])
        self.assertEqual(self.saved_receipt(request["id"]), receipt)

    def test_explicit_timeout_still_raises_without_replaying_the_committed_post(self):
        request = core_http.creation("timed-out-core-create")
        with self.delayed_creation(0.5) as (seen, finished):
            with self.assertRaises(TimeoutError):
                self.request("/api/commands", request, timeout=0.1)
            self.assertTrue(finished.wait(30))
        self.assertEqual(seen, [request["id"]])
        self.saved_receipt(request["id"])
        self.assertEqual(seen, [request["id"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
