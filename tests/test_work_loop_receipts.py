"""A later admission refusal must not hide completed loop calls or their usage."""
import unittest
from unittest.mock import patch

from ai_union.errors import CoreError, Rejected
from tests.test_core_work import work_data
from tests.test_work_context import tool_call
from tests.test_work_dispatch import CallbackTransport, WorkDispatchTests


class WorkLoopReceiptTests(WorkDispatchTests):
    def loop_request(self):
        request = self.arrange()
        request["kind"] = "run_loop"
        self.app.work.transport = self.channel = CallbackTransport(message=tool_call())
        return request

    def other_work(self):
        value = work_data(work_id="independent-work", member_id="independent-member",
                          binding_id="independent-binding", mandate_id="independent-mandate",
                          definition_id="independent-definition", materials_root="other-docs")
        self.assertEqual(self.work(data=value)[1]["receipt"]["status"], "succeeded")

    def after_first_turn(self, request, change):
        run_step = self.app.work.run_step

        def run_then_change(token, incoming):
            receipt = run_step(token, incoming)
            if incoming["id"] == request["id"] + "-t1":
                change()
            return receipt

        with patch.object(self.app.work, "run_step", side_effect=run_then_change):
            status, value, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(status, 200, value)
        return value["receipt"]

    def assert_completed_facts(self, receipt):
        self.assertEqual(receipt["status"], "rejected", receipt)
        self.assertEqual(receipt["turns"], 1)
        self.assertEqual(receipt["tool_calls"], 1)
        self.assertEqual(receipt["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertFalse(receipt["result"])
        self.assertEqual(receipt["version"], self.state()["version"])
        self.assertEqual(len(self.channel.calls), 1, "the refused next turn never dispatched")
        self.assertEqual([step["status"] for step in self.card()["steps"]], ["used"])
        self.assertEqual(self.card().get("results", []), [])

    def test_version_change_between_turns_returns_facts_and_replays_after_restart(self):
        request = self.loop_request()
        receipt = self.after_first_turn(request, self.other_work)
        self.assert_completed_facts(receipt)
        self.assertEqual(self.app.work.run_loop(self.token, request), receipt)
        self.stop()
        self.start()
        self.app.work.transport = channel = CallbackTransport()
        self.assertEqual(self.app.work.run_loop(self.token, request), receipt)
        self.assertEqual(channel.calls, [])

    def test_logout_between_turns_preserves_parent_receipt_without_new_dispatch(self):
        request = self.loop_request()
        receipt = self.after_first_turn(request, lambda: self.request("/api/auth/logout", {}))
        self.assert_completed_facts(receipt)
        stored = self.app.work.store.receipt(self.directory, self.au_id, request["id"],
                                             self.principal, self.intent)
        self.assertEqual(stored, receipt)
        status, _, _ = self.request("/api/v1/governance/receipts?organization_id=" + self.au_id
                                    + "&id=" + request["id"])
        self.assertIn(status, (401, 403, 409), "the revoked session still cannot query receipts")

    def test_governor_handover_between_turns_keeps_original_issuer_receipt(self):
        request = self.loop_request()
        successor_token, successor_id = self.participant("loop-successor")

        def handover():
            self.success("nominate_governor", {"principal_id": successor_id, "reason": "controlled handover"})
            self.success("accept_governance", {"reason": "accept responsibility"}, token=successor_token)

        receipt = self.after_first_turn(request, handover)
        self.assert_completed_facts(receipt)
        status, value, _ = self.request("/api/v1/governance/receipts?organization_id=" + self.au_id
                                        + "&id=" + request["id"])
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"], receipt)
        self.assertEqual(self.app.work.run_loop(self.token, request), receipt)
        self.assertEqual(len(self.channel.calls), 1)

    def test_first_turn_admission_refusal_does_not_invent_a_completed_call(self):
        request = self.loop_request()
        run_step = self.app.work.run_step

        def change_then_run(token, incoming):
            self.other_work()
            return run_step(token, incoming)

        with patch.object(self.app.work, "run_step", side_effect=change_then_run):
            status, value, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual((receipt["turns"], receipt["tool_calls"], receipt["effect"]), (0, 0, "none"))
        self.assertEqual(receipt["usage"], {"input_tokens": 0, "output_tokens": 0})
        self.assertEqual(self.channel.calls, [])
        self.assertEqual(self.card().get("steps", []), [])

    def assert_uncommitted_result_keeps_reservation(self, error):
        request = self.loop_request()
        save = self.app.work.store.save

        def fail_final(*args, **kwargs):
            if self.channel.calls:
                raise error
            return save(*args, **kwargs)

        with patch.object(self.app.work.store, "save", side_effect=fail_final):
            with self.assertRaises(type(error)):
                self.app.work.run_loop(self.token, request)
        self.assertEqual([step["status"] for step in self.card()["steps"]], ["reserved"])
        self.assertEqual(self.card().get("tool_calls", []), [])
        with self.app.work.store.transaction(self.directory) as cx:
            self.assertIsNone(self.app.work.store.existing(cx, request, self.principal))
        receipt = self.app.work.run_loop(self.token, request)
        self.assertEqual(receipt["model_outcome"], "unknown")
        self.assertEqual(len(self.channel.calls), 1)
        self.assertEqual([step["status"] for step in self.card()["steps"]], ["reserved"])

    def test_late_invariant_rejection_cannot_be_reported_as_not_dispatched(self):
        self.assert_uncommitted_result_keeps_reservation(Rejected("controlled final invariant rejection"))

    def test_integrity_failure_cannot_be_reported_as_admission_refusal(self):
        self.assert_uncommitted_result_keeps_reservation(CoreError("incompatible_state", "controlled integrity failure"))

    def test_storage_failure_cannot_be_reported_as_admission_refusal(self):
        self.assert_uncommitted_result_keeps_reservation(OSError("controlled final storage failure"))


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkLoopReceiptTests(name) for name in WorkLoopReceiptTests.__dict__
                              if name.startswith("test_"))
