"""Review input failures must not masquerade as U092 product failures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "U-092"
RUNNERS = [EVIDENCE / directory / "probes.py" for directory in
           ("duty-review-20261110", "superseded-recovery-review")]
REFERENCE = EVIDENCE / "duty-review-20261110" / "validation.json"


class ReviewInputTests(unittest.TestCase):
    def invoke(self, runner, candidate, report, *args):
        return subprocess.run([sys.executable, "-B", str(runner), str(candidate),
                               str(report), *args], capture_output=True,
                              text=True, encoding="utf-8", timeout=15)

    def test_missing_candidate_is_input_failure_before_import(self):
        for runner in RUNNERS:
            with self.subTest(runner=runner.parent.name), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                candidate = base / "candidate"
                candidate.mkdir()
                report = base / "report.json"
                result = self.invoke(runner, candidate, report)
                self.assertEqual(result.returncode, 2, result.stderr)
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["status"], "input_unavailable")
                self.assertEqual(data["tests"], 0)
                self.assertEqual(data["observations"], [])
                self.assertIn("tests/test_work_recovery.py", data["missing"])
                self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_explicit_repaired_candidate_is_bound_without_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = base / "candidate"
            files = {}
            for name in json.loads(REFERENCE.read_text(encoding="utf-8"))["source_files_sha256"]:
                file = candidate / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b"explicit revised candidate\n")
                files[name] = hashlib.sha256(file.read_bytes()).hexdigest()
            manifest = base / "candidate-manifest.json"
            manifest.write_text(json.dumps({"source_files_sha256": files}), encoding="utf-8")
            digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
            spec = importlib.util.spec_from_file_location("u092_review_inputs", EVIDENCE / "review_inputs.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            found, report, binding = module.prepare_candidate([
                str(candidate), str(base / "report.json"),
                "--candidate-manifest", str(manifest), "--manifest-sha256", digest])
            self.assertEqual(found, candidate.resolve())
            self.assertEqual(binding["mode"], "explicit_candidate")
            self.assertEqual(binding["candidate_manifest_sha256"], digest)
            self.assertEqual(binding["source_files_sha256"], files)
            self.assertFalse(report.exists(), "input validation cannot report behavioral success")
            # An explicitly supplied manifest is not permission to ignore later drift.
            (candidate / "tests/test_work_recovery.py").write_bytes(b"different fixture\n")
            for runner in RUNNERS:
                result = self.invoke(runner, candidate, report, "--candidate-manifest",
                                     str(manifest), "--manifest-sha256", digest)
                self.assertEqual(result.returncode, 2, result.stderr)
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["mismatched"], ["tests/test_work_recovery.py"])

    def test_invalid_or_unbound_manifest_is_input_failure(self):
        cases = [
            (b"{}", "wrong-digest"),
            (b"not json", None),
            (b'{"source_files_sha256": {"../outside.py": "bad"}}', None),
        ]
        for raw, supplied_digest in cases:
            for runner in RUNNERS:
                with self.subTest(raw=raw, runner=runner.parent.name), tempfile.TemporaryDirectory() as tmp:
                    base = Path(tmp)
                    manifest = base / "manifest.json"
                    manifest.write_bytes(raw)
                    report = base / "report.json"
                    result = self.invoke(runner, base, report, "--candidate-manifest", str(manifest),
                                         "--manifest-sha256", supplied_digest or hashlib.sha256(raw).hexdigest())
                    self.assertEqual(result.returncode, 2, result.stderr)
                    data = json.loads(report.read_text(encoding="utf-8"))
                    self.assertEqual(data["status"], "input_invalid")
                    self.assertFalse(data["candidate_imported"])
                    self.assertEqual(data["tests"], 0)

    def test_revised_manifest_requires_explicit_digest(self):
        for runner in RUNNERS:
            with self.subTest(runner=runner.parent.name), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                report = base / "report.json"
                result = self.invoke(runner, base, report, "--candidate-manifest", str(base / "missing.json"))
                self.assertEqual(result.returncode, 2, result.stderr)
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["status"], "input_invalid")
                self.assertEqual(data["tests"], 0)
                self.assertEqual(data["observations"], [])
                self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_wrong_source_never_imports_candidate(self):
        for runner in RUNNERS:
            with self.subTest(runner=runner.parent.name), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                candidate = base / "candidate"
                paths = json.loads(REFERENCE.read_text(encoding="utf-8"))["source_files_sha256"]
                for name in paths:
                    file = candidate / name
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text("changed source\n", encoding="utf-8")
                marker = base / "imported"
                (candidate / "ai_union" / "__init__.py").write_text(
                    f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
                    encoding="utf-8")
                report = base / "report.json"
                result = self.invoke(runner, candidate, report)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(marker.exists(), "candidate imported before source validation")
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["status"], "input_mismatch")
                self.assertEqual(len(data["mismatched"]), 20)
                self.assertEqual(data["tests"], 0)


if __name__ == "__main__":
    unittest.main()
