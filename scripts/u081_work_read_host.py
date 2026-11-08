"""Private, isolated S03 HTTP/SQLite fixture for the U-081 browser check."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_core_work_http import WorkHttpChainTests


case = WorkHttpChainTests()
try:
    case.setUp()
    case.prepare_work()
    status, result, _ = case.run_step()
    assert status == 200 and result["receipt"]["status"] == "succeeded", result
    status, work, _ = case.request("/api/v1/work?organization_id=" + case.au_id)
    assert status == 200 and work["works"][0]["results"], work
    # The one-time test cookie is consumed privately by the browser process.
    print(json.dumps({"origin": case.server.origin, "organization_id": case.au_id,
                      "cookie_name": case.server.cookie_name, "token": case.token}), flush=True)
    sys.stdin.readline()
finally:
    if hasattr(case, "double"):
        case.tearDown()
    case.doCleanups()
