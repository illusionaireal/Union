"""Original observations and concurrent recovery retain facts without replay."""
from contextlib import closing
import copy
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from ai_union.application.model_checks import usage_from
from ai_union.model_service import ServiceError
from tests.model_access_support import ModelAccessCase


def event(request_id, seq=1, **usage):
    return {"request_id": request_id, "seq": seq, "type": "usage",
            "created_at": "2026-11-06", "payload": usage}


class CoreModelObservationTests(ModelAccessCase):
    def ready(self):
        self.saved()
        self.allow_documents()
        self.resource_grant(6)

    def private_result(self):
        with closing(sqlite3.connect(self.database())) as cx:
            row = cx.execute("SELECT result FROM model_attempts ORDER BY rowid LIMIT 1").fetchone()
        return json.loads(row[0]) if row and row[0] else None

    def assert_no_tool(self):
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], 0)

    def test_next_poll_failure_preserves_observed_usage(self):
        self.ready()
        actual = self.provider.request
        polls = []

        def request(request_id, au_id):
            polls.append(request_id)
            if len(polls) > 1:
                raise ServiceError("model_service_unavailable")
            return actual(request_id, au_id) | {"state": "streaming", "result": None}

        def events(request_id, au_id, after=0):
            return {"events": [event(request_id, input_tokens=37, output_tokens=9,
                                      cost_minor=4, currency="USD")] if after == 0 else []}

        with patch.object(self.provider, "request", side_effect=request), patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "unknown")
        self.assertEqual(check["attempts"][0]["usage"]["input_tokens"], 37)
        self.assertEqual(check["attempts"][0]["usage"]["cost_minor"], 4)
        self.assertEqual(len(self.private_result()["events"]), 1)
        self.assertEqual(len(self.provider.requests), 1)
        self.assert_no_tool()

    def test_second_event_page_failure_preserves_first_page(self):
        self.ready()
        actual = self.provider.request

        def request(request_id, au_id):
            return actual(request_id, au_id) | {"state": "streaming", "result": None}

        def events(request_id, au_id, after=0):
            if after:
                raise ServiceError("model_service_unavailable")
            items = [event(request_id, input_tokens=37, output_tokens=9)]
            items.extend({"request_id": request_id, "seq": seq, "type": "native_event",
                          "payload": {}, "created_at": "2026-11-06"} for seq in range(2, 501))
            return {"events": items}

        with patch.object(self.provider, "request", side_effect=request), patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "unknown")
        self.assertEqual(check["attempts"][0]["usage"]["input_tokens"], 37)
        self.assertEqual(check["attempts"][0]["usage"]["observed_through_seq"], 500)
        self.assertEqual(len(self.private_result()["events"]), 500)
        self.assertEqual(len(self.provider.requests), 1)
        self.assert_no_tool()

    def test_cancel_after_observation_retains_usage_without_followup(self):
        self.ready()
        actual = self.provider.request
        observed = threading.Event()
        runner = self.app.models.check_runner
        actual_observe = runner.observe

        def request(request_id, au_id):
            return actual(request_id, au_id) | {"state": "streaming", "result": None}

        def events(request_id, au_id, after=0):
            return {"events": [event(request_id, input_tokens=37, output_tokens=9)] if after == 0 else []}

        def observe(*args):
            result = actual_observe(*args)
            observed.set()
            return result

        with patch.object(self.provider, "request", side_effect=request), patch.object(self.provider, "events", side_effect=events), patch.object(runner, "observe", side_effect=observe):
            receipt, _ = self.start_check()
            self.assertTrue(observed.wait(2), "Expected a committed observation before cancellation")
            self.model_success("cancel_model_check", {"check_id": receipt["check_id"], "reason": "Review cancellation"})
            self.app.join_jobs()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "unknown")
        self.assertEqual(check["attempts"][0]["usage"]["input_tokens"], 37)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertEqual(self.models()["resources"]["reserved_calls"], 1)
        self.assert_no_tool()

    def test_identical_replayed_sequence_does_not_fail_original_check(self):
        self.ready()

        def events(request_id, au_id, after=0):
            item = event(request_id, input_tokens=24, output_tokens=10)
            return {"events": [item, copy.deepcopy(item)] if after == 0 else []}

        with patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "succeeded", check["message"])
        self.assertEqual(len(self.private_result()["events"]), 1)
        self.assertEqual(len(self.provider.requests), 2)

    def test_conflicting_sequence_keeps_original_observed_prefix(self):
        self.ready()
        actual = self.provider.request

        def request(request_id, au_id):
            return actual(request_id, au_id) | {"state": "streaming", "result": None}

        def events(request_id, au_id, after=0):
            return {"events": [event(request_id, input_tokens=37, output_tokens=9),
                                event(request_id, input_tokens=999, output_tokens=999)]}

        with patch.object(self.provider, "request", side_effect=request), patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "failed")
        self.assertEqual(len(self.provider.requests), 1)
        self.assert_no_tool()
        self.assertEqual(check["attempts"][0]["usage"]["input_tokens"], 37,
                         "Rejecting a conflicting event must not erase its already observed original")
        self.assertEqual([item["seq"] for item in self.private_result()["events"]], [1])

    def test_late_start_failure_does_not_overwrite_successful_explicit_recovery(self):
        self.ready()
        service = self.app.models
        actual_start = threading.Thread.start
        actual_state = service.state
        failure_thread = []
        blocked = threading.Event()
        release = threading.Event()
        outcome = []
        request_id = "review-start-race"

        def start(thread):
            target = getattr(thread, "_target", None)
            if not failure_thread and getattr(target, "__qualname__", "").startswith("ModelAccessService.spawn."):
                failure_thread.append(threading.get_ident())
                raise RuntimeError("Controlled first start failure")
            return actual_start(thread)

        def state(au_id):
            if failure_thread and threading.get_ident() == failure_thread[0] and not blocked.is_set():
                blocked.set()
                if not release.wait(4):
                    raise AssertionError("Recovery did not release start failure recorder")
            return actual_state(au_id)

        def submit():
            try:
                outcome.append(self.start_check(request_id))
            except BaseException as error:
                outcome.append(error)

        with patch("ai_union.application.model_access.threading.Thread.start", new=start), patch.object(service, "state", side_effect=state):
            submitter = threading.Thread(target=submit)
            submitter.start()
            reconciled = threading.Event()
            recovery_errors = []
            def reconcile():
                try:
                    self.model_success("reconcile_model_check", {"check_id": request_id})
                    self.wait_for("checks", request_id)
                except BaseException as error:
                    recovery_errors.append(error)
                finally:
                    reconciled.set()
            recovery = threading.Thread(target=reconcile)
            try:
                self.assertTrue(blocked.wait(2), "Expected the controlled failure recorder")
                # Force recovery to finish before the late recorder only when
                # the service permits that interleaving. A correct owner holds
                # its mutex, so recovery must instead proceed after release.
                can_interleave = self.app.mutex.acquire(blocking=False)
                if can_interleave:
                    self.app.mutex.release()
                recovery.start()
                if can_interleave:
                    self.assertTrue(reconciled.wait(4), "Concurrent recovery did not finish")
                    self.assertEqual(self.wait_for("checks", request_id)["status"], "succeeded")
            finally:
                release.set()
                submitter.join(4)
                if recovery.ident is not None:
                    recovery.join(4)
            self.assertFalse(recovery_errors, recovery_errors)
        self.assertFalse(submitter.is_alive())
        self.assertEqual(len(outcome), 1)
        if isinstance(outcome[0], BaseException):
            raise outcome[0]
        final = self.wait_for("checks", request_id)
        self.assertEqual(len(self.provider.requests), 2)
        self.assertEqual(final["status"], "succeeded",
                         "A stale start-failed observer must not overwrite the completed original check")


class CoreModelUsageFactsTests(unittest.TestCase):
    def test_invalid_later_values_do_not_erase_last_valid_observation(self):
        value = usage_from({"events": [event("r", input_tokens=37, output_tokens=9, cost_minor=4, currency="USD")],
                            "result": {"usage": {"input_tokens": -1, "output_tokens": "unknown", "cost_minor": -1}}})
        self.assertEqual((value["input_tokens"], value["output_tokens"]), (37, 9))
        self.assertEqual((value["cost_minor"], value["currency"]), (4, "USD"))

    def test_currency_only_update_does_not_relabel_an_old_charge(self):
        value = usage_from({"events": [event("r", cost_minor=4, currency="USD"),
                                      event("r", seq=2, currency="JPY")]})
        self.assertNotEqual((value["cost_minor"], value["currency"]), (4, "JPY"),
                            "No event ever reported JPY 4")


if __name__ == "__main__":
    unittest.main(verbosity=2)
