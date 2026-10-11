import tempfile
import unittest
from pathlib import Path

from ai_union.engine import Engine, Rejected
from tests.support import CHARTER, decision, init, organization


class Mechanisms(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(Path(self.temp.name))

    def test_bootstrap_is_temporary_and_cannot_spoof_board(self):
        organization(self.e)
        self.assertEqual(len(self.e.state()["members"]), 2)
        with self.assertRaises(Rejected):
            self.e.apply_decision(decision(self.e, []), "bootstrap")
        with self.assertRaises(Rejected):
            self.e.apply_decision(decision(self.e, [], actor_ref="board"), "m2", "a2")

    def test_invalid_batch_rolls_back_and_conflict_is_detected(self):
        organization(self.e)
        before = self.e.state()
        d = decision(self.e, [{"op": "create_member", "id": "m3", "name": "Third"},
                              {"op": "create_work", "id": "invalid", "title": "Invalid", "instruction": "bad",
                               "position_id": "missing", "dependencies": []}])
        with self.assertRaises(Rejected):
            self.e.apply_decision(d, "m1", "a1")
        self.assertEqual(before, self.e.state())
        stale = decision(self.e, [])
        self.e.apply_decision(decision(self.e, [{"op": "set_strategy", "hypothesis": "A test hypothesis"}]), "m1", "a1")
        with self.assertRaises(Rejected):
            self.e.apply_decision(stale, "m1", "a1")

    def test_delivery_has_evidence_and_is_idempotent(self):
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        self.assertEqual(self.e.runs()[0]["package"], package)
        result = {"status": "delivered", "summary": "done", "artifacts": [{"name": "note.md", "content": "First result"}]}
        self.e.finish_work(package["run_id"], result, {"input_tokens": 10, "output_tokens": 20})
        before = self.e.state()
        self.e.finish_work(package["run_id"], result, {"input_tokens": 10, "output_tokens": 20})
        self.assertEqual(before, self.e.state())
        self.assertEqual(len(self.e.usage()), 1)
        package2 = self.e.begin_work("w2", "fixture")
        self.assertIn("First result", str(package2["context"]))
        self.assertIn("w1", str(package2["context_manifest"]))

    def test_no_artifact_cannot_be_delivered(self):
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        with self.assertRaises(Rejected):
            self.e.finish_work(package["run_id"], {"status": "delivered", "artifacts": []}, {})
        self.assertNotEqual(self.e.state()["work"]["w1"]["status"], "delivered")

    def test_board_amendment_revokes_new_action_preserves_history(self):
        organization(self.e)
        old = decision(self.e, [{"op": "create_member", "id": "m3", "name": "Third"}])
        with self.assertRaises(Rejected):
            self.e.amend("wrong", CHARTER, "not trusted")
        new = CHARTER | {"allowed_operations": ["wait"]}
        self.e.amend("test-key", new, "Reduce authority")
        with self.assertRaises(Rejected):
            self.e.apply_decision(old, "m1", "a1")
        with self.assertRaises(Rejected):
            self.e.apply_decision(decision(self.e, old["operations"]), "m1", "a1")
        self.assertEqual(self.e.charter(1)["allowed_operations"], CHARTER["allowed_operations"])
        self.assertEqual(self.e.context("w1")["manifest"]["charter_version"], 2)

    def test_handoff_changes_pending_responsibility_and_context(self):
        organization(self.e)
        self.e.apply_decision(decision(self.e, [{"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a3"}]), "m1", "a1")
        self.assertEqual(self.e.state()["work"]["w1"]["member_id"], "m2")
        with self.assertRaises(Rejected):
            self.e.apply_decision(decision(self.e, []), "m1", "a1")
        package = self.e.begin_work("w1", "fixture")
        self.assertEqual(package["member_id"], "m2")
        self.assertEqual(package["assignment_id"], "a3")

    def test_crash_recovery_does_not_blindly_execute_again(self):
        organization(self.e)
        package = self.e.begin_work("w1", "fixture")
        restarted = Engine(self.temp.name)
        restarted.recover()
        self.assertEqual(restarted.state()["work"]["w1"]["status"], "needs_review")
        with self.assertRaises(Rejected):
            restarted.begin_work("w1", "fixture")
        self.assertEqual(restarted.runs()[0]["id"], package["run_id"])

    def test_wait_wakes_once_after_restart(self):
        organization(self.e)
        self.e.apply_decision(decision(self.e, [{"op": "wait", "until": "2030-01-01T00:00:00+00:00", "reason": "Await evidence"}]), "m1", "a1")
        restart = Engine(self.temp.name)
        self.assertEqual(restart.wake_due("2029-01-01T00:00:00+00:00"), 0)
        self.assertEqual(restart.wake_due("2030-01-01T00:00:00+00:00"), 1)
        self.assertEqual(restart.wake_due("2030-01-01T00:00:00+00:00"), 0)

    def test_call_budget_reservation_survives_restart(self):
        self.e = init(Path(self.temp.name) / "limited", max_calls=1)
        organization(self.e)
        p = self.e.begin_work("w1", "fixture")
        self.e.finish_work(p["run_id"], {"status": "delivered", "summary": "done", "artifacts": [{"name": "a.md", "content": "ok"}]}, {})
        restarted = Engine(self.e.root)
        with self.assertRaises(Rejected):
            restarted.begin_work("w2", "fixture")
        self.assertEqual(restarted.status()["budget"]["calls_reserved"], 1)

    def test_external_events_are_deduplicated(self):
        self.assertTrue(self.e.add_event("receipt-1", "external_feedback", {"source": "test", "simulated": True}))
        self.assertFalse(self.e.add_event("receipt-1", "external_feedback", {"source": "test", "simulated": True}))
        with self.assertRaises(Rejected):
            self.e.add_event("receipt-1", "external_feedback", {"source": "different", "simulated": True})

    def test_revised_artifact_retains_original_version(self):
        organization(self.e)
        p = self.e.begin_work("w1", "fixture")
        self.e.finish_work(p["run_id"], {"status": "delivered", "artifacts": [{"name": "a.md", "content": "version one"}]}, {})
        self.e.apply_decision(decision(self.e, [{"op": "update_work", "work_id": "w1", "title": "Revision", "instruction": "Revise artifact", "dependencies": []}]), "m1", "a1")
        p2 = self.e.begin_work("w1", "fixture")
        self.e.finish_work(p2["run_id"], {"status": "delivered", "artifacts": [{"name": "a.md", "content": "version two"}]}, {})
        artifacts = sorted(self.e.state()["artifacts"].values(), key=lambda a: a["version"])
        self.assertEqual([a["version"] for a in artifacts], [1, 2])
        self.assertEqual(self.e._read_artifact(artifacts[0]), "version one")
        self.assertEqual(self.e._read_artifact(artifacts[1]), "version two")

    def test_malformed_operation_does_not_escape_transaction(self):
        organization(self.e)
        before = self.e.state()
        with self.assertRaises(Rejected):
            self.e.apply_decision(decision(self.e, [{"op": "create_work", "id": "bad", "title": "bad", "instruction": "bad", "position_id": [], "dependencies": []}]), "m1", "a1")
        self.assertEqual(before, self.e.state())

    def test_new_charter_cannot_authorize_its_own_adoption(self):
        locked = CHARTER | {"board_can_amend": False}
        self.e.amend("test-key", locked, "Lock supported amendment route")
        with self.assertRaises(Rejected):
            self.e.amend("test-key", CHARTER, "Self authorize")

    def test_dependency_cycles_are_rejected(self):
        organization(self.e)
        with self.assertRaises(Rejected):
            self.e.apply_decision(decision(self.e, [{"op": "update_work", "work_id": "w1", "title": "bad", "instruction": "bad", "dependencies": ["w2"]}]), "m1", "a1")

    def test_asset_tampering_is_detected(self):
        organization(self.e)
        p = self.e.begin_work("w1", "fixture")
        self.e.finish_work(p["run_id"], {"status": "delivered", "artifacts": [{"name": "a.md", "content": "original"}]}, {})
        artifact = next(iter(self.e.state()["artifacts"].values()))
        (self.e.root / artifact["path"]).write_text("modified")
        with self.assertRaises(Rejected):
            self.e.context("w2")
