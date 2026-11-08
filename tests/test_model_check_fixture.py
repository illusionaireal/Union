"""The HTTP fixture waits for an original check without dispatching a retry."""
import threading
import unittest
from contextlib import contextmanager

from tests.model_access_support import ModelAccessCase


class ModelCheckFixtureTests(ModelAccessCase):
    def prepare_check(self):
        self.saved()
        self.allow_documents()
        self.resource_grant(2)

    @contextmanager
    def pending_original(self, request_id):
        entered, release = threading.Event(), threading.Event()

        def hold():
            entered.set()
            if not release.wait(30):
                raise AssertionError("Test must release the original model request")

        self.provider.before_result = hold
        receipt, _ = self.start_check(request_id)
        try:
            self.assertTrue(entered.wait(3), "Original model request did not enter")
            yield receipt["check_id"], release
        finally:
            release.set()
            self.wait_for("checks", receipt["check_id"])

    def assert_original_pair(self, check_id, result):
        self.assertEqual(result["id"], check_id)
        self.assertEqual(result["status"], "succeeded")
        ids = [body["id"] for path, body in self.provider.posts if path == "/v1/requests"]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual(set(ids), set(result["attempt_ids"]))

    def test_default_wait_observes_delayed_original_check(self):
        self.prepare_check()
        with self.pending_original("fixture-delayed-original") as (check_id, release):
            timer = threading.Timer(5.5, release.set)
            timer.start()
            try:
                result = self.wait_for("checks", check_id)
            finally:
                timer.cancel()
                timer.join()
            self.assert_original_pair(check_id, result)

    def test_explicit_short_wait_still_fails_then_queries_same_check(self):
        self.prepare_check()
        with self.pending_original("fixture-explicit-short") as (check_id, release):
            with self.assertRaisesRegex(AssertionError, "Bounded test job did not complete"):
                self.wait_for("checks", check_id, timeout=0.05)
            self.assertEqual(len(self.provider.requests), 1)
            release.set()
            result = self.wait_for("checks", check_id)
            self.assert_original_pair(check_id, result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
