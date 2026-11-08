"""Disposable Core HTTP/SQLite host; one bounded loopback model request only."""
import json
import sqlite3
import sys
import threading
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_union.model_service import ModelServiceClient
from ai_union.work_transport import ModeldWorkTransport
from tests.test_core_work_http import WorkHttpChainTests, CONNECTION
from tests.test_work_transport_http import ModeldDouble


def main():
    case = WorkHttpChainTests()
    finish = threading.Event()
    cancel_delivery = threading.Event()
    model_requests = []
    cancellations = []

    def post(handler):
        route = urlsplit(handler.path)
        body = handler._body()
        if route.path == "/v1/requests":
            assert not model_requests, "the fixture permits one fake model request"
            model_requests.append(body)
            return handler._send(202, {"id": body["id"], "au_id": body["au_id"], "state": "queued"})
        assert route.path.endswith("/cancel"), "unexpected fake model mutation"
        identity = {"id": unquote(route.path.split("/")[-2]),
                    "au_id": parse_qs(route.query)["au_id"][0]}
        assert model_requests and identity == {k: model_requests[0][k] for k in identity}
        cancellations.append(identity)
        assert cancel_delivery.wait(20), "fixture cancel delivery gate was not released"
        return handler._send(200, identity | {"state": "cancel_requested"})

    def get(handler):
        route = urlsplit(handler.path)
        if route.path.endswith("/events"):
            return handler._send(200, {"events": []})
        state = "interrupted" if finish.is_set() else "cancel_requested" if cancellations else "running"
        return handler._send(200, {"id": unquote(route.path.rsplit("/", 1)[-1]),
                                  "au_id": parse_qs(route.query)["au_id"][0], "state": state, "result": None})

    def ready():
        return {"origin": case.server.origin, "organization_id": case.au_id,
                "cookie_name": case.server.cookie_name, "token": case.token}

    def inspect():
        with sqlite3.connect(case.database()) as cx:
            state = json.loads(cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0])
            work = state["work_runtime"]["works"]["work-http"]
            return {"fake_model_calls": len(model_requests), "cancel_posts": len(cancellations),
                    "real_model_calls": 0, "work_id": work["id"],
                    "loop_command_ids": [loop["command_id"] for loop in work.get("loops", [])],
                    "steps": [{k: s.get(k) for k in ("status", "step_ref", "model_request_id", "command_id")}
                              for s in work.get("steps", [])]}

    try:
        case.setUp()
        case.prepare_work()
        # Keep observation paced; the public transport and deadlines stay unchanged.
        case.app.work.transport_factory = lambda au, connection: ModeldWorkTransport(
            ModelServiceClient(str(case.config)), au, CONNECTION, timeout_seconds=30, poll_seconds=0.1)
        with patch.object(ModeldDouble, "do_POST", post), patch.object(ModeldDouble, "do_GET", get):
            print(json.dumps(ready()), flush=True)
            for line in sys.stdin:
                command = line.strip()
                if command == "finish":
                    finish.set()
                    cancel_delivery.set()
                    value = {"released": True}
                elif command == "release-cancel":
                    cancel_delivery.set()
                    value = {"cancel_released": True}
                elif command == "inspect":
                    value = inspect()
                elif command in {"disable", "enable"}:
                    connection = case.models()["connections"][0]
                    enabled = command == "enable"
                    case.model_success("set_connection", {
                        "connection_id": connection["id"], "expected_revision": connection["revision"],
                        "enabled": enabled, "make_default": enabled})
                    status, value, _ = case.request("/api/v1/work?organization_id=" + case.au_id)
                    assert status == 200 and value["access"]["can_start"] == enabled
                elif command == "reopen":
                    assert finish.is_set()
                    assert not case.app.work.active_loops and not case.app.work.active_steps
                    case.stop()
                    case.start()
                    value = ready()
                else:
                    raise ValueError("unsupported fixture control")
                print(json.dumps(value), flush=True)
    finally:
        finish.set()
        cancel_delivery.set()
        if hasattr(case, "double"):
            case.tearDown()
        case.doCleanups()


if __name__ == "__main__":
    main()
