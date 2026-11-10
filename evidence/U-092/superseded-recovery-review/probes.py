"""Run against an isolated U092 candidate, using only temporary synthetic data.

Usage: python -B probes.py <candidate-source-directory> <private-result.json>
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_inputs import prepare_candidate  # noqa: E402

candidate, report, source_binding = prepare_candidate()
sys.path.insert(0, str(candidate))

from ai_union.errors import Rejected  # noqa: E402
from tests.test_work_recovery import WorkRecoveryTests  # noqa: E402


class SupersededRecoveryReview(WorkRecoveryTests):
    observations = []

    def envelope(self):
        return self.request_value() | {"kind": "recover_work", "data": {
            "work_id": "work-overview", "attempt_id": self.attempt_id,
            "reason": "Recover the original request after temporary service restart"}}

    def interrupt_recovery(self, client, command):
        def crash():
            raise KeyboardInterrupt("controlled loss during original recovery GET")
        client.on_lookup = crash
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.command(self.token, command)
        client.on_lookup = None

    def observe_replay(self, client, command):
        before_dump = self.dump()
        before = copy.deepcopy(self.card())
        body_count = len(client.bodies)
        # Submit the actual original envelope through the HTTP API.
        http, body, _ = self.request("/api/v1/work/commands", command)
        after = self.card()
        facts = {
            "test": self._testMethodName,
            "http": http,
            "response_status": body.get("receipt", {}).get("status"),
            "response_code": body.get("code"),
            "state_unchanged": self.dump() == before_dump,
            "epoch_before": before["attempts"][0].get("execution_epoch", 0),
            "epoch_after": after["attempts"][0].get("execution_epoch", 0),
            "recovery_phases_before": [r["phase"] for r in before["recoveries"]],
            "recovery_phases_after": [r["phase"] for r in after["recoveries"]],
            "original_attempt_preserved": before["attempts"][0]["id"] == after["attempts"][0]["id"],
            "original_model_request_preserved": before["steps"][0]["model_request_id"] == after["steps"][0]["model_request_id"],
            "fake_dispatches": len(client.bodies),
            "new_fake_dispatches_during_replay": len(client.bodies) - body_count,
            "real_model_calls": 0,
        }
        self.observations.append(facts)
        self.assertEqual(len(client.bodies), body_count, "recovery replay must not dispatch a model")
        self.assertTrue(facts["original_attempt_preserved"])
        self.assertTrue(facts["original_model_request_preserved"])
        return facts

    def test_completed_recovery_replay_control_is_read_only(self):
        _, client, _ = self.interrupted(state="completed")
        command = self.envelope()
        self.assertEqual(self.app.work.command(self.token, command)["status"], "succeeded")
        facts = self.observe_replay(client, command)
        self.assertEqual(facts["response_status"], "succeeded")
        self.assertTrue(facts["state_unchanged"])

    def prepare_replacement(self):
        _, client, _ = self.interrupted(state="completed")
        original = self.envelope()
        self.interrupt_recovery(client, original)
        self.stop()
        self.start()
        self.channel(client)
        return client, original, self.envelope()

    def test_superseded_replay_after_replacement_completion_cannot_mutate_ownership(self):
        client, original, replacement = self.prepare_replacement()
        self.assertEqual(self.app.work.command(self.token, replacement)["status"], "succeeded")
        self.assertEqual([r["phase"] for r in self.card()["recoveries"]], ["superseded", "completed"])
        facts = self.observe_replay(client, original)
        self.assertTrue(facts["state_unchanged"],
                        "superseded original recovery committed another ownership/preparation mutation")
        self.assertEqual(facts["epoch_after"], facts["epoch_before"])

    def test_superseded_replay_while_replacement_prepared_cannot_mutate_ownership(self):
        client, original, replacement = self.prepare_replacement()
        self.interrupt_recovery(client, replacement)
        self.assertEqual([r["phase"] for r in self.card()["recoveries"]], ["superseded", "prepared"])
        facts = self.observe_replay(client, original)
        self.assertTrue(facts["state_unchanged"])
        self.assertEqual(facts["epoch_after"], facts["epoch_before"])


names = [name for name in SupersededRecoveryReview.__dict__ if name.startswith("test_")]
suite = unittest.TestSuite(SupersededRecoveryReview(name) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
output = {
    "source_binding": source_binding,
    "scope": "independent synthetic HTTP/SQLite superseded-recovery review",
    "source_sha256": {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest()
                      for name in ("ai_union/application/work_recovery.py", "tests/test_work_recovery.py")},
    "tests": result.testsRun,
    "failures": [{"test": case.id(), "traceback": trace} for case, trace in result.failures],
    "errors": [{"test": case.id(), "traceback": trace} for case, trace in result.errors],
    "observations": SupersededRecoveryReview.observations,
}
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
raise SystemExit(0 if result.wasSuccessful() else 1)
