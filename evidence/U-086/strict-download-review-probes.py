"""Review exact download assertions offline; never run the real driver.

Usage (pinned Node on PATH):
  python evidence/U-086/strict-download-review-probes.py <commit> [report.json]

Exit 1 reports an accepted counterexample; runtime/extraction errors are separate.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "1d9ed8e9ddcaed949d38218186ede28d216dfb8f"
REPORT = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SOURCES = {}
RESULTS = {}


def source(name):
    raw = subprocess.check_output(["git", "show", f"{CANDIDATE}:{name}"], cwd=ROOT)
    SOURCES[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return raw.decode("utf-8")


def between(text, start, end):
    if text.count(start) != 1:
        raise ValueError("ambiguous/missing assertion block")
    rest = text.split(start, 1)[1]
    if end not in rest:
        raise ValueError("missing assertion block end")
    return start + rest.split(end, 1)[0]


JS = source("scripts/exit22c_download.cjs")
DOWNLOAD = between(JS, "  const recordedFull = resultRead.result || resultRead;",
                   "  await page.evaluate(async config => {")
REOPEN = between(JS, "  const entry = (after.works || []).find(w => w.id === workId);",
                 "  // Restart request conservation." if "  // Restart request conservation." in JS
                 else "  fs.writeFileSync(path.join(output, 'snapshot-after-restart.json')")
CONTENT = "Original synthetic result — 合成资料\n"
DIGEST = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()
ORIGINAL = {
    "protocol": "core.work.v1", "organization_id": "original-au",
    "work_id": "original-work", "content": CONTENT,
    "result": {"id": "original-result", "title": "Original title",
               "sha256": DIGEST, "status": "candidate"},
}

# Only the inspected assertions receive crypto/Buffer, synthetic page selectors
# and synthetic fetch. No browser, sockets, credentials, driver main or host.
VM = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const names = [];
let fetches = 0;
const context = {
  ...input.variables,
  crypto: require('node:crypto'), Buffer,
  card: () => ({getByRole: () => ({getAttribute: async () =>
    '/api/v1/work/results?organization_id=original-au&work_id=original-work&id=original-result'})}),
  page: {evaluate: async (fn, arg) => fn(arg)},
  fetch: async () => {
    fetches++;
    return {ok: input.status === 200, status: input.status, json: async () => input.body};
  },
  check: (name, value = true) => {
    if (!value) throw new Error('review assertion rejected');
    names.push(name);
  },
};
(async () => {
  try {
    await vm.runInNewContext('(async () => {' + input.block + '\n})()', context,
                            {timeout: 1000});
    process.stdout.write(JSON.stringify({accepted: true, checks: names.length, fetches}));
  } catch (error) {
    if (error.message !== 'review assertion rejected') throw error;
    process.stdout.write(JSON.stringify({accepted: false, checks: names.length, fetches}));
  }
})().catch(error => {process.stderr.write(error.name); process.exitCode = 2;});
"""


def probe(name, block, variables, body=None, status=200):
    result = subprocess.run(
        ["node", "-e", VM], cwd=ROOT, capture_output=True, text=True, timeout=5,
        input=json.dumps({"block": block, "variables": variables,
                          "body": body, "status": status}), check=True,
    )
    RESULTS[name] = json.loads(result.stdout)
    return RESULTS[name]["accepted"]


def download(name, body, status=200):
    return probe(name, DOWNLOAD,
                 {"resultRead": ORIGINAL, "digest": DIGEST,
                  "workId": "original-work",
                  "createdReceipt": {"organization_id": "original-au"}}, body, status)


def reopened(name, result_id):
    return probe(name, REOPEN, {
        "workId": "original-work", "resultId": "original-result",
        "recorded": DIGEST,
        "createdReceipt": {"organization_id": "original-au"},
        "after": {"protocol": "core.work.v1", "organization_id": "original-au",
                  "works": [{"id": "original-work", "status": "delivered",
                             "delivered_result_id": "original-result",
                             "results": [{"id": result_id, "status": "adopted",
                                          "sha256": DIGEST}]}]},
    })


class StrictDownloadReview(unittest.TestCase):
    def test_control_original_result_is_accepted(self):
        self.assertTrue(download("control_original", copy.deepcopy(ORIGINAL)))
        self.assertEqual(RESULTS["control_original"]["fetches"], 1)
        self.assertEqual(RESULTS["control_original"]["checks"], 4)

    def test_fixed_error_body_is_rejected(self):
        self.assertFalse(download("fixed_error_body", {"error": "result unavailable"}))

    def test_fixed_null_result_is_rejected(self):
        self.assertFalse(download("fixed_null_result", {"result": None}))

    def test_fixed_other_result_is_rejected(self):
        body = copy.deepcopy(ORIGINAL)
        body["result"]["id"] = "other-result"
        self.assertFalse(download("fixed_other_result", body))

    def test_changed_content_is_rejected(self):
        body = copy.deepcopy(ORIGINAL)
        body["content"] += "different bytes"
        self.assertFalse(download("changed_content", body))

    def test_changed_title_is_rejected(self):
        body = copy.deepcopy(ORIGINAL)
        body["result"]["title"] = "Another title"
        self.assertFalse(download("changed_title", body))

    def test_download_must_match_original_au(self):
        body = copy.deepcopy(ORIGINAL)
        body["organization_id"] = "other-au"
        self.assertFalse(download("wrong_au", body))

    def test_download_must_match_original_work(self):
        body = copy.deepcopy(ORIGINAL)
        body["work_id"] = "other-work"
        self.assertFalse(download("wrong_work", body))

    def test_http_error_cannot_be_success_even_with_matching_json(self):
        self.assertFalse(download("http_403_matching_body", copy.deepcopy(ORIGINAL), 403))

    def test_control_original_adopted_result_survives(self):
        self.assertTrue(reopened("control_reopen_original", "original-result"))

    def test_another_adopted_result_does_not_prove_original_survived(self):
        self.assertFalse(reopened("reopen_other_result", "other-result"))


def saved_evidence():
    prefix = "evidence/129-u086-strict-download-exit/"
    before = json.loads(source(prefix + "snapshot-before-restart.json"))
    after = json.loads(source(prefix + "snapshot-after-restart.json"))
    checks = json.loads(source(prefix + "checks.json"))
    source(prefix + "README.md")
    work = next(w for w in after["works"] if w["id"] == checks["workId"])
    return {
        "claimed_checks": checks["passed"], "check_names": len(checks["checks"]),
        "before_protocol": before.get("protocol"), "before_error": before.get("code"),
        "after_protocol": after.get("protocol"), "work_status": work["status"],
        "recorded_model_requests": len({s["model_request_id"] for s in work["steps"]}),
        "steps": [{k: s.get(k) for k in ["seq", "status", "model_request_id", "usage"]}
                  for s in work["steps"]],
        "budget": work.get("budget"), "known_usage": work.get("usage"),
        "cost_status": work.get("cost_status"),
        "delivered_result_id": work.get("delivered_result_id"),
        "tool_calls": [{k: t.get(k) for k in ["seq", "tool", "step_ref", "sha256", "bytes"]}
                       for t in work.get("tool_calls", [])],
        "results": [{k: r.get(k) for k in ["id", "status", "sha256", "bytes", "sources"]}
                    for r in work["results"]],
        "scope": "saved Core records; no independent remote dispatch or billing verification",
    }


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(StrictDownloadReview))
    report = {
        "candidate": CANDIDATE, "tests": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "probes": RESULTS, "saved_evidence": saved_evidence(), "sources": SOURCES,
        "real_model_calls_added": 0,
    }
    if REPORT:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
