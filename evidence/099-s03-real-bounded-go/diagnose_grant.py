"""Diagnose why saving a modeld_grant connection is refused; no inference is attempted."""
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_union.console import Console
from ai_union.model_service import ModelServiceClient

CONFIG = os.environ["UNION_MODELD_CONFIG"]
MODEL = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
root = tempfile.mkdtemp(prefix="union-diag-")
app = Console(Path(root) / "console", fixture=None, enable_api=False)
token = app.session("owner") if hasattr(app, "session") else None
print("console root", root)
try:
    au = app.creation.create({"name": "Diag AU", "purpose": "diagnostic"}, app.owner_principal())
    au_id = au["organization_id"]
    print("au", au_id)
    client = ModelServiceClient(CONFIG)
    accounts = client.call("GET", "/v1/accounts", admin=True)["accounts"]
    account = accounts[0]["id"]
    grant_id = "grant-" + uuid.uuid4().hex[:12]
    grant = client.call("POST", "/v1/grants",
                        {"id": grant_id, "au_id": au_id, "account_ref": account, "model_ids": [MODEL]}, admin=True)
    print("grant", json.dumps(grant, ensure_ascii=False))
    got = client.call("GET", "/v1/grants/" + grant_id, admin=True)
    print("grant readback", json.dumps(got, ensure_ascii=False))
finally:
    app.close()
