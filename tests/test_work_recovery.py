"""U-092 original-attempt recovery through real HTTP and SQLite, no real models."""
import copy
import json
import unittest
from unittest.mock import patch

from ai_union.model_service import ServiceError
from ai_union.work_transport import ModeldWorkTransport

from tests.test_work_dispatch import WorkDispatchTests, CallbackTransport


class RecoveryClient:
    def __init__(self):
        self.requests = {}
        self.posts = []
        self.lookups = []
        self.crash_post = False
        self.authorized = True

    def call(self, method, path, body=None):
        assert method == "POST" and path == "/v1/requests"
        assert body["id"] not in self.requests, "original model request POST replay"
        self.posts.append(copy.deepcopy(body))
        self.requests[body["id"]] = copy.deepcopy(body)
        if self.crash_post:
            raise KeyboardInterrupt("controlled process loss after POST")
        return {"id": body["id"], "state": "queued"}

    def request(self, request_id, au_id):
        import hashlib
        self.lookups.append((request_id, au_id))
        body = self.requests.get(request_id)
        if body is None:
            raise ServiceError("not_found", 404)
        digest = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")).encode("utf-8")).hexdigest()
        return {"id": request_id, "au_id": au_id, "state": "completed", "request_digest": digest,
                "action_authorized": self.authorized,
                "result": {"message": {"content": "original recovered result", "tool_calls": []},
                           "usage": {"input_tokens": 13, "output_tokens": 6}}}

    def events(self, request_id, au_id, after=0):
        return {"events": []}


