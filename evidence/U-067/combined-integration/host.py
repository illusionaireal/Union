"""Isolated combined-candidate fixture; stdout is private browser setup only."""
import hashlib
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.test_core_work_http import WorkHttpChainTests, work_data
from tests.test_work_transport_http import ModeldDouble


case = WorkHttpChainTests()
try:
    case.setUp()
    case.prepare_work()
    source = "a 正文\n"
    result_text = "# 组合验收概览\n来源 nested/a.md：" + source
    ModeldDouble.result = {
        "message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "combined-read", "type": "function", "function": {
                "name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]},
        "usage": {"input_tokens": 5, "output_tokens": 2}}
    code, value, _ = case.run_step()
    assert code == 200 and value["receipt"]["tool_calls"] == 1
    ModeldDouble.result = {"message": {"role": "assistant", "content": result_text},
                          "usage": {"input_tokens": 8, "output_tokens": 4}}
    code, value, _ = case.run_step()
    assert code == 200 and value["receipt"]["result"]
    sent = [body for method, path, _, body in ModeldDouble.seen
            if method == "POST" and path == "/v1/requests"]
    assert len(sent) == 2
    messages = sent[-1]["messages"]
    assert any(m.get("role") == "tool" and json.loads(m["content"]).get("content") == source
               for m in messages)

    code, completed_read, _ = case.request("/api/v1/work?organization_id=" + case.au_id)
    assert code == 200
    first = next(w for w in completed_read["works"] if w["id"] == "work-http")
    attempt = next(a for a in first["attempts"] if a["status"] == "running")
    code, value, _ = case.work_command(case.au_id, "finish_attempt", {
        "work_id": "work-http", "attempt_id": attempt["id"], "outcome": "stopped",
        "reason": "controlled two-turn bound reached; candidate remains readable"})
    assert code == 200 and value["receipt"]["status"] == "succeeded"

    pending_id = "work-pending"
    code, value, _ = case.work_command(case.au_id, "start_work", work_data(
        work_id=pending_id, title="未确认的独立工作", member_id="m-pending",
        binding_id="b-pending", mandate_id="ma-pending", definition_id="d-pending"))
    assert code == 200 and value["receipt"]["status"] == "succeeded", value.get("receipt", {}).get("message")
    code, value, _ = case.work_command(case.au_id, "start_attempt", {"work_id": pending_id})
    assert code == 200 and value["receipt"]["status"] == "succeeded"
    original = {"id": str(uuid.uuid4()), "organization_id": case.au_id,
                "base_version": case.read()["au"]["version"], "kind": "run_step",
                "data": {"work_id": pending_id}}
    ModeldDouble.state = "interrupted"
    code, value, _ = case.request("/api/v1/work/commands", original)
    assert code == 200 and value["receipt"]["model_outcome"] == "unknown"
    assert case.read()["au"]["schema_version"] == 4
    code, before, _ = case.request("/api/v1/work?organization_id=" + case.au_id)
    assert code == 200
    by_id = {w["id"]: w for w in before["works"]}
    completed = by_id["work-http"]
    pending = by_id[pending_id]
    assert completed["budget"]["used"] == 2 and completed["budget"]["reserved"] == 0
    assert completed["tool_calls"][0]["sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert pending["budget"]["reserved"] == 1 and pending["budget"]["used"] == 0
    assert pending["steps"][0]["status"] == "unknown"
    ids = [w["model_request_id"] for card in by_id.values() for w in card["steps"]]
    assert len(ids) == len(set(ids)) == 3
    posts = sum(method == "POST" and path == "/v1/requests" for method, path, _, _ in ModeldDouble.seen)
    assert posts == 3

    case.stop()
    case.start()
    case.app.work.transport_factory = case.channel
    code, value, _ = case.request("/api/v1/work/commands", original)
    receipt = value.get("receipt", value)
    assert code == 200 and receipt["model_outcome"] == "unknown"
    code, reopened, _ = case.request("/api/v1/work?organization_id=" + case.au_id)
    assert code == 200
    reopened = {w["id"]: w for w in reopened["works"]}
    for key in ["steps", "budget", "results", "tool_calls"]:
        for work_id in by_id:
            assert reopened[work_id][key] == by_id[work_id][key], (work_id, key)
    assert sum(method == "POST" and path == "/v1/requests" for method, path, _, _ in ModeldDouble.seen) == posts
    print(json.dumps({"origin": case.server.origin, "organization_id": case.au_id,
                      "cookie_name": case.server.cookie_name, "token": case.token,
                      "expected_result": result_text, "model_posts": posts}), flush=True)
    sys.stdin.readline()
    assert sum(method == "POST" and path == "/v1/requests" for method, path, _, _ in ModeldDouble.seen) == posts
finally:
    if hasattr(case, "double"):
        case.tearDown()
    case.doCleanups()
