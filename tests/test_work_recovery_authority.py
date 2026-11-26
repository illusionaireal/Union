"""Current identity, sealed wire input and current authorization recovery boundaries."""
import copy
import json
import unittest
from unittest.mock import patch

from ai_union.errors import Rejected
from ai_union.model_service import ServiceError
from ai_union.work_transport import ModeldWorkTransport
from tests.test_work_recovery import WorkRecoveryTests, RecoveryClient


class WorkRecoveryAuthorityTests(WorkRecoveryTests):
    def test_wrong_wire_connection_revision_cannot_reserve_or_post(self):
        request = self.arrange()
        connection = copy.deepcopy(self.state()["model_access"]["connections"]["connection-a"])
        connection["revision"] += 1
        client = RecoveryClient()
        self.app.work.transport = ModeldWorkTransport(client, self.au_id, connection)
        before = self.dump()
        with self.assertRaises(Rejected): self.app.work.run_step(self.token, request)
        self.assertEqual(client.posts, [])
        self.assertEqual(self.dump(), before)

    def test_wrong_wire_au_cannot_leave_a_bad_reservation(self):
        request = self.arrange()
        client = self.wire()
        self.app.work.transport.au_id = "other-au"
        before = self.dump()
        with self.assertRaises(Rejected): self.app.work.run_step(self.token, request)
        self.assertEqual(client.posts, [])
        self.assertEqual(self.dump(), before)

    def test_recovery_denies_client_owner_epoch_and_wrong_attempt(self):
        self.arrange()
        self.stop(); self.start()
        before = self.card()["attempts"]
        for extra in ({"epoch": 99}, {"host_instance": "client-owner"}, {"actor_principal_id": self.principal}):
            status, value, _ = self.recover(**extra)
            self.assertEqual(status, 400, value)
        _, value, _ = self.recover(attempt_id="work-overview#a9")
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(self.card()["attempts"], before)

    def test_recovery_issuer_replays_only_exact_original_receipt(self):
        self.arrange()
        self.stop(); self.start()
        _, original, request = self.recover()
        owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        changed = copy.deepcopy(request)
        changed["data"]["reason"] = "changed original payload"
        status, value, _ = self.request("/api/v1/work/commands", changed)
        self.assertEqual(status, 409, value)
        outsider, _ = self.participant("recovery-outsider")
        status, value, _ = self.request("/api/v1/work/commands", request, token=outsider)
        self.assertEqual(status, 403, value)
        self.assertEqual(self.request("/api/v1/work/commands", request)[1]["receipt"], original["receipt"])
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], owner)

    def test_current_authorization_get_failure_keeps_original_observed_fact_pending(self):
        request = self.arrange()
        client = self.wire()
        save = self.app.work.store.save
        def crash(cx, state, charter, command, *args, **kwargs):
            if command["kind"] == "work_dispatch_adopted": raise KeyboardInterrupt("before adoption")
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        self.wire(client)
        with patch.object(client, "request", side_effect=ServiceError("unavailable", 503)):
            _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        step = self.card()["steps"][0]
        self.assertEqual(step["status"], "reserved")
        self.assertTrue(step["adoption_pending"])
        self.assertEqual(step["usage"], {"input_tokens": 13, "output_tokens": 6})
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(len(client.posts), 1)

    def test_wrong_digest_reply_cannot_be_attached_as_an_original_completed_fact(self):
        request = self.arrange()
        client = self.wire()
        original = client.request
        client.request = lambda *args: original(*args) | {"request_digest": "0" * 64}
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt.get("model_outcome"), "unknown", receipt)
        step = self.card()["steps"][0]
        self.assertIsNone(step.get("observed_sha256"), "wrong digest result is not the original completed fact")
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(len(client.posts), 1)

    def test_host_closing_inside_context_save_cannot_commit_result_adoption(self):
        request = self.arrange()
        self.wire()
        from ai_union.adapters.work_context_store import WorkContextStore
        save = WorkContextStore.save
        def close_at_save(*args, **kwargs):
            save(*args, **kwargs)
            self.app.close()
        with patch.object(WorkContextStore, "save", side_effect=close_at_save):
            receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt.get("model_outcome"), "unknown", receipt)
        self.assertEqual(self.card().get("results", []), [])
        self.assertEqual(self.card()["steps"][0]["status"], "reserved")
        self.assertTrue(self.card()["steps"][0]["adoption_pending"])

    def test_current_owner_can_retry_missing_original_get_without_new_epoch_or_post(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        self.wire(client)
        with patch.object(client, "request", side_effect=ServiceError("missing", 404)):
            _, first, first_request = self.recover()
        self.assertEqual(first["receipt"]["status"], "succeeded", first)
        owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        self.assertTrue(self.works()["works"][0]["attempts"][0]["recovery"]["eligible"])
        _, second, _ = self.recover()
        self.assertEqual(second["receipt"]["status"], "succeeded", second)
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], owner)
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(self.request("/api/v1/work/commands", first_request)[1]["receipt"], first["receipt"])

    def test_same_host_pending_request_can_continue_without_reclaiming_owner(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        _, result, _ = self.recover()
        self.assertEqual(result["receipt"]["status"], "succeeded", result)
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], owner)
        self.assertEqual(len(client.posts), 1)

    def test_current_owner_recovery_busy_and_replay_cannot_start_parallel_lookup(self):
        import threading
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        owner = copy.deepcopy(self.card()["attempts"][0]["execution_owner"])
        original = client.request
        entered, release = threading.Event(), threading.Event()
        def lookup(*args):
            if not entered.is_set():
                entered.set()
                release.wait(5)
            return original(*args)
        client.request = lookup
        version = self.state()["version"]
        outcomes = []
        def first():
            outcomes.append(self.work_command(self.au_id, "recover_work", {
                "work_id": "work-overview", "attempt_id": self.attempt_id, "reason": "first original lookup"},
                request_id="recovery-busy-original", version=version))
        thread = threading.Thread(target=first)
        thread.start()
        try:
            self.assertTrue(entered.wait(3), "first recovery must enter original GET")
            replay_request = {"id": "recovery-busy-original", "organization_id": self.au_id,
                "base_version": version, "kind": "recover_work", "data": {
                    "work_id": "work-overview", "attempt_id": self.attempt_id, "reason": "first original lookup"}}
            status, replay, _ = self.request("/api/v1/work/commands", replay_request)
            self.assertEqual(status, 200, replay)
            _, second, _ = self.recover()
            self.assertEqual(second["receipt"]["status"], "rejected", second)
            self.assertEqual(client.lookups, [])
        finally:
            release.set()
            thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes[0][1]["receipt"]["status"], "succeeded", outcomes)
        self.assertEqual(self.card()["attempts"][0]["execution_owner"], owner)
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(len(client.posts), 1)
        self.assertEqual(len(client.lookups), 2)

    def test_blocked_post_does_not_hold_global_mutex_or_block_unrelated_read(self):
        import threading
        request = self.arrange()
        client = self.wire()
        entered, release, read_finished = threading.Event(), threading.Event(), threading.Event()
        call = client.call
        def blocked(*args, **kwargs):
            entered.set()
            release.wait(5)
            return call(*args, **kwargs)
        client.call = blocked
        outcomes = []
        worker = threading.Thread(target=lambda: outcomes.append(self.app.work.run_step(self.token, request)))
        reader = threading.Thread(target=lambda: (self.app.work.read(self.token, self.au_id), read_finished.set()))
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            reader.start()
            self.assertTrue(read_finished.wait(.4), "a waiting POST must not own the global mutex/catalog")
        finally:
            release.set()
            worker.join(10)
            if reader.ident: reader.join(10)
        self.assertFalse(worker.is_alive())
        self.assertFalse(reader.is_alive())
        self.assertEqual(outcomes[0]["status"], "succeeded", outcomes)

    def test_old_worker_refusal_cannot_release_a_new_owner_reservation(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        old = self.app.work
        self.stop(); self.start()
        self.wire(client)
        with patch.object(client, "request", side_effect=ServiceError("unavailable", 503)):
            _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        before = self.dump()
        result = old.record_channel_outcome(self.directory, self.intent, request, self.principal,
                                            "late old-worker refusal", refused=True)
        self.assertEqual(result.get("model_outcome"), "unknown", result)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.card()["steps"][0]["status"], "reserved")

    def test_old_worker_known_usage_survives_without_settling_new_owner_reservation(self):
        request = self.arrange()
        client = self.wire()
        client.crash_post = True
        with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        old = self.app.work
        self.stop(); self.start()
        self.wire(client)
        with patch.object(client, "request", side_effect=ServiceError("unavailable", 503)): self.recover()
        from ai_union.work_transport import UnadoptableWorkResult
        step = self.card()["steps"][0]
        old.record_channel_outcome(self.directory, self.intent, request, self.principal, "late completed usage",
            completed=UnadoptableWorkResult(step["model_request_id"], {"input_tokens": 13, "output_tokens": 6}))
        current = self.card()["steps"][0]
        self.assertEqual(current["status"], "reserved")
        self.assertEqual(current["usage"], {"input_tokens": 13, "output_tokens": 6})
        self.assertEqual(self.card().get("results", []), [])

    def test_revoked_completion_keeps_full_usage_privately_with_only_counts_in_public_state(self):
        request = self.arrange()
        client = self.wire()
        client.authorized = False
        original = client.request
        def complete(*args):
            result = original(*args)
            result["result"]["usage"]["provider_observation"] = {"reference": "private-usage-canary"}
            return result
        client.request = complete
        result = self.app.work.run_step(self.token, request)
        self.assertEqual(result["model_outcome"], "not_adoptable", result)
        step = self.card()["steps"][0]
        from ai_union.adapters.work_execution_store import WorkExecutionStore
        with self.app.work.store.transaction(self.directory) as cx:
            observed = WorkExecutionStore.load_observed(cx, step)
        self.assertEqual(observed["usage"].get("provider_observation"), {"reference": "private-usage-canary"})
        self.assertNotIn("private-usage-canary", json.dumps(self.works()))


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkRecoveryAuthorityTests(name) for name in WorkRecoveryAuthorityTests.__dict__
                             if name.startswith("test_"))
