"""Temporary real HTTP/SQLite host; modeld is an explicit loopback double."""
import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_core_work_http import WorkHttpChainTests
from tests.test_work_transport_http import ModeldDouble

case = WorkHttpChainTests()
release = threading.Event()
original_post = ModeldDouble.do_POST


def pending_post(handler):
    if not release.wait(30):
        raise TimeoutError("U084 controlled model was not released")
    return original_post(handler)


try:
    case.setUp()
    case.prepare_work()
    ModeldDouble.result = {"message": {"role": "assistant", "content": "# U084 controlled result\n"},
                          "usage": {"input_tokens": 11, "output_tokens": 4}}
    pending = "--pending-receipt" in sys.argv
    with patch.object(ModeldDouble, "do_POST", pending_post if pending else original_post):
        print(json.dumps({"origin": case.server.origin, "organization_id": case.au_id,
                          "cookie_name": case.server.cookie_name, "token": case.token}), flush=True)
        if pending:
            sys.stdin.readline()
            release.set()
        sys.stdin.readline()
finally:
    release.set()
    if hasattr(case, "double"):
        case.tearDown()
    case.doCleanups()
