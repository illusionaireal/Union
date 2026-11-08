"""Temporary real HTTP/SQLite host; modeld is an explicit loopback double."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_core_work_http import WorkHttpChainTests
from tests.test_work_transport_http import ModeldDouble

case = WorkHttpChainTests()
try:
    case.setUp()
    case.prepare_work()
    ModeldDouble.result = {"message": {"role": "assistant", "content": "# U084 controlled result\n"},
                          "usage": {"input_tokens": 11, "output_tokens": 4}}
    print(json.dumps({"origin": case.server.origin, "organization_id": case.au_id,
                      "cookie_name": case.server.cookie_name, "token": case.token}), flush=True)
    sys.stdin.readline()
finally:
    if hasattr(case, "double"):
        case.tearDown()
    case.doCleanups()
