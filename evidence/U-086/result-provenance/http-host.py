"""Disposable Console/SQLite host; two controlled fake turns, no real model."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.test_core_result_delivery import ResultDeliveryTests

case = ResultDeliveryTests()


def ready():
    return {"origin": case.server.origin, "organization_id": case.au_id,
            "cookie_name": case.server.cookie_name, "token": case.token,
            "work_id": "work-overview"}


try:
    case.setUp()
    case.prepare_candidate()
    for kind in ("adopt_result", "deliver_work"):
        status, body, _ = case.work_command(case.au_id, kind, case.data)
        assert status == 200 and body["receipt"]["status"] == "succeeded"
    print(json.dumps(ready()), flush=True)
    for line in sys.stdin:
        if line.strip() == "stop":
            break
        assert line.strip() == "reopen"
        case.stop()
        case.start()
        assert len(case.channel.calls) == 2 and case.provider.requests == {}
        print(json.dumps(ready()), flush=True)
    assert len(case.channel.calls) == 2 and case.provider.requests == {}
finally:
    if not case.doCleanups():
        raise AssertionError("fixture cleanup failed")
