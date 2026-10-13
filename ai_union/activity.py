"""Short lived host evidence, independent of persistent execution results."""
import json
import os
import threading
import time
from contextlib import contextmanager

from .engine import encoded, uid
from .locking import held


@contextmanager
def activity(engine):
    stop = threading.Event()
    owner = uid("host")
    engine._local.host_owner = owner
    path = engine.root / "runner.activity.json"
    temporary = engine.root / (owner + ".tmp")

    def beat():
        temporary.write_text(encoded({"owner": owner, "heartbeat": time.time(), "pid": os.getpid()}), encoding="utf-8")
        temporary.replace(path)

    def keep_alive():
        while not stop.wait(1):
            try:
                beat()
            except OSError:
                return  # Missing evidence must not be represented as healthy.

    beat()
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()
    try:
        yield
    finally:
        engine._local.host_owner = None
        stop.set()
        thread.join()
        path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


def host_activity(engine):
    try:
        record = json.loads((engine.root / "runner.activity.json").read_text(encoding="utf-8"))
        age = time.time() - record["heartbeat"]
        live = 0 <= age <= 5 and held(engine.root / "runner.lock")
        return {"confirmed": live, "owner": record["owner"] if live else None}
    except (OSError, ValueError, KeyError, TypeError):
        return {"confirmed": False, "owner": None}
