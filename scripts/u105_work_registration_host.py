"""Disposable authenticated Core host; no Work pre-created and no inference allowed."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_core_work_registration import WorkRegistrationTests

case = WorkRegistrationTests()
try:
    case.setUp()
    documents = case.root / "controlled-docs"
    documents.mkdir()
    (documents / "overview.txt").write_text("U105 controlled input", encoding="utf-8")
    (case.root / "document-roots.json").write_text(json.dumps({
        "version": 1, "roots": {"project-docs": str(documents)}}), encoding="utf-8")
    print(json.dumps({"origin": case.server.origin, "organization_id": case.au_id,
                      "cookie_name": case.server.cookie_name, "token": case.token}), flush=True)
    sys.stdin.readline()
    assert case.provider.requests == {}, "registration unexpectedly dispatched inference"
    print(json.dumps({"model_requests": 0}), flush=True)
finally:
    case.doCleanups()
