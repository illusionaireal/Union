"""Run with current-source and an exported 90d8b1f source; no real inference."""
import json
from pathlib import Path
import subprocess
import sys

current, old = (Path(value).resolve() for value in sys.argv[1:3])
sys.path.insert(0, str(current))
from tests.test_work_dispatch_compatibility import WorkDispatchCompatibilityTests

case = WorkDispatchCompatibilityTests("test_failed_prepare_rolls_back_marker_and_intent_before_transport")
case.setUp()
try:
    request = case.arrange()
    channel = case.interrupt_call(request)
    original = case.card()["steps"][0]
    schema = case.state()["schema_version"]
    case.stop()
    before = case.dump()
    old_read = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from ai_union.adapters.core_au_store import CoreAUStore
from ai_union.errors import CoreError
value = json.load(sys.stdin)
try:
    CoreAUStore().read(Path(value['directory']), value['au_id'], creation=value['intent'])
except CoreError as error:
    print(json.dumps({'rejected': True, 'code': error.code}))
else:
    print(json.dumps({'rejected': False}))
"""
    result = subprocess.run([sys.executable, "-c", old_read, str(old)],
                            input=json.dumps({"directory": str(case.directory),
                                              "au_id": case.au_id, "intent": case.intent}),
                            text=True, capture_output=True, check=True)
    observed = json.loads(result.stdout)
    assert observed == {"rejected": True, "code": "incompatible_state"}, observed
    assert case.dump() == before, "old read changed original data"
    case.start()
    case.app.work.transport = channel
    receipt = case.app.work.run_step(case.token, request)
    assert receipt["model_outcome"] == "unknown", receipt
    assert case.card()["steps"][0] == original
    assert len(channel.calls) == 1
    print(json.dumps({"schema": schema, "old_runtime": observed,
                      "original_reservation": original["status"],
                      "reopen_outcome": receipt["model_outcome"],
                      "replayed_model_calls": 0, "real_model_calls": 0}))
finally:
    case.tearDown()
    case.doCleanups()
