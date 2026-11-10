"""Read-only restart audit of the existing U-099/U-100 run; no command replay."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
from urllib.parse import urlencode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--bun", required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("responses_acceptance", Path(__file__).parents[1] / "U-099/acceptance.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runner = module.Acceptance(args.state_dir, args.bun)
    keys = ("id", "attempt_ids", "principal_id", "member_id", "binding_id", "binding_version",
            "work_id", "work_version", "mandate_id", "mandate_version", "agent_definition",
            "versions", "resource_revision", "connection_id", "connection_revision", "grant_ref", "grant_revision")
    try:
        before = runner.request_rows()
        runner.start()
        runner.login()
        models = runner.models()
        audited = {}
        watermarks = {}
        for label in ("normal", "interrupt"):
            original = runner.meta[label + "_check"]
            current = next(c for c in models["checks"] if c["id"] == original["id"])
            assert {k: current[k] for k in keys} == {k: original[k] for k in keys}
            assert len(current["attempts"]) == len(original["attempts"])
            watermarks[label] = []
            for old, new in zip(original["attempts"], current["attempts"]):
                assert {k: v for k, v in old["usage"].items() if k != "observed_through_seq"} == {
                    k: v for k, v in new["usage"].items() if k != "observed_through_seq"}
                old_seq, new_seq = old["usage"]["observed_through_seq"], new["usage"]["observed_through_seq"]
                assert new_seq >= old_seq  # Reconcile may observe later saved events, not new consumption.
                watermarks[label].append({"before": old_seq, "after": new_seq})
            assert current["status"] == ("succeeded" if label == "normal" else "unknown")
            if label == "normal":
                assert module.digest(current["output"]) == runner.meta["normal_verified"]["output_sha256"]
            else:
                assert current["stop_requested"] is True
                assert current["waiting"]["object"] == original["id"]
                assert current["waiting"]["responsible_member_id"] == original["member_id"]
            audited[label] = current
        observed = runner.meta["before_cancel"]
        remote = runner.client.request(observed["request_id"], runner.meta["au_id"])
        assert remote["id"] == observed["request_id"] and remote["au_id"] == runner.meta["au_id"]
        assert remote["state"] == "interrupted" and remote["cancel_requested"] is True
        stream = runner.request("/api/v1/models/events?" + urlencode({"organization_id": runner.meta["au_id"],
            "check_id": observed["check_id"], "attempt_id": observed["request_id"], "after": 0}))
        text = "".join(e.get("text", "") for e in stream["events"] if e["type"] == "text_delta")
        assert hashlib.sha256(text.encode("utf8")[:observed["text_bytes"]]).hexdigest() == observed["text_sha256"]
        assert runner.request_rows() == before and len(before) == 4
        assert models["resources"]["reserved_calls"] == 4
        result = {"passed": True, "checks": audited, "remote": remote,
                  "responsibility_fields": list(keys), "usage_unchanged": True, "observation_watermarks": watermarks,
                  "requests_unchanged": True,
                  "request_count": len(before), "reserved_calls": 4, "prefix_preserved": True,
                  "saved_text_sha256": module.digest(text), "saved_text_bytes": len(text.encode("utf8"))}
        path = runner.root / "u100-restart-audit-private.json"
        assert not path.exists(), "Preserve the original audit; select a new explicit observation label before repeating"
        module.save(path, result)
        print('{"passed":true,"requests":4,"new_requests":0,"reserved_calls":4}')
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
