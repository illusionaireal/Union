"""Independent lifecycle probes; run against an isolated U092 source snapshot.

Usage: python -B probes.py <candidate-source-directory> <result.json>
Only synthetic models and the existing temporary HTTP/SQLite fixture run.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


candidate = Path(sys.argv[1]).resolve()
report = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(candidate))

from ai_union.errors import Rejected  # noqa: E402
from tests.test_work_dispatch import CallbackTransport  # noqa: E402
from tests.test_work_recovery import WorkRecoveryTests  # noqa: E402


class LifecycleReview(WorkRecoveryTests):
    observations = []

    def record(self, channel, before):
        card = self.card()
        facts = {
            "test": self._testMethodName,
            "service_closed": self.app.closed,
            "fake_dispatches": len(channel.calls),
            "state_unchanged": self.dump() == before,
            "steps": [{k: step.get(k) for k in
                       ("step_ref", "command_id", "model_request_id", "status")}
                      for step in card.get("steps", [])],
            "real_model_calls": 0,
        }
        self.observations.append(facts)
        return facts

    def test_live_service_control_dispatches_once(self):
        request = self.arrange()
        before = self.dump()
        channel = CallbackTransport()
        self.app.work.transport_factory = lambda *_: channel
        value = self.app.work.run_step(self.token, request)
        facts = self.record(channel, before)
        self.assertEqual(value["status"], "succeeded", value)
        self.assertEqual(facts["fake_dispatches"], 1)
        self.assertEqual(facts["steps"][0]["status"], "used")

    def test_close_during_channel_construction_cannot_commit_or_dispatch(self):
        request = self.arrange()
        before = self.dump()
        channel = CallbackTransport()

        def build(*_):
            self.app.close()
            return channel

        self.app.work.transport_factory = build
        try:
            self.app.work.run_step(self.token, request)
        except Rejected:
            pass
        facts = self.record(channel, before)
        self.assertEqual(facts["fake_dispatches"], 0,
                         "closed service started a model call after channel construction")
        self.assertTrue(facts["state_unchanged"],
                        "closed service persisted a new dispatch reservation")

    def test_close_after_reservation_keeps_original_intent_without_dispatch(self):
        request = self.arrange()
        before = self.dump()
        channel = CallbackTransport()
        self.app.work.transport = channel
        original_check = self.app.work.verify_material_binding
        checks = []

        def close_at_final_check(plan):
            original_check(plan)
            checks.append(len(checks) + 1)
            if len(checks) == 2:
                self.assertEqual(self.card()["steps"][0]["command_id"], request["id"])
                self.app.close()

        with patch.object(self.app.work, "verify_material_binding", side_effect=close_at_final_check):
            try:
                self.app.work.run_step(self.token, request)
            except Rejected:
                pass
        facts = self.record(channel, before)
        self.assertEqual(checks, [1, 2])
        self.assertEqual(len(facts["steps"]), 1)
        self.assertEqual(facts["steps"][0]["command_id"], request["id"])
        self.assertEqual(facts["steps"][0]["status"], "reserved")
        self.assertEqual(facts["fake_dispatches"], 0,
                         "closed service dispatched its already committed reservation")


names = [name for name in LifecycleReview.__dict__ if name.startswith("test_")]
suite = unittest.TestSuite(LifecycleReview(name) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
manifest = candidate / "review-source-manifest.json"
output = {
    "scope": "independent synthetic HTTP/SQLite lifecycle review; no author source mutation",
    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None,
    "source_sha256": {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest()
                      for name in ("ai_union/application/work.py", "ai_union/application/work_recovery.py",
                                   "ai_union/console.py", "tests/test_work_recovery.py")},
    "tests": result.testsRun,
    "failures": [{"test": case.id(), "traceback": trace} for case, trace in result.failures],
    "errors": [{"test": case.id(), "traceback": trace} for case, trace in result.errors],
    "observations": LifecycleReview.observations,
}
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
raise SystemExit(0 if result.wasSuccessful() else 1)
