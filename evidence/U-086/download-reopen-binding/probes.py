"""Exercise only an exact download restart block with synthetic observations.

python evidence/U-086/download-reopen-binding/probes.py <commit-or-file> [report]
No driver main, browser, host, credentials, or model calls are executed.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
INPUT = sys.argv[1]
SOURCE_PATH = "scripts/exit22c_download.cjs"
raw = (Path(INPUT).read_bytes() if Path(INPUT).is_file() else
       subprocess.check_output(["git", "show", f"{INPUT}:{SOURCE_PATH}"], cwd=ROOT))
source = raw.decode("utf-8")
starts = list(re.finditer(r"  const (?:after|reopenedResponse) = await page.evaluate\(async auId => \{", source))
assert len(starts) == 1, "missing/ambiguous restart observation boundary"
end = "  fs.writeFileSync(path.join(output, 'snapshot-after-restart.json')"
assert source.count(end) == 1, "missing/ambiguous restart observation end"
BLOCK = source[starts[0].start():source.index(end)]
assert "settledStep" not in BLOCK, "do not confuse download and interrupt drivers"
OBSERVATIONS = {}
SHA = hashlib.sha256("Original synthetic result — 合成资料\n".encode()).hexdigest()
ORIGINAL = {
    "protocol": "core.work.v1", "organization_id": "original-au",
    "works": [{"id": "original-work", "status": "delivered",
               "delivered_result_id": "original-result",
               "results": [{"id": "original-result", "status": "adopted", "sha256": SHA}]}],
}
VM = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const checks = [];
let reads = 0;
const context = {
  ...input.variables,
  page: {evaluate: async (fn, arg) => fn(arg)},
  fetch: async () => {
    reads++;
    return {status: input.status, ok: input.status === 200, json: async () => input.body};
  },
  check: (name, value = true) => {
    if (!value) throw new Error('synthetic observation rejected');
    checks.push(name);
  },
};
(async () => {
  try {
    await vm.runInNewContext('(async () => {' + input.block + '\n})()', context, {timeout: 1000});
    process.stdout.write(JSON.stringify({accepted: true, checks, reads}));
  } catch (error) {
    process.stdout.write(JSON.stringify(error.message === 'synthetic observation rejected'
      ? {accepted: false, checks, reads}
      : {runtime_error: error.name, checks, reads}));
  }
})().catch(() => {process.exitCode = 2;});
"""


def observe(name, body=None, status=200, block=BLOCK):
    result = subprocess.run(
        ["node", "-e", VM], cwd=ROOT, text=True, capture_output=True, check=True, timeout=5,
        input=json.dumps({"block": block, "body": body, "status": status,
                          "variables": {"workId": "original-work", "resultId": "original-result",
                                        "recorded": SHA,
                                        "createdReceipt": {"organization_id": "original-au"}}}),
    )
    observed = json.loads(result.stdout)
    OBSERVATIONS[name] = observed
    return observed


class DownloadRestartBinding(unittest.TestCase):
    def setUp(self):
        self.body = copy.deepcopy(ORIGINAL)
        self.work = self.body["works"][0]
        self.result = self.work["results"][0]

    def rejected(self, status=200):
        observed = observe(self.id().split(".")[-1], self.body, status)
        self.assertNotIn("runtime_error", observed)
        self.assertIs(observed["accepted"], False)
        self.assertEqual(observed["reads"], 1)

    def accepted(self):
        observed = observe(self.id().split(".")[-1], self.body)
        self.assertNotIn("runtime_error", observed)
        self.assertIs(observed["accepted"], True)
        self.assertEqual(observed["reads"], 1)

    def test_original_delivered_result_survives(self):
        self.accepted()

    def test_original_survives_beside_another_adopted_result(self):
        self.work["results"].insert(0, {"id": "another-result", "status": "adopted", "sha256": SHA})
        self.accepted()

    def test_another_adopted_result_cannot_replace_original(self):
        self.result["id"] = "another-result"
        self.work["delivered_result_id"] = "another-result"
        self.rejected()

    def test_original_digest_must_survive(self):
        self.result["sha256"] = "0" * 64
        self.rejected()

    def test_missing_digest_is_not_proof(self):
        del self.result["sha256"]
        self.rejected()

    def test_delivery_must_bind_the_original_result(self):
        self.work["delivered_result_id"] = "another-result"
        self.rejected()

    def test_missing_delivery_binding_is_not_proof(self):
        del self.work["delivered_result_id"]
        self.rejected()

    def test_response_must_be_the_original_au(self):
        self.body["organization_id"] = "another-au"
        self.rejected()

    def test_missing_au_is_not_proof(self):
        del self.body["organization_id"]
        self.rejected()

    def test_response_must_be_a_work_snapshot(self):
        self.body["protocol"] = "unrelated.v1"
        self.rejected()

    def test_missing_protocol_is_not_proof(self):
        del self.body["protocol"]
        self.rejected()

    def test_matching_body_with_http_403_is_not_success(self):
        self.rejected(status=403)

    def test_missing_original_work_is_rejected(self):
        self.work["id"] = "another-work"
        self.rejected()

    def test_undelivered_work_is_rejected(self):
        self.work["status"] = "running"
        self.rejected()

    def test_unadopted_original_result_is_rejected(self):
        self.result["status"] = "candidate"
        self.rejected()

    def test_vm_observes_synchronous_and_awaited_rejections(self):
        for name, block in [("sync", "check('rejection', false);"),
                            ("async", "await Promise.resolve(); check('rejection', false);")]:
            with self.subTest(name=name):
                self.assertIs(observe(name, block=block)["accepted"], False)

    def test_vm_keeps_success_and_runtime_errors_distinct(self):
        observed = observe("async_success", block="await Promise.resolve(); check('success', true);")
        self.assertIs(observed["accepted"], True)
        observed = observe("async_runtime_error", block="await Promise.resolve(); missingSyntheticVariable();")
        self.assertEqual(observed["runtime_error"], "ReferenceError")
        self.assertNotIn("accepted", observed)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(DownloadRestartBinding))
    report = {"source_input": INPUT if not Path(INPUT).is_file() else "candidate driver file",
              "source_path": SOURCE_PATH, "source_sha256": hashlib.sha256(raw).hexdigest(),
              "block_sha256": hashlib.sha256(BLOCK.encode()).hexdigest(),
              "block": BLOCK, "contains_settled_step": False,
              "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "observations": OBSERVATIONS, "real_model_calls": 0,
              "scope": "exact restart block; synthetic HTTP observations only"}
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["source_sha256", "tests", "failures", "errors", "real_model_calls"]}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
