"""Truncate one committed registration response on disposable Core HTTP/SQLite."""
import os
import runpy
import socket
import sys
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
from ai_union.server import Handler

original_send = Handler.send
fault = os.environ.get("UNION_REGISTRATION_RESPONSE_FAULT", "normal")


def send(handler, status, value, mime="application/json; charset=utf-8", headers=None):
    if (handler.command != "POST" or handler.path != "/api/v1/work/commands"
            or not isinstance(value, dict) or value.get("receipt", {}).get("kind") != "start_work"
            or fault == "normal"):
        return original_send(handler, status, value, mime, headers)
    assert status == 200 and value["receipt"]["status"] == "succeeded"
    if fault == "malformed":
        return original_send(handler, status, b'{"receipt":', mime, headers)
    if fault == "receipt-body":
        changed = {**value, "receipt": {**value["receipt"], "work_id": "replacement-work"}}
        return original_send(handler, status, changed, mime, headers)
    assert fault in ("body-lost", "denied-body-lost")
    handler.send_response(403 if fault == "denied-body-lost" else 200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", "4096")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(b'{"receipt":')
    handler.wfile.flush()
    handler.connection.shutdown(socket.SHUT_WR)
    handler.close_connection = True


if __name__ == "__main__":
    with patch.object(Handler, "send", send):
        runpy.run_path(str(root / "scripts/u105_work_registration_host.py"), run_name="__main__")
