"""Disposable authenticated host; two explicit fake turns, never real inference."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_core_result_delivery import ResultDeliveryTests

case = ResultDeliveryTests()
try:
    case.setUp()
    case.prepare_candidate()
    case.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                           "enabled": False, "make_default": False})
    other, _ = case.participant("u106-outsider")
    print(json.dumps({"origin": case.server.origin, "organization_id": case.au_id,
                      "cookie_name": case.server.cookie_name, "token": case.token, "other_token": other,
                      "work_id": "work-overview", "result": case.result}), flush=True)
    sys.stdin.readline()
    assert len(case.channel.calls) == 2 and case.provider.requests == {}
    print(json.dumps({"fake_model_calls": 2, "real_model_calls": 0}), flush=True)
finally:
    case.doCleanups()
