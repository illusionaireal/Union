"""Exercise the real loopback helper with a slow, single original creation."""
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests import test_http


case = test_http.HTTPTests()
seen = []
finished = threading.Event()
try:
    case.setUp()
    command = case.app.command

    def delayed(token, request):
        seen.append(request["id"])
        try:
            time.sleep(4.5)
            return command(token, request)
        finally:
            finished.set()

    case.app.command = delayed
    au_id = case.create()
    # Creation receipts live in the catalog, before the AU command namespace.
    receipt = case.app.receipt(case.board, None, "create-http")
    assert receipt["status"] == "succeeded", receipt["status"]
    assert receipt["organization_id"] == au_id
    assert seen == ["create-http"], seen
    print(json.dumps({"delayed_seconds": 4.5, "original_request_count": len(seen),
                      "original_receipt": "succeeded", "real_model_calls": 0}))
finally:
    if seen:
        finished.wait(30)
    case.doCleanups()
