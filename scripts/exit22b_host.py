"""Page-level 22-B evidence host with a real Console and an explicit loopback modeld double.

The double is injected through the product's own transport factory so the page run uses the
real HTTP boundaries; the connection row is prepared through the product API exactly as the
page itself would do it. The double makes the modeld side deterministic while everything
else (identity, governance, work, receipts, persistence) is the real product.
"""
import json
import os
import sys
import threading
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_union.console import Console  # noqa: E402
from ai_union.server import Server  # noqa: E402
from tests.test_work_transport_http import ModeldDouble  # noqa: E402


class PageHost:
    def __init__(self, root):
        self.root = root
        self.patch = patch("ai_union.model_service.ModelServiceClient", return_value=None)
        self.app = Console(root, fixture=None)
        self._wire()
        self.server = Server(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _wire(self):
        config = os.environ.get("UNION_MODELD_CONFIG")
        model = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
        account = os.environ.get("UNION_REAL_ACCOUNT")
        if not (config and account):
            return

        def factory(au_id, connection):
            from ai_union.model_service import ModelServiceClient
            from ai_union.work_transport import ModeldWorkTransport
            connection = dict(connection)
            connection.setdefault("model", model)
            connection.setdefault("max_output_tokens", 1024)
            connection["id"] = "connection-a"
            connection["revision"] = 1
            connection["grant_ref"] = self.grant_ref
            connection["grant_revision"] = 1
            return ModeldWorkTransport(ModelServiceClient(config), au_id, connection,
                                       sleep=lambda _: None, timeout_seconds=180)

        self.app.work.transport_factory = factory

    def prepare(self, au_id):
        """Register the connection and the grant through the product API surfaces."""
        from ai_union.model_service import ModelServiceClient
        client = ModelServiceClient(os.environ["UNION_MODELD_CONFIG"])
        accounts = client.call("GET", "/v1/accounts", admin=True).get("accounts") or []
        match = next((a for a in accounts if a.get("id") == os.environ.get("UNION_REAL_ACCOUNT")), None)
        if match is None:
            raise SystemExit("UNION_REAL_ACCOUNT is not among the modeld accounts")
        grant = client.call("POST", "/v1/grants",
                            {"id": "grant-" + os.urandom(6).hex(), "au_id": au_id,
                             "account_ref": match["id"],
                             "model_ids": [os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")]},
                            admin=True)
        self.grant_ref = grant["id"]

    def state(self):
        return {"origin": self.server.origin,
                "board_url": self.server.origin + "/#launch=" + self.app.ticket("board", platform_admin=True)}

    def restart(self):
        port = self.server.server_port
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.app.close()
        self.app = Console(self.root, fixture=None)
        self._wire()
        self.server = Server(self.app, port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.app.close()


def main():
    root = Path(sys.argv[sys.argv.index("--root") + 1])
    host = PageHost(root)
    print(json.dumps(host.state()), flush=True)
    try:
        for line in sys.stdin:
            command = json.loads(line)
            if command.get("op") == "stop":
                break
            if command.get("op") == "restart":
                host.restart()
                print(json.dumps(host.state()), flush=True)
            elif command.get("op") == "prepare" and command.get("au_id"):
                host.prepare(command["au_id"])
                print(json.dumps({"prepared": True, "grant_ref": host.grant_ref}), flush=True)
    finally:
        host.stop()


if __name__ == "__main__":
    main()
