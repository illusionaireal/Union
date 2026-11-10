"""Read exact public evidence blobs; never execute the candidate or a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


DEFAULT_COMMIT = "02dc3f37a4c0ad0c43e33b1cce1a18db2b2fd556"
ROOT = Path(__file__).resolve().parents[3]


def audit(commit: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("an exact 40-character commit SHA is required")
    hashes = {}

    def read(path: str) -> bytes:
        value = subprocess.run(
            ["git", "show", f"{commit}:{path}"], cwd=ROOT,
            capture_output=True, check=True,
        ).stdout
        hashes[path] = hashlib.sha256(value).hexdigest()
        return value

    supplement = "evidence/U-086/original-id-supplement-2026-11-10.md"
    read(supplement)
    runs = {}
    for number, directory in (
        (127, "127-u086-real-interrupt-exit"),
        (134, "134-u086-interrupt-final-verification"),
        (139, "139-u086-original-output-gate-exit"),
    ):
        prefix = f"evidence/{directory}/"
        suffix = "-final-head" if number == 127 else ""
        snapshot = json.loads(read(prefix + f"snapshot-after-restart{suffix}.json"))
        checks = json.loads(read(prefix + f"checks{suffix}.json"))
        before = json.loads(read(prefix + "snapshot-before-restart.json"))
        work = next(w for w in snapshot["works"] if w["id"] == checks["workId"])
        steps = work["steps"]
        cancelled = next(s for s in steps if s.get("cancel_requested_at"))
        labels = checks["checks"]
        cancel_label = next(x for x in labels if x.startswith("cancel accepted by the product: "))
        try:
            receipt = json.loads(cancel_label.split(": ", 1)[1])
            complete_cancel_json = isinstance(receipt, dict)
        except json.JSONDecodeError:
            complete_cancel_json = False
        known_usage = {
            key: sum(s.get("usage", {}).get(key, 0) for s in steps)
            for key in ("input_tokens", "output_tokens")
        }
        # The sum describes only fields present in saved steps; it is not an
        # estimate of missing usage. Retain that distinction explicitly below.
        runs[str(number)] = {
            "snapshot_path": prefix + f"snapshot-after-restart{suffix}.json",
            "nonce": checks.get("nonce"),
            "au_id": snapshot["organization_id"],
            "principal_id": snapshot["access"]["principal_id"],
            "step_records": [
                {key: step.get(key) for key in (
                    "step_ref", "attempt_id", "command_id", "model_request_id",
                    "status", "model_outcome", "usage", "reason",
                )}
                for step in steps
            ],
            "distinct_saved_request_ids": len({s["model_request_id"] for s in steps}),
            "cancelled_request_id_matches_check_label": any(
                cancelled["model_request_id"] in label for label in labels
            ),
            "cancelled_request_usage_present": "usage" in cancelled,
            "cancelled_request_model_outcome": cancelled.get("model_outcome"),
            "cancelled_request_has_saved_interrupted_status": cancelled.get("model_outcome") == "interrupted",
            "cancel_label_contains_complete_json": complete_cancel_json,
            "receipt_identity_check_labels": [label for label in labels if (
                "receipt identifies" in label or "receipt id matches" in label
                or "original GET" in label
            )],
            "checks_top_level_fields": sorted(checks),
            "original_output_check_present": "original request text observed before cancel" in labels,
            "before_snapshot_is_core_work": before.get("protocol") == "core.work.v1",
            "budget": work["budget"],
            "known_usage_subtotal": known_usage,
            "reported_usage_equals_known_subtotal": all(
                snapshot.get("usage", {}).get(key) == value
                for key, value in known_usage.items()
            ),
            "unknown_usage_included_in_subtotal": False,
        }

    earlier, selected, later = (runs[str(n)] for n in (127, 134, 139))
    return {
        "status": "record_audit_completed",
        "commit": commit,
        "source_sha256": hashes,
        "runs": runs,
        "structural_controls": {
            "all_cancelled_ids_match_check_labels": all(r["cancelled_request_id_matches_check_label"] for r in runs.values()),
            "all_reported_usage_matches_known_subtotals": all(r["reported_usage_equals_known_subtotal"] for r in runs.values()),
            "three_distinct_aus": len({r["au_id"] for r in runs.values()}) == 3,
        },
        "supplement_134_claims": {
            "saved_request_count": selected["distinct_saved_request_ids"],
            "verified_remote_invocation_count": None,
            "modeld_interrupted_status_recorded": selected["cancelled_request_has_saved_interrupted_status"],
            "complete_cancel_receipt_json": selected["cancel_label_contains_complete_json"],
            "127_review_binds_134_run": earlier["au_id"] == selected["au_id"],
            "later_139_has_output_check": later["original_output_check_present"],
            "full_22c_acceptance_established": False,
        },
        "limits": [
            "Selected public artifacts only; no assertion that other private records do not exist.",
            "Receipt check labels are retained evidence, not independently recomputed full receipts.",
            "The later 139 output check does not by itself prove page-visible real output or full acceptance.",
            "Persisted request records are not verified remote invocation or billing counts.",
            "This is documentary consistency analysis, not a product behavioral test or model run.",
        ],
        "real_model_calls_by_audit": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default=DEFAULT_COMMIT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.commit)
    except (ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Record input unavailable or invalid: {type(error).__name__}\n")
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": report["status"], "commit": report["commit"],
        "blobs": len(report["source_sha256"]), "controls": report["structural_controls"],
        "full_acceptance_established": False, "real_model_calls": 0,
    }))
