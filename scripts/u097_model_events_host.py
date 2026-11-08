"""Isolated HTTP/SQLite browser fixture; gated model double, no external model."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.model_access_support import ModelAccessCase


def main():
    case = ModelAccessCase()
    case.setUp()
    phase = [1]
    try:
        case.saved()
        case.allow_documents()
        case.resource_grant()
        case.provider.result_state = "running"
        original = case.provider.request
        def running(request_id, au_id):
            return original(request_id, au_id) | {"result": None}
        def events(request_id, au_id, after=0):
            data = [{"request_id": request_id, "seq": 1, "type": "text_delta",
                     "payload": {"text": "正在生成的片段一"}, "created_at": "2026-11-09"},
                    {"request_id": request_id, "seq": 2, "type": "native_event",
                     "payload": {"text": "private-native-canary"}, "created_at": "2026-11-09"}]
            if phase[0] == 2:
                data.append({"request_id": request_id, "seq": 3, "type": "text_delta",
                             "payload": {"text": "，片段二"}, "created_at": "2026-11-09"})
            return {"events": [e for e in data if e["seq"] > after]}
        with patch.object(case.provider, "request", side_effect=running), patch.object(case.provider, "events", side_effect=events):
            receipt, _ = case.start_check()
            def wait_seq(seq):
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    check = next(c for c in case.models()["checks"] if c["id"] == receipt["check_id"])
                    if check["attempts"] and check["attempts"][0]["usage"]["observed_through_seq"] >= seq:
                        return check["attempts"][0]["id"]
                    time.sleep(.02)
                raise AssertionError("fixture did not persist its prefix")
            attempt = wait_seq(2)
            def info():
                return {"origin": case.server.origin, "organization_id": case.au_id,
                        "cookie_name": case.server.cookie_name, "token": case.token,
                        "check_id": receipt["check_id"], "attempt_id": attempt,
                        "inference_posts": len(case.provider.requests), "real_model_calls": 0}
            print(json.dumps(info()), flush=True)
            for line in sys.stdin:
                op = json.loads(line)["op"]
                if op == "stop": break
                if op == "advance": phase[0] = 2; wait_seq(3)
                elif op == "restart": case.stop(); case.start()
                elif op == "revoke": case.provider.revoked = True
                elif op != "status": raise AssertionError("unknown fixture operation")
                print(json.dumps(info()), flush=True)
    finally:
        case.doCleanups()


if __name__ == "__main__":
    main()
