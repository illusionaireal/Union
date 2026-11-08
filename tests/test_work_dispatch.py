"""Durable automatic call intent and late facts; all model channels are doubles."""
import copy
import json
import unittest
import uuid
from unittest.mock import patch

from ai_union.adapters.core_au_store import CoreAUStore
from ai_union.errors import CoreError, Rejected
from ai_union.model_service import ServiceError
from ai_union.work_transport import ModeldWorkTransport
from tests import test_core_work as support
from tests.test_work_transport import FakeClient, CONNECTION


class CallbackTransport:
    def __init__(self, callback=None, message=None):
        self.callback = callback
        self.message = message or {"content": "controlled completed result", "tool_calls": []}
        self.calls = []

    def chat(self, package, messages, tools):
        self.calls.append(copy.deepcopy(package))
        if self.callback:
            self.callback(package)
        return copy.deepcopy(self.message), {"input_tokens": 11, "output_tokens": 4}


class WorkDispatchTests(support.CoreWorkTests):
    def arrange(self):
        self.work_with_listing()
        self.prepare_materials()
        self.attempt_id = self.start_attempt()
        self.directory, self.intent = self.app.governance.locate(self.au_id)
        return self.request_value()

    def request_value(self, work_id="work-overview"):
        return {"id": str(uuid.uuid4()), "organization_id": self.au_id,
                "base_version": self.state()["version"], "kind": "run_step", "data": {"work_id": work_id}}

    def state(self):
        with self.app.work.store.transaction(self.directory) as cx:
            return CoreAUStore.read_in(cx, self.au_id, creation=self.intent)["au"]

    def card(self):
        return self.state()["work_runtime"]["works"]["work-overview"]

    def test_reservation_and_original_request_are_committed_before_dispatch(self):
        request = self.arrange()
        observed = []
        self.app.work.transport = channel = CallbackTransport(lambda package: observed.append(self.card()))
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertEqual(len(observed[0].get("steps", [])), 1, "no durable reservation at transport entry")
        step = observed[0]["steps"][0]
        self.assertEqual(step["status"], "reserved")
        self.assertEqual(step["command_id"], request["id"])
        self.assertEqual(step["attempt_id"], self.attempt_id)
        self.assertEqual(step["model_request_id"], ModeldWorkTransport._request_id(channel.calls[0]))
        self.assertEqual(self.card()["steps"][0]["step_ref"], step["step_ref"])
        self.assertEqual(self.card()["steps"][0]["status"], "used")

    def test_reentrant_same_request_does_not_dispatch_twice(self):
        request = self.arrange()
        repeated = []
        def callback(package):
            if len(channel.calls) == 1:
                repeated.append(self.app.work.run_step(self.token, request))
        self.app.work.transport = channel = CallbackTransport(callback)
        final = self.app.work.run_step(self.token, request)
        self.assertEqual(len(channel.calls), 1)
        self.assertEqual(repeated[0]["model_outcome"], "unknown")
        self.assertEqual(final["status"], "succeeded", final)
        self.assertEqual(self.app.work.run_step(self.token, request), final)
        self.assertEqual(len(channel.calls), 1)

    def test_another_command_cannot_dispatch_the_same_unresolved_work(self):
        request = self.arrange()
        other = []
        def callback(package):
            if len(channel.calls) == 1:
                other.append(self.app.work.run_step(self.token, self.request_value()))
        self.app.work.transport = channel = CallbackTransport(callback)
        self.app.work.run_step(self.token, request)
        self.assertEqual(len(channel.calls), 1)
        self.assertEqual(other[0]["status"], "rejected")
        self.assertEqual(len(self.card()["steps"]), 1)

    def test_process_interruption_keeps_original_intent_after_reopen(self):
        request = self.arrange()
        def interrupted(package):
            raise KeyboardInterrupt("controlled process interruption")
        self.app.work.transport = CallbackTransport(interrupted)
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, request)
        original = self.card()["steps"][0]
        self.assertEqual(original["status"], "reserved")
        self.stop(); self.start()
        self.app.work.transport = channel = CallbackTransport()
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt["model_outcome"], "unknown")
        self.assertEqual(channel.calls, [])
        self.assertEqual(self.card()["steps"][0], original)

    def test_current_charter_revocation_preserves_completed_usage_without_tools(self):
        request = self.arrange()
        def revoke(package):
            charter = copy.deepcopy(self.state()["charter"])
            charter["allowed_tools"] = [t for t in charter["allowed_tools"] if t not in ("read_document", "list_documents")]
            self.success("amend_charter", {"charter": charter, "reason": "revoked while model was executing"})
        message = {"content": "must not be adopted", "tool_calls": [{"id": "read-late", "type": "function",
                   "function": {"name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]}
        self.app.work.transport = CallbackTransport(revoke, message)
        with patch("ai_union.application.work.documents.read_text") as reader:
            receipt = self.app.work.run_step(self.token, request)
        reader.assert_not_called()
        self.assertEqual(receipt["model_outcome"], "not_adoptable", receipt)
        self.assertEqual(self.card()["steps"][0]["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(self.card().get("tool_calls", []), [])

    def test_closed_attempt_cannot_erase_the_completed_original_call(self):
        request = self.arrange()
        def close(package):
            _, value, _ = self.work_command(self.au_id, "finish_attempt", {"work_id": "work-overview",
                "attempt_id": self.attempt_id, "outcome": "stopped", "reason": "stop during the call"})
            self.assertEqual(value["receipt"]["status"], "succeeded")
        self.app.work.transport = CallbackTransport(close)
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt["model_outcome"], "not_adoptable", receipt)
        self.assertEqual(self.card()["steps"][0]["attempt_id"], self.attempt_id)
        self.assertEqual(self.card()["steps"][0]["status"], "used")

    def test_lost_session_does_not_erase_completed_usage(self):
        request = self.arrange()
        def logout(package):
            self.request("/api/auth/logout", {})
        self.app.work.transport = CallbackTransport(logout)
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt["model_outcome"], "not_adoptable", receipt)
        self.assertEqual(self.card()["steps"][0]["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(self.card().get("results", []), [])

    def test_final_storage_failure_keeps_the_committed_reservation(self):
        request = self.arrange()
        self.app.work.transport = channel = CallbackTransport(message={"content": None, "tool_calls": [
            {"id": "read-before-save", "type": "function", "function": {
                "name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]})
        save = self.app.work.store.save
        def fail_after_dispatch(*args, **kwargs):
            if channel.calls:
                raise OSError("controlled final save failure")
            return save(*args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=fail_after_dispatch):
            with self.assertRaises(OSError):
                self.app.work.run_step(self.token, request)
        step = self.card()["steps"][0]
        self.assertEqual(step["status"], "reserved")
        self.assertEqual(step["command_id"], request["id"])
        self.assertEqual(self.card().get("tool_calls", []), [])
        with self.app.work.store.transaction(self.directory) as cx:
            if cx.execute("SELECT 1 FROM sqlite_master WHERE name='work_model_turns'").fetchone():
                self.assertEqual(cx.execute("SELECT count(*) FROM work_model_turns").fetchone()[0], 0)
        self.assertEqual(self.app.work.run_step(self.token, request)["model_outcome"], "unknown")
        self.assertEqual(len(channel.calls), 1)

    def test_definite_refusal_releases_only_its_original_reservation(self):
        request = self.arrange()
        def refuse(package):
            raise Rejected("controlled pre-execution refusal")
        self.app.work.transport = channel = CallbackTransport(refuse)
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual(self.card()["steps"][0]["status"], "released")
        self.assertEqual(self.works()["works"][0]["budget"]["used"], 0)
        self.assertEqual(self.app.work.run_step(self.token, request), receipt)
        self.assertEqual(len(channel.calls), 1)

    def test_manual_settlement_cannot_release_an_in_flight_automatic_call(self):
        request = self.arrange()
        settlements = []
        def settle(package):
            steps = self.card().get("steps", [])
            if steps:
                settlements.append(self.work_command(self.au_id, "settle_step", {"work_id": "work-overview",
                    "step_id": steps[0]["step_ref"], "status": "released", "reason": "cannot prove remote cancellation"})[1])
        self.app.work.transport = CallbackTransport(settle)
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(len(settlements), 1, "no durable automatic step to protect")
        self.assertEqual(settlements[0]["receipt"]["status"], "rejected")
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertEqual(self.card()["steps"][0]["status"], "used")

    def unknown_call(self):
        request = self.arrange()
        def timeout(package):
            raise ServiceError("controlled response loss")
        self.app.work.transport = CallbackTransport(timeout)
        receipt = self.app.work.run_step(self.token, request)
        return request, receipt["step"]

    def test_reconciliation_queries_original_request_without_post_or_adopting_content(self):
        request, step_id = self.unknown_call()
        client = FakeClient()
        seen = []
        original = client.request
        def lookup(request_id, au_id):
            seen.append((request_id, au_id))
            return original(request_id, au_id)
        client.request = lookup
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, CONNECTION)
        _, value, _ = self.work_command(self.au_id, "reconcile_step", {"work_id": "work-overview",
            "step_id": step_id, "status": "used", "reason": "query original request"})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(seen, [(self.card()["steps"][0]["model_request_id"], self.au_id)])
        self.assertEqual(client.bodies, [])
        self.assertEqual(self.card()["steps"][0]["usage"], {"input_tokens": 11, "output_tokens": 4})
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(self.app.work.run_step(self.token, request)["model_outcome"], "unknown",
                         "the old receipt is immutable; current state carries reconciliation")

    def test_missing_remote_request_never_releases_an_unknown_reservation(self):
        _, step_id = self.unknown_call()
        client = FakeClient()
        seen = []
        def missing(request_id, au_id):
            seen.append(request_id)
            raise ServiceError("not found", 404)
        client.request = missing
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, CONNECTION)
        self.work_command(self.au_id, "reconcile_step", {"work_id": "work-overview",
            "step_id": step_id, "status": "released", "reason": "404 is not proof of no execution"})
        self.assertEqual(len(seen), 1)
        self.assertEqual(client.bodies, [])
        self.assertEqual(self.card()["steps"][0]["status"], "unknown")
        self.assertEqual(self.works()["works"][0]["budget"]["reserved"], 1)

    def test_another_work_can_finish_while_the_first_call_is_in_flight(self):
        request = self.arrange()
        other_data = support.work_data(work_id="work-second", member_id="member-second", binding_id="binding-second",
            mandate_id="mandate-second", definition_id="definition-second", materials_root="other-docs", max_calls=2)
        self.assertEqual(self.work(data=other_data)[1]["receipt"]["status"], "succeeded")
        self.work_command(self.au_id, "start_attempt", {"work_id": "work-second"})
        request["base_version"] = self.state()["version"]
        receipts = []
        def other_work(package):
            self.app.work.transport = CallbackTransport()
            receipts.append(self.app.work.run_step(self.token, self.request_value("work-second")))
        self.app.work.transport = CallbackTransport(other_work)
        receipt = self.app.work.run_step(self.token, request)
        self.assertTrue(receipts[0]["result"], receipts)
        self.assertTrue(receipt["result"], receipt)
        self.assertEqual(self.card()["steps"][0]["status"], "used")

    def test_loop_receipt_uses_the_actual_committed_version(self):
        request = self.arrange()
        request["kind"] = "run_loop"
        self.app.work.transport = CallbackTransport()
        receipt = self.app.work.run_loop(self.token, request)
        self.assertEqual(receipt["version"], self.state()["version"])
        self.assertEqual(receipt["turns"], 1)
        self.assertEqual(receipt["usage"], {"input_tokens": 11, "output_tokens": 4})

    def test_pending_request_id_is_reserved_across_command_kinds(self):
        request = self.arrange()
        replies = []
        def collide(package):
            replies.append(self.work_command(self.au_id, "finish_attempt", {"work_id": "work-overview",
                "attempt_id": self.attempt_id, "outcome": "stopped", "reason": "same ID different command"},
                request_id=request["id"]))
        self.app.work.transport = CallbackTransport(collide)
        try:
            self.app.work.run_step(self.token, request)
        except CoreError:
            pass
        self.assertEqual(replies[0][0], 409, replies)
        self.assertEqual(self.card()["steps"][0]["status"], "used")

    def context_first(self):
        request = self.arrange()
        from tests.test_work_context import tool_call
        self.app.work.transport = CallbackTransport(message=tool_call())
        self.assertEqual(self.app.work.run_step(self.token, request)["tool_calls"], 1)

    def test_root_revocation_during_inference_prevents_adopting_old_context(self):
        self.context_first()
        self.app.work.transport = CallbackTransport(lambda _: (self.app.root / "document-roots.json").unlink())
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt.get("model_outcome"), "not_adoptable", receipt)
        self.assertEqual(self.card()["steps"][-1]["status"], "used")
        self.assertEqual(self.card().get("results", []), [])

    def test_factory_revocation_cannot_redisclose_old_context(self):
        self.context_first()
        channel = CallbackTransport()
        def factory(au_id, connection):
            (self.app.root / "document-roots.json").unlink()
            return channel
        self.app.work.transport = None
        self.app.work.transport_factory = factory
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(channel.calls, [])
        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual(len(self.card()["steps"]), 1)

    def test_reconciliation_validates_the_public_command_before_lookup(self):
        _, step_id = self.unknown_call()
        for data in ({}, {"work_id": "work-overview", "step_id": step_id, "status": "invented", "reason": "x"}):
            with self.subTest(data=data):
                status, _, _ = self.work_command(self.au_id, "reconcile_step", data)
                self.assertEqual(status, 400)

    def test_same_loop_reentry_does_not_freeze_an_intermediate_receipt(self):
        request = self.arrange()
        request["kind"] = "run_loop"
        nested = []
        def reenter(package):
            if not nested:
                nested.append(self.app.work.run_loop(self.token, request))
        self.app.work.transport = channel = CallbackTransport(reenter)
        receipt = self.app.work.run_loop(self.token, request)
        self.assertEqual(len(channel.calls), 1)
        self.assertEqual(receipt["turns"], 1, receipt)
        self.assertTrue(receipt["result"], receipt)
        self.assertEqual(self.app.work.run_loop(self.token, request), receipt)

    def test_loop_replay_after_parent_save_loss_reads_completed_last_call(self):
        self.arrange()
        self.app.work.transport = channel = CallbackTransport()
        for _ in range(3):
            self.app.work.run_step(self.token, self.request_value())
        request = self.request_value()
        request["kind"] = "run_loop"
        save = self.app.work.store_receipt
        def fail_parent(directory, intent, incoming, principal, receipt):
            if incoming["id"] == request["id"]:
                raise OSError("controlled parent receipt failure")
            return save(directory, intent, incoming, principal, receipt)
        with patch.object(self.app.work, "store_receipt", side_effect=fail_parent):
            with self.assertRaises(OSError):
                self.app.work.run_loop(self.token, request)
        self.assertEqual(self.works()["works"][0]["budget"]["used"], 4)
        receipt = self.app.work.run_loop(self.token, request)
        self.assertTrue(receipt["result"], receipt)
        self.assertEqual(receipt["turns"], 1)
        self.assertEqual(len(channel.calls), 4, "recover the completed child without a fifth call")

    def test_final_save_failure_can_be_reconciled_without_restarting_the_service(self):
        request = self.arrange()
        self.app.work.transport = channel = CallbackTransport()
        save = self.app.work.store.save
        def fail_final(*args, **kwargs):
            if channel.calls:
                raise OSError("controlled final save failure")
            return save(*args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=fail_final):
            with self.assertRaises(OSError):
                self.app.work.run_step(self.token, request)
        step = self.card()["steps"][0]
        client = FakeClient()
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, CONNECTION)
        _, value, _ = self.work_command(self.au_id, "reconcile_step", {"work_id": "work-overview",
            "step_id": step["step_ref"], "status": "used", "reason": "read original after storage recovers"})
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(client.bodies, [])

    def test_root_revocation_at_reservation_commit_refuses_before_post(self):
        self.context_first()
        self.app.work.transport = channel = CallbackTransport()
        save = self.app.work.store.save
        def revoke_at_commit(cx, state, charter, request, *args, **kwargs):
            value = save(cx, state, charter, request, *args, **kwargs)
            if request["kind"] == "work_dispatch_prepared":
                (self.app.root / "document-roots.json").unlink()
            return value
        with patch.object(self.app.work.store, "save", side_effect=revoke_at_commit):
            receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(channel.calls, [])
        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual(self.card()["steps"][-1]["status"], "released")


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkDispatchTests(name) for name in WorkDispatchTests.__dict__ if name.startswith("test_"))
