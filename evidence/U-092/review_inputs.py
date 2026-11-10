"""Bind the unpublished U092 candidate before importing its test fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import re


REFERENCE = Path(__file__).resolve().parent / "duty-review-20261110" / "validation.json"


def prepare_candidate(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--candidate-manifest", type=Path,
                        help="Explicit revised input: JSON containing source_files_sha256")
    parser.add_argument("--manifest-sha256", help="SHA256 of that manifest's exact bytes")
    args = parser.parse_args(argv)
    candidate, report = args.candidate.resolve(), args.report.resolve()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    expected = reference["source_files_sha256"]
    binding = {
        "mode": "historical_snapshot",
        "historical_snapshot_manifest_sha256": reference["source_manifest_sha256"],
        "candidate_manifest_sha256": None,
    }

    def stop(status, reason, **details):
        value = {"status": status, "reason": reason, "source_binding": binding,
                 "tests": 0, "observations": [], "real_model_calls": 0,
                 "candidate_imported": False, **details}
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(f"U092 review {status}: {reason}. No behavioral tests ran.")
        raise SystemExit(2)

    if bool(args.candidate_manifest) != bool(args.manifest_sha256):
        stop("input_invalid", "Supply both --candidate-manifest and --manifest-sha256")
    if args.candidate_manifest:
        try:
            raw = args.candidate_manifest.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != args.manifest_sha256:
                stop("input_invalid", "The supplied manifest SHA256 does not match")
            manifest = json.loads(raw)
            revised = manifest.get("source_files_sha256") if isinstance(manifest, dict) else None
            if not isinstance(revised, dict) or revised.keys() != expected.keys():
                stop("input_invalid", "The manifest must cover exactly the 20 historical source paths")
            if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                   for value in revised.values()):
                stop("input_invalid", "Each source digest must be a lowercase SHA256")
            expected = revised
            binding.update(mode="explicit_candidate", candidate_manifest_sha256=digest)
        except (OSError, ValueError):
            stop("input_invalid", "Cannot read a valid candidate manifest")

    missing, mismatched, actual = [], [], {}
    for name, digest in expected.items():
        try:
            actual[name] = hashlib.sha256((candidate / name).read_bytes()).hexdigest()
        except OSError:
            missing.append(name)
            continue
        if actual[name] != digest:
            mismatched.append(name)
    binding["source_files_sha256"] = actual
    if missing or mismatched:
        stop("input_unavailable" if missing else "input_mismatch",
             "Provide the unpublished recovery source and fixture for the selected manifest; "
             "the clean integration checkout alone is insufficient",
             missing=missing, mismatched=mismatched)
    return candidate, report, binding
