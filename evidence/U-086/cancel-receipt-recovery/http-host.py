"""Disposable Core HTTP/SQLite host, one fake inference and one fake cancel."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.test_cancel_delivery_observation import CancelDeliveryObservationTests

case = CancelDeliveryObservationTests()


def ready():
    step = case.works()["works"][0]["steps"][0]
    return {"origin": case.server.origin, "cookie_name": case.server.cookie_name, "token": case.token,
            "receipt": case.original,
            "reference": {"organization_id": case.au_id, "work_id": "work-overview",
                          "cancel_id": case.cancel_request["id"], "principal_id": case.principal,
                          **{key: step[key] for key in ("step_ref", "attempt_id", "command_id",
                                                       "model_request_id", "connection")}}}


try:
    case.setUp()
    case.prepare_delivery()
    print(json.dumps(ready()), flush=True)
    for line in sys.stdin:
        if line.strip() == "stop":
            break
        assert line.strip() == "reopen"
        case.stop()
        case.start()
        assert len(case.client.bodies) == len(case.cancellations) == 1
        print(json.dumps(ready()), flush=True)
    assert len(case.client.bodies) == len(case.cancellations) == 1
finally:
    if not case.doCleanups():
        raise AssertionError("fixture cleanup failed")
