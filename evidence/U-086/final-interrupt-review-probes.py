"""Offline review of saved evidence and exact driver assertions; no model calls.

Run with the pinned Node on PATH:
  python evidence/U-086/final-interrupt-review-probes.py [git-commit] [report.json]

Exit 1 means the reviewed driver accepted a counterexample. Source/import errors
are reported separately. This is a review probe, not a real acceptance driver.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "1e490d074d0b4e91291860d742244af55ed81d88"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else None
FOLDER = "evidence/127-u086-real-interrupt-exit/"
SOURCES = {}
RESULTS = {}


def source(name):
    raw = subprocess.check_output(["git", "show", f"{CANDIDATE}:{name}"], cwd=ROOT)
    SOURCES[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return raw.decode("utf-8")


def between(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


JS = source("scripts/exit22b_page.cjs")
TRIGGER = between(JS, "  let inflight = null;\n  await waitFor(async () => {",
                  "  }, 'in-flight automatic reservation visible'")
CANCEL = "  check('cancel accepted by the product: " + between(
    JS, "  check('cancel accepted by the product: ",
    "  // The settlement may be interrupted")
REOPEN = "  check('the settled step survives" + between(
    JS, "  check('the settled step survives",
    "  fs.writeFileSync(path.join(output, 'snapshot-after-restart.json')")

# The sandbox has only synthetic inputs, check() and a synthetic Core read.
# No driver import, require, process, host, browser, real transport or credentials.
VM = r"""
const vm = require('node:vm');
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const names = [];
const context = {
  inflight: null,
  ...input.variables,
  coreWork: async () => input.read,
  check: (name, value = true) => {
    if (!value) throw new Error('assertion rejected');
    names.push(name);
  },
};
(async () => {
  try {
    const value = await vm.runInNewContext(
      '(async () => {' + input.block + '\n})()', context, { timeout: 1000 });
    process.stdout.write(JSON.stringify({ accepted: input.predicate ? value === true : true,
                                        checks: names.length }));
  } catch (error) {
    if (error.message !== 'assertion rejected') throw error;
    process.stdout.write(JSON.stringify({ accepted: false, checks: names.length }));
  }
})().catch(error => { process.stderr.write(error.name); process.exitCode = 2; });
"""


def probe(name, block, variables, *, read=None, predicate=False):
    response = subprocess.run(
        ["node", "-e", VM], cwd=ROOT, capture_output=True, text=True,
        input=json.dumps({"block": block, "variables": variables,
                          "read": read, "predicate": predicate}),
        check=True, timeout=5,
    )
    RESULTS[name] = json.loads(response.stdout)
    return RESULTS[name]["accepted"]


def original_step():
    return {"step_ref": "work-exit#s2", "attempt_id": "work-exit#a1",
            "command_id": "original-loop-t2", "model_request_id": "original-request-2",
            "status": "unknown", "reason": "original unresolved result"}


class FinalInterruptReview(unittest.TestCase):
    def test_control_no_reservation_does_not_trigger_cancel(self):
        read = {"works": [{"id": "work-exit", "steps": []}]}
        self.assertFalse(probe("control_no_reservation", TRIGGER,
                               {"workId": "work-exit"}, read=read, predicate=True))

    def test_prior_step_output_cannot_replace_cancelled_request_output(self):
        read = {"works": [{"id": "work-exit", "steps": [
            {"step_ref": "work-exit#s1", "command_id": "original-loop-t1",
             "model_request_id": "original-request-1", "status": "used",
             "usage": {"input_tokens": 438, "output_tokens": 43}},
            {**original_step(), "status": "reserved"},
        ]}]}
        self.assertFalse(probe("cancel_without_original_output", TRIGGER,
                               {"workId": "work-exit"}, read=read, predicate=True))

    def test_control_valid_cancel_receipt_is_accepted(self):
        receipt = {**original_step(), "id": "cancel-original", "status": "succeeded",
                   "organization_id": "original-au", "cancel_accepted": True}
        self.assertTrue(probe("control_cancel_receipt", CANCEL,
                              {"cancelOutcome": {"status": 200, "receipt": receipt}}))

    def test_cancel_receipt_must_match_the_original_request(self):
        receipt = {"id": "other-cancel", "status": "succeeded", "cancel_accepted": True,
                   "organization_id": "other-au", "step_ref": "other-work#s9",
                   "attempt_id": "other-attempt", "model_request_id": "other-request"}
        self.assertFalse(probe("cancel_receipt_wrong_identity", CANCEL,
                               {"cancelOutcome": {"status": 200, "receipt": receipt},
                                "inflight": original_step(),
                                "createdReceipt": {"organization_id": "original-au"}}))

    def test_control_reopened_unknown_with_reservation_is_accepted(self):
        self.assertTrue(probe("control_reopen", REOPEN,
                              {"settledStep": original_step(),
                               "entry": {"budget": {"reserved": 1, "used": 1}}}))

    def test_reopened_unknown_must_keep_its_reservation(self):
        self.assertFalse(probe("reopen_lost_reservation", REOPEN,
                               {"settledStep": original_step(),
                                "entry": {"budget": {"reserved": 0, "used": 1}}}))


def saved_evidence():
    old = json.loads(source(FOLDER + "snapshot-after-restart.json"))
    new = json.loads(source(FOLDER + "snapshot-after-restart-final-head.json"))
    before = json.loads(source(FOLDER + "snapshot-before-restart.json"))
    checks = json.loads(source(FOLDER + "checks-final-head.json"))
    work = next(w for w in new["works"] if w["id"] == "work-exit")
    old_work = next(w for w in old["works"] if w["id"] == "work-exit")
    steps = work["steps"]
    cancelled = next(s for s in steps if s.get("cancel_requested_at"))
    # These assertions verify our extraction against the immutable input, not the
    # author's missing acceptance conditions or the actual external execution.
    assert new["protocol"] == old["protocol"] == "core.work.v1"
    assert len({s["model_request_id"] for s in steps}) == len(steps)
    assert any(cancelled["model_request_id"] in c for c in checks["checks"])
    return {
        "early_run_recorded_requests": len(old_work["steps"]),
        "final_run_recorded_requests": len(steps),
        "different_au_between_runs": old["organization_id"] != new["organization_id"],
        "before_read_protocol": before.get("protocol"),
        "before_read_error_code": before.get("code"),
        "final_before_snapshot_present": bool(subprocess.check_output(
            ["git", "ls-tree", "--name-only", CANDIDATE, "--",
             FOLDER + "snapshot-before-restart-final-head.json"], cwd=ROOT).strip()),
        "final_steps": [{"seq": s["seq"], "status": s["status"],
                         "model_request_id": s["model_request_id"],
                         "usage": s.get("usage"),
                         "model_outcome": s.get("model_outcome")} for s in steps],
        "cancelled_request_matches_check": True,
        "final_budget": work["budget"],
        "final_known_usage": work["usage"],
        "complete_usage_known": all("usage" in s for s in steps),
        "claim_passed_checks": checks["passed"],
        "scope": "saved records only; no external verification or request replay",
    }


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(FinalInterruptReview))
    report = {
        "candidate": CANDIDATE,
        "reviewed_driver": "scripts/exit22b_page.cjs",
        "tests": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "probes": RESULTS,
        "saved_evidence": saved_evidence(), "sources": SOURCES,
        "real_model_calls_added": 0,
    }
    if REPORT:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
