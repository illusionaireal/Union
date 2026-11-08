"""Concurrent preflight failures cannot settle a different dispatch invocation."""
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from ai_union.errors import Rejected
from ai_union.model_service import ServiceError
from tests.test_work_dispatch import CallbackTransport, WorkDispatchTests


class WorkPreflightRaceTests(WorkDispatchTests):
    def race(self, failure, *, unknown=False):
        request = self.arrange()
        preflight_entered = threading.Event()
        dispatched = threading.Event()
        observed = {}

        def callback(package):
            dispatched.set()
            observed["duplicate"] = duplicate.result(timeout=10)
            with self.app.work.store.transaction(self.directory) as cx:
                observed["terminal_before_owner_returns"] = cx.execute(
                    "SELECT receipt FROM governance_commands WHERE id=?", (request["id"],)).fetchone()
            observed["original_step"] = self.card()["steps"][0]
            if unknown:
                raise ServiceError("controlled lost transport response")

        channel = CallbackTransport(callback)
        constructions = []

        def factory(au_id, connection):
            constructions.append(au_id)
            if len(constructions) == 1:
                preflight_entered.set()
                if not dispatched.wait(timeout=10):
                    raise AssertionError("owner never reached transport")
                if failure is not None:
                    raise failure
                return None
            return channel

        self.app.work.transport = None
        self.app.work.transport_factory = factory
        with ThreadPoolExecutor(max_workers=1) as pool:
            duplicate = pool.submit(self.app.work.run_step, self.token, request)
            try:
                self.assertTrue(preflight_entered.wait(timeout=10))
                receipt = self.app.work.run_step(self.token, request)
            finally:
                dispatched.set()
            duplicate.result(timeout=10)
        self.assertEqual(len(constructions), 2)
        self.assertEqual(len(channel.calls), 1)
        self.assertEqual(observed["original_step"]["command_id"], request["id"])
        self.assertEqual(observed["original_step"]["model_request_id"], channel.calls[0]["run_id"])
        return request, receipt, observed, channel

    def assert_completion(self, failure):
        request, receipt, observed, channel = self.race(failure)
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertIsNone(observed["terminal_before_owner_returns"])
        self.assertEqual(observed["duplicate"]["model_outcome"], "unknown")
        self.assertEqual(observed["duplicate"]["model_request_id"], channel.calls[0]["run_id"])
        step = self.card()["steps"][0]
        self.assertEqual(step["status"], "used")
        self.assertEqual(step["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(len(self.card()["results"]), 1)
        self.assertEqual(self.app.work.run_step(self.token, request), receipt)
        self.assertEqual(len(channel.calls), 1)

    def test_completed_call_survives_duplicate_factory_refusal(self):
        self.assert_completion(Rejected("controlled duplicate preflight refusal"))

    def test_completed_call_survives_duplicate_factory_error(self):
        self.assert_completion(RuntimeError("controlled duplicate construction error"))

    def test_completed_call_survives_duplicate_missing_channel(self):
        self.assert_completion(None)

    def test_unknown_call_keeps_original_reservation_after_duplicate_refusal_and_restart(self):
        request, receipt, observed, channel = self.race(Rejected("duplicate refused"), unknown=True)
        self.assertEqual(receipt.get("model_outcome"), "unknown", receipt)
        self.assertIsNone(observed["terminal_before_owner_returns"])
        self.assertEqual(observed["duplicate"]["model_outcome"], "unknown")
        original = self.card()["steps"][0]
        self.assertEqual(original["status"], "unknown")
        self.assertEqual(original["model_request_id"], channel.calls[0]["run_id"])
        self.assertNotIn("usage", original)
        self.stop()
        self.start()
        self.app.work.transport = reopened = CallbackTransport()
        self.assertEqual(self.app.work.run_step(self.token, request), receipt)
        self.assertEqual(self.card()["steps"][0], original)
        self.assertEqual(reopened.calls, [])

    def test_late_preflight_failure_returns_already_completed_original_receipt(self):
        request = self.arrange()
        completed = []
        channel = CallbackTransport()

        def factory(au_id, connection):
            self.app.work.transport = channel
            completed.append(self.app.work.run_step(self.token, request))
            raise Rejected("duplicate failed after owner committed")

        self.app.work.transport = None
        self.app.work.transport_factory = factory
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt, completed[0])
        self.assertEqual(receipt["status"], "succeeded")
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(len(channel.calls), 1)

    def test_ordinary_preflight_failure_has_no_call_reservation_or_version_change(self):
        request = self.arrange()

        def factory(au_id, connection):
            raise Rejected("controlled failure before any intent")

        self.app.work.transport = None
        self.app.work.transport_factory = factory
        before = self.state()
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual((receipt["status"], receipt["effect"]), ("rejected", "none"))
        self.assertEqual(self.state(), before)
        self.assertEqual(self.card().get("steps", []), [])
        self.assertEqual(self.app.work.run_step(self.token, request), receipt)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkPreflightRaceTests(name) for name in
                              WorkPreflightRaceTests.__dict__ if name.startswith("test_"))
