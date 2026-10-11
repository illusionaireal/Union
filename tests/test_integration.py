import json
import os
import threading
import time
import tempfile
import unittest
from pathlib import Path

from ai_union.engine import Engine, Rejected
from ai_union.evaluation import evaluate
from ai_union.executor import CodexExecutor, ExecutionFailure, FixtureExecutor
from ai_union.runner import exclusive, run, watch
from tests.support import CHARTER, decision, init, organization

REPO = Path(__file__).resolve().parents[1]


class Integration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(self.temp.name)

    def test_whole_fixture_loop_and_restart_are_explicitly_simulated(self):
        fixture = json.loads((REPO / "examples/fixture.json").read_text())
        actions = run(self.e, FixtureExecutor(fixture), 8)
        self.assertEqual(actions[-1]["action"], "wait")
        restarted = Engine(self.e.root)
        report = evaluate(restarted)
        self.assertTrue(report["mechanism_scenario_passed"])
        self.assertEqual(report["status"], "simulated")
        self.assertFalse(report["real_agent_verified"])
        self.assertEqual(len(restarted.usage()), 6)
        self.assertEqual(run(restarted, FixtureExecutor([]), 1)[0]["action"], "wait")

    def test_cannot_run_two_dispatchers(self):
        with exclusive(self.e):
            with self.assertRaises(Rejected):
                with exclusive(self.e):
                    pass

    def test_rejected_agent_output_is_recorded_and_does_not_change_organization(self):
        fixture = [{"issue": "bad", "rationale": "bad", "expected_effect": "bad", "evidence_refs": [],
                    "operations": [{"op": "amend_charter"}]}]
        actions = run(self.e, FixtureExecutor(fixture), 1)
        self.assertEqual(actions[0]["action"], "blocked")
        self.assertEqual(self.e.state()["members"], {})
        self.assertEqual(self.e.runs()[0]["status"], "failed")
        self.assertEqual(self.e.decisions()[0]["status"], "rejected")

    def test_tools_revoked_while_running_rejects_delivery(self):
        organization(self.e)
        p = self.e.begin_work("w1", "fixture")
        self.e.amend("test-key", CHARTER | {"allowed_tools": []}, "test revocation")
        with self.assertRaises(Rejected):
            self.e.finish_work(p["run_id"], {"status": "delivered", "artifacts": [{"name": "a.txt", "content": "not allowed"}]}, {})
        self.assertFalse(self.e.state()["artifacts"])

    def test_handoff_rejects_previous_executor_receipt(self):
        organization(self.e)
        p = self.e.begin_work("w1", "fixture")
        self.e.apply_decision(decision(self.e, [{"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a3"}]), "m1", "a1")
        with self.assertRaises(Rejected):
            self.e.finish_work(p["run_id"], {"status": "delivered", "artifacts": [{"name": "a.txt", "content": "stale"}]}, {})

    def test_amount_budget_without_known_reservation_blocks_before_call(self):
        self.e.configure_resources("test-key", {"max_calls": 3, "timeout_seconds": 30, "max_cost": 1}, "test")
        actions = run(self.e, FixtureExecutor([]), 1)
        self.assertEqual(actions[0]["action"], "blocked")
        self.assertFalse(self.e.runs())

    def test_waiting_process_wakes_for_external_event_without_idle_calls(self):
        fixture = json.loads((REPO / "examples/fixture.json").read_text())
        run(self.e, FixtureExecutor(fixture), 8)
        before = len(self.e.runs())
        response = [{"issue": "new evidence", "rationale": "wait for further input", "expected_effect": "wait",
                     "evidence_refs": [], "operations": [{"op": "wait", "until": "2099-01-01T00:00:00+00:00", "reason": "test"}]}]
        def event():
            time.sleep(0.08)
            self.e.add_event("watch-input", "external_feedback", {"source": "test", "simulated": True})
        t = threading.Thread(target=event)
        t.start()
        actions = watch(self.e, FixtureExecutor(response), 1, 2, poll_seconds=0.03)
        t.join()
        self.assertEqual(actions[0]["action"], "decision")
        self.assertEqual(len(self.e.runs()), before + 1)


class CodexContract(unittest.TestCase):
    """Subprocess doubles exercise the adapter; these are not real model evaluations."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fake(self, body):
        cmd = self.root / "fake_codex"
        cmd.write_text("#!/usr/bin/env python3\n" + body)
        cmd.chmod(0o700)
        return str(cmd)

    def package(self):
        return {"run_id": "test-run", "kind": "work", "timeout_seconds": 2,
                "context": {}, "context_manifest": {}}

    def test_submit_status_result_and_usage(self):
        fake = self.fake('''import sys,json
from pathlib import Path
args=sys.argv
assert args[args.index('--sandbox')+1]=='read-only'
assert '--ignore-user-config' in args
assert 'shell_tool' in args and 'multi_agent' in args
sys.stdin.read()
Path(args[args.index('--output-last-message')+1]).write_text(json.dumps({'status':'delivered','summary':'test','artifacts':[{'name':'a.txt','content':'adapter test'}]}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':12,'output_tokens':7}}))
''')
        ex = CodexExecutor(self.root, command=fake)
        result, usage = ex.execute(self.package())
        self.assertEqual(result["artifacts"][0]["content"], "adapter test")
        self.assertEqual(usage["output_tokens"], 7)
        self.assertEqual(CodexExecutor(self.root, command=fake).status("test-run"), "needs_review")

    def test_timeout_is_unknown_and_requires_reconciliation(self):
        fake = self.fake("import time,sys\nsys.stdin.read()\ntime.sleep(10)\n")
        ex = CodexExecutor(self.root, command=fake)
        p = self.package() | {"timeout_seconds": 0.1}
        with self.assertRaises(ExecutionFailure) as caught:
            ex.execute(p)
        self.assertTrue(caught.exception.unknown)

    def test_out_of_scope_tool_receipt_is_not_accepted(self):
        fake = self.fake('''import sys,json
from pathlib import Path
sys.stdin.read()
Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text('{}')
print(json.dumps({'type':'item.completed','item':{'type':'command_execution'}}))
print(json.dumps({'type':'turn.completed','usage':{}}))
''')
        with self.assertRaises(ExecutionFailure) as caught:
            CodexExecutor(self.root, command=fake).execute(self.package())
        self.assertTrue(caught.exception.unknown)
