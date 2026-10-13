"""Private stdin test harness. Fault controls are never exposed by the HTTP service."""
import argparse
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_union.console import Console
from ai_union.engine import encoded
from ai_union.executor import FixtureExecutor, ExecutionFailure
from ai_union.runner import exclusive
from ai_union.server import Server


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--port", type=int, default=0)
    args = p.parse_args()
    fixture = json.loads((Path(__file__).resolve().parents[1] / "examples/fixture.json").read_text(encoding="utf-8"))
    app = Console(args.root, fixture)
    server = Server(app, args.port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    gate = threading.Event()
    gate.set()
    mode = {"unknown": False}
    original = app.executor_factory

    def factory(e, data):
        executor = original(e, data)
        execute = executor.execute
        def controlled(package):
            gate.wait(15)
            if mode["unknown"]:
                mode["unknown"] = False
                raise ExecutionFailure("test injected unknown", unknown=True)
            return execute(package)
        executor.execute = controlled
        return executor
    app.executor_factory = factory
    actor = app.new_session("board")
    originals = {}
    print(encoded({"origin": server.origin, "board_url": server.origin + "/#launch=" + app.ticket("board"),
                   "observer_url": server.origin + "/#launch=" + app.ticket("observer")}), flush=True)
    try:
        for line in sys.stdin:
            command = json.loads(line)
            op = command["op"]
            result = {"ok": True}
            e = app.engine(actor, command["org"]) if command.get("org") else None
            if op == "hold": gate.clear()
            elif op == "release": gate.set()
            elif op == "unknown": mode["unknown"] = True
            elif op == "event": e.add_event(command["id"], "opinion", {"source": "browser-test", "simulated": True, "content": command["id"]})
            elif op == "unconfirmed": result["run_id"] = e.begin_decision("fixture")["run_id"]
            elif op == "recover":
                with exclusive(e): e.recover()
            elif op == "corrupt":
                a=e.state()["artifacts"][command["id"]]
                file=e.root / a["path"]
                originals[str(file)] = file.read_bytes()
                file.write_text("test corruption", encoding="utf-8")
            elif op == "restore":
                for path, content in originals.items(): Path(path).write_bytes(content)
                originals.clear()
            elif op == "expire":
                for session in app.sessions.values(): session["expires"] = 0
            elif op == "ticket":
                result["url"] = server.origin + "/#launch=" + app.ticket(command.get("role", "board"))
            elif op == "state": result["state"] = e.state()
            elif op == "stop":
                print(encoded(result), flush=True)
                break
            else: raise ValueError(op)
            print(encoded(result), flush=True)
    finally:
        gate.set()
        server.shutdown()
        thread.join()
        server.server_close()
        app.close()


if __name__ == "__main__":
    main()
