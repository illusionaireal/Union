"""Verify the exact review VMs and an author's reopen block, with no driver run.

Usage: python evidence/U-086/review-await-probes.py [author-commit] [report.json]
Requires the pinned Node on PATH. Only synthetic values enter the Node VM.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REVIEW = "a401d2ba3469b48b3125b749c57c21b756536bbf"
AUTHOR = sys.argv[1] if len(sys.argv) > 1 else "970144a"
SOURCES = {}


def source(commit, path):
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    SOURCES[f"{commit}:{path}"] = hashlib.sha256(raw).hexdigest()
    return raw.decode("utf-8")


def run(vm, block, variables=None):
    result = subprocess.run(["node", "-e", vm], cwd=ROOT, text=True,
                            input=json.dumps({"block": block, "variables": variables or {},
                                              "predicate": False, "status": 200}),
                            capture_output=True, timeout=5)
    if result.returncode:
        return {"runtime_error": result.stderr.strip(), "exit": result.returncode}
    return json.loads(result.stdout)


def main():
    controls = {}
    vms = {}
    for name in ("strict-download", "final-interrupt"):
        text = source(REVIEW, f"evidence/U-086/{name}-review-probes.py")
        tree = ast.parse(text)
        vm = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "VM"
                          for target in node.targets))
        vms[name] = vm
        cases = {
            "sync_rejection": ("check('synthetic rejection', false);", False),
            "awaited_rejection": ("await Promise.resolve(); check('synthetic rejection', false);", False),
            "awaited_success": ("await Promise.resolve(); check('synthetic success', true);", True),
        }
        for case, (block, accepted) in cases.items():
            observed = run(vm, block)
            assert observed.get("accepted") is accepted, (name, case, observed)
            controls[name + ":" + case] = observed
        observed = run(vm, "await Promise.resolve(); missingReviewVariable();")
        assert observed == {"runtime_error": "ReferenceError", "exit": 2}, observed
        controls[name + ":runtime_error_is_separate"] = observed

    author = source(AUTHOR, "scripts/exit22c_download.cjs")
    start = "  const entry = (after.works || []).find(w => w.id === workId);"
    end = "  fs.writeFileSync(path.join(output, 'snapshot-after-restart.json')"
    assert author.count(start) == 1 and end in author
    block = start + author.split(start, 1)[1].split(end, 1)[0]
    observations = {}
    for result_id in ("original-result", "other-result"):
        observations[result_id] = run(vms["strict-download"], block, {
            "workId": "original-work", "resultId": "original-result", "recorded": "original-digest",
            "createdReceipt": {"organization_id": "original-au"},
            "after": {"protocol": "core.work.v1", "organization_id": "original-au",
                      "works": [{"id": "original-work", "status": "delivered",
                                 "delivered_result_id": result_id,
                                 "results": [{"id": result_id, "status": "adopted",
                                              "sha256": "original-digest"}]}]},
        })
        assert "runtime_error" not in observations[result_id], observations[result_id]
    report = {"review_commit": REVIEW, "author_commit": subprocess.check_output(
        ["git", "rev-parse", AUTHOR], cwd=ROOT, text=True).strip(),
        "harness_controls": controls, "author_reopen_observations": observations,
        "author_rejects_another_result": observations["other-result"]["accepted"] is False,
        "source_sha256": SOURCES, "real_model_calls": 0,
        "scope": "VM control validation and exact extracted assertions; no driver main or browser"}
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