class WorkRecoveryTests(WorkDispatchTests):
    def wire(self, client=None):
        client = client or RecoveryClient()
        connection = self.state()["model_access"]["connections"]["connection-a"]
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, connection)
        return client

    def recover(self, **changes):
        data = {"work_id": "work-overview", "attempt_id": self.attempt_id,
                "reason": "recover the original execution after controlled host restart"}
        data.update(changes)
        return self.work_command(self.au_id, "recover_work", data)

    def test_dispatching_recovery_only_gets_original_digest_and_adopts_same_step(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, request)
        original = copy.deepcopy(self.card()["steps"][0])
        self.assertEqual(original.get("dispatch_phase"), "dispatching")
        self.assertEqual(len(original.get("request_sha256", "")), 64)
        self.stop(); self.start()
        self.wire(client)
        status, value, _ = self.recover()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        step = self.card()["steps"][0]
        self.assertEqual((step["step_ref"], step["attempt_id"], step["model_request_id"]),
                         (original["step_ref"], self.attempt_id, original["model_request_id"]))
        self.assertEqual(step["status"], "used", step)
        self.assertEqual(step["usage"], {"input_tokens": 13, "output_tokens": 6})
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(client.lookups, [(step["model_request_id"], self.au_id)] * 2)
        self.assertEqual(self.card()["results"][0]["content"], "original recovered result")

    def test_proven_prepared_recovery_dispatches_frozen_original_request_once(self):
        request = self.arrange()
        client = self.wire()
        original = self.app.work.store.save
        def interrupt_after_prepare(cx, state, charter, command, *args, **kwargs):
            original(cx, state, charter, command, *args, **kwargs)
            if command["kind"] == "work_dispatch_prepared":
                self.assertEqual(client.posts, [])
        # A crash at the next dispatching transaction leaves the prepare commit intact.
        def before_dispatch(cx, state, charter, command, *args, **kwargs):
            if command["kind"] == "work_dispatch_dispatching":
                raise KeyboardInterrupt("controlled loss before dispatching commit")
            return interrupt_after_prepare(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=before_dispatch):
            with self.assertRaises(KeyboardInterrupt):
                self.app.work.run_step(self.token, request)
        original_step = copy.deepcopy(self.card()["steps"][0])
        self.assertEqual(original_step.get("dispatch_phase"), "prepared")
        self.stop(); self.start()
        self.wire(client)
        status, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(client.posts[0]["id"], original_step["model_request_id"])
        self.assertEqual(self.card()["steps"][0]["status"], "used")

    def test_completed_fact_survives_adoption_crash_and_recovers_without_network(self):
        request = self.arrange()
        client = self.wire()
        save = self.app.work.store.save
        def fail_adoption(cx, state, charter, command, *args, **kwargs):
            if command["kind"] == "work_dispatch_adopted":
                raise KeyboardInterrupt("controlled crash in adoption transaction")
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=fail_adoption):
            with self.assertRaises(KeyboardInterrupt):
                self.app.work.run_step(self.token, request)
        step = self.card()["steps"][0]
        self.assertTrue(step.get("adoption_pending"), step)
        self.assertEqual(step["usage"], {"input_tokens": 13, "output_tokens": 6})
        self.assertEqual(self.card().get("results", []), [])
        self.stop(); self.start()
        self.wire(client)
        prior_queries = len(client.lookups)
        _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertFalse(self.card()["steps"][0]["adoption_pending"])
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(len(client.lookups), prior_queries + 1, "only current original-request authorization is read")

    def test_current_remote_revocation_keeps_saved_completed_usage_without_adopting(self):
        request = self.arrange()
        client = self.wire()
        save = self.app.work.store.save
        def fail_adoption(cx, state, charter, command, *args, **kwargs):
            if command["kind"] == "work_dispatch_adopted": raise KeyboardInterrupt("after observing")
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=fail_adoption):
            with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        self.wire(client)
        client.authorized = False
        _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        step = self.card()["steps"][0]
        self.assertEqual(step["status"], "used")
        self.assertEqual(step.get("model_outcome"), "not_adoptable", step)
        self.assertEqual(step["usage"], {"input_tokens": 13, "output_tokens": 6})
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(len(client.posts), 1)

    def test_closed_host_late_completion_preserves_fact_without_tools_or_adoption(self):
        request = self.arrange()
        message = {"content": None, "tool_calls": [{"id": "read-after-close", "type": "function",
                   "function": {"name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]}
        old_service = self.app.work
        self.app.work.transport = CallbackTransport(lambda package: self.app.close(), message)
        with patch("ai_union.application.work.documents.read_text", return_value=("late", "0" * 64, 4)) as reader:
            receipt = old_service.run_step(self.token, request)
        reader.assert_not_called()
        self.assertEqual(receipt.get("model_outcome"), "unknown", receipt)
        self.assertEqual(self.card().get("tool_calls", []), [])
        self.assertTrue(self.card()["steps"][0].get("adoption_pending"))
        self.assertEqual(self.card()["steps"][0]["usage"], {"input_tokens": 11, "output_tokens": 4})

    def test_current_host_new_recovery_cannot_increment_owner_epoch(self):
        self.arrange()
        self.stop(); self.start()
        _, first, _ = self.recover()
        self.assertEqual(first["receipt"]["status"], "succeeded", first)
        owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        _, second, _ = self.recover()
        self.assertEqual(second["receipt"]["status"], "rejected", second)
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], owner)

    def test_read_projection_reports_actual_recovery_without_claiming_or_private_body(self):
        request = self.arrange()
        self.app.work.transport = CallbackTransport()
        self.app.work.run_step(self.token, request)
        self.assertFalse(self.works()["works"][0]["attempts"][0].get("recovery", {}).get("eligible", True))
        self.stop(); self.start()
        before = self.dump()
        attempt = self.works()["works"][0]["attempts"][0]
        self.assertTrue(attempt.get("recovery", {}).get("eligible"), attempt)
        self.assertEqual(self.dump(), before)
        serialized = json.dumps(self.works())
        self.assertNotIn("wire_body", serialized)
        self.assertNotIn("messages", serialized)

    def test_two_recoverers_and_superseded_replay_leave_one_current_epoch(self):
        import threading
        self.arrange()
        self.stop(); self.start()
        data = {"work_id": "work-overview", "attempt_id": self.attempt_id, "reason": "competing recovery"}
        version = self.state()["version"]
        outcomes = []
        def claim():
            outcomes.append(self.work_command(self.au_id, "recover_work", data, version=version))
        threads = [threading.Thread(target=claim) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        winners = [item for item in outcomes if item[1]["receipt"]["status"] == "succeeded"]
        self.assertEqual(len(winners), 1, outcomes)
        first_request = winners[0][2]
        self.assertEqual(self.card()["attempts"][0]["execution_owner"]["epoch"], 1)
        self.stop(); self.start()
        _, second, _ = self.recover()
        self.assertEqual(second["receipt"]["status"], "succeeded", second)
        current = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        self.assertEqual(current["epoch"], 2)
        self.assertEqual(self.request("/api/v1/work/commands", first_request)[1]["receipt"], winners[0][1]["receipt"])
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], current)

    def test_close_before_dispatch_commit_preserves_prepared_for_next_host(self):
        request = self.arrange()
        client = self.wire()
        from ai_union.application import work_recovery
        original = work_recovery.send_prepared
        def close_first(*args):
            self.app.close()
            return original(*args)
        with patch.object(work_recovery, "send_prepared", side_effect=close_first):
            receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(client.posts, [])
        step = self.card()["steps"][0]
        self.assertEqual((step["status"], step["dispatch_phase"]), ("reserved", "prepared"), receipt)

    def test_old_epoch_worker_cannot_settle_new_owner_observation(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        old_service = self.app.work
        from ai_union.domain.work_recovery import owner
        old_owner = copy.deepcopy(owner(self.card()["attempts"][0]))
        self.stop(); self.start()
        self.wire(client)
        _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        before = self.dump()
        from ai_union.application.work_recovery import adopt_observed
        adopt_observed(old_service, self.token, self.directory, self.intent, request, self.principal, old_owner)
        self.assertEqual(self.dump(), before)

    def test_unknown_original_get_404_keeps_same_reservation_and_never_posts(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        self.wire(client)
        with patch.object(client, "request", side_effect=ServiceError("missing", 404)):
            _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.card()["steps"][0]["status"], "reserved")
        self.assertEqual(len(client.posts), 1)

    def test_original_loop_resumes_tool_progress_with_same_attempt_and_original_commands(self):
        request = self.arrange() | {"kind": "run_loop"}
        message = {"content": None, "tool_calls": [{"id": "read-loop", "type": "function",
                   "function": {"name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]}
        self.app.work.transport = CallbackTransport(message=message)
        run_step = self.app.work.run_step
        def interrupt_next(token, command):
            if command["id"].endswith("-t2"): raise KeyboardInterrupt("after first committed tool turn")
            return run_step(token, command)
        with patch.object(self.app.work, "run_step", side_effect=interrupt_next):
            with self.assertRaises(KeyboardInterrupt): self.app.work.run_loop(self.token, request)
        first_step = copy.deepcopy(self.card()["steps"][0])
        document = self.root / "authorized-docs" / "nested" / "a.md"
        old_text = document.read_text(encoding="utf-8")
        document.write_text("changed after committed tool", encoding="utf-8")
        self.stop(); self.start()
        seen = []
        class Continue(CallbackTransport):
            def chat(inner, package, messages, tools):
                seen.extend(copy.deepcopy(messages))
                return super().chat(package, messages, tools)
        self.app.work.transport = channel = Continue()
        _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(len(channel.calls), 1)
        self.assertEqual(len(self.card()["attempts"]), 1)
        self.assertEqual([s["command_id"] for s in self.card()["steps"]], [request["id"] + "-t1", request["id"] + "-t2"])
        self.assertEqual(self.card()["steps"][0], first_step)
        self.assertEqual(json.loads(next(m for m in seen if m["role"] == "tool")["content"])["content"], old_text)

    def test_tampered_private_snapshot_is_refused_before_recovery_owner_changes(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        before_owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        with self.app.work.store.transaction(self.directory) as cx:
            cx.execute("UPDATE work_execution_requests SET payload='{}'")
        self.wire(client)
        status, value, _ = self.recover()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], before_owner)
        self.assertEqual(len(client.posts), 1)

    def test_revoked_material_binding_refuses_original_context_recovery(self):
        request = self.arrange()
        self.app.work.transport = CallbackTransport(message={"content": None, "tool_calls": [
            {"id": "read-permission", "type": "function", "function": {
                "name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]})
        self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        (self.root / "document-roots.json").unlink()
        before_owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], before_owner)

    def test_close_after_dispatch_marker_before_post_keeps_original_uncertainty(self):
        request = self.arrange()
        client = self.wire()
        channel = self.app.work.transport
        chat = channel.chat_body
        def close_now(body, **kwargs):
            self.app.close()
            return chat(body, **kwargs)
        with patch.object(channel, "chat_body", side_effect=close_now):
            receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(client.posts, [])
        step = self.card()["steps"][0]
        self.assertEqual((step["status"], step["dispatch_phase"]), ("reserved", "dispatching"), receipt)

    def test_original_digest_mismatch_lookup_cannot_adopt_or_replay(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        self.wire(client)
        query = client.request
        def mismatch(*args):
            return query(*args) | {"request_digest": "0" * 64}
        with patch.object(client, "request", side_effect=mismatch): _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.card()["steps"][0]["status"], "reserved")
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(len(client.posts), 1)

    def test_restart_reclaims_original_attempt_and_reuses_committed_tool_context(self):
        request = self.arrange()
        message = {"content": None, "tool_calls": [{"id": "read-original", "type": "function",
                   "function": {"name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]}
        self.app.work.transport = CallbackTransport(message=message)
        self.assertEqual(self.app.work.run_step(self.token, request)["status"], "succeeded")
        original = copy.deepcopy(self.card())
        old_instance = self.app.instance
        self.stop(); self.start()
        status, value, recovery_request = self.recover()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        recovered = self.card()
        self.assertEqual([a["id"] for a in recovered["attempts"]], [self.attempt_id])
        self.assertEqual(recovered["attempts"][0]["host_instance"], old_instance)
        self.assertEqual(recovered["attempts"][0]["execution_owner"]["instance"], self.app.instance)
        self.assertEqual(recovered["steps"], original["steps"])
        seen = []
        class Next(CallbackTransport):
            def chat(inner, package, messages, tools):
                seen.extend(copy.deepcopy(messages))
                return super().chat(package, messages, tools)
        self.app.work.transport = Next()
        receipt = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertEqual(len(self.card()["attempts"]), 1)
        tools = [m for m in seen if m["role"] == "tool"]
        self.assertEqual(tools[0]["tool_call_id"], "read-original")
        self.assertEqual(json.loads(tools[0]["content"])["step_ref"], original["tool_calls"][0]["step_ref"])
        self.assertEqual(self.request("/api/v1/work/commands", recovery_request)[1]["receipt"], value["receipt"])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkRecoveryTests(name) for name in WorkRecoveryTests.__dict__
                             if name.startswith("test_"))
