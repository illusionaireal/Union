"""Cut a disposable HTTP cancel response after commit, never the saved receipt."""
import importlib.util
import os
import socket
from pathlib import Path
from unittest.mock import patch

previous = Path(__file__).parents[1] / "page-cancel-action" / "http-host.py"
spec = importlib.util.spec_from_file_location("cancel_fixture", previous)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from ai_union.server import Handler

original_send = Handler.send
fault = os.environ.get("UNION_CANCEL_RESPONSE_FAULT", "normal")


def send(handler, status, value, mime="application/json; charset=utf-8", headers=None):
    if (handler.command != "POST" or handler.path != "/api/v1/work/commands"
            or not isinstance(value, dict) or value.get("receipt", {}).get("kind") != "cancel_step"
            or fault == "normal"):
        return original_send(handler, status, value, mime, headers)
    assert status == 200 and value["receipt"]["status"] == "succeeded"
    if fault == "malformed":
        return original_send(handler, 200, b'{"receipt":', mime, headers)
    assert fault in ("body-lost", "denied-body-lost")
    # Send genuine HTTP headers and a partial body. Content-Length deliberately
    # exceeds the bytes sent, so Chromium observes a transport failure after 200.
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
        fixture.host.main()
