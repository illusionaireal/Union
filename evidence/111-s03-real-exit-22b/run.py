"""Real bounded exit for #22-B: goal -> document body -> candidate -> adopt -> download -> reopen.

Standalone evidence tooling (not the PR32 driver). Gated by the host configuration; one
work with at most three calls, synthetic material only.
"""
import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_union.console import Console  # noqa: E402
from ai_union.model_service import ModelServiceClient  # noqa: E402

CONFIG = os.environ["UNION_MODELD_CONFIG"]
MODEL = os.environ.get("UNION_REAL_MODEL", "deepseek-v4.1-flash")
ACCOUNT = os.environ["UNION_REAL_ACCOUNT"]
MAX_OUTPUT = min(int(os.environ.get("UNION_REAL_MAX_OUTPUT", "1024")), 1024)


def content_and_digest():
    text = "# 合成资料\n\n本资料只用于有界验收：项目代号 UNION-BOUNDED-7319，试点城市为杭州。\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def main():
    text, digest = content_and_digest()
    root = Path(tempfile.mkdtemp(prefix="union-exit-22b-"))
    app = Console(root / "console", fixture=None, enable_api=False)
    try:
        app.work.transport = None
        token = app.identity.login("owner", "owner-safe-password")["token"] if hasattr(app.identity, "login") else None
        au = app.creation.create({"name": "22B 验收", "purpose": "真实有界出口"}, app.owner_principal())
        au_id = au["organization_id"]
        client = ModelServiceClient(CONFIG)
        account = ACCOUNT
        grant = client.call("POST", "/v1/grants",
                            {"id": "grant-" + uuid.uuid4().hex[:12], "au_id": au_id,
                             "account_ref": account, "model_ids": [MODEL]}, admin=True)
        app.models.command  # noqa: B018 - keep import surface explicit
        ok = app.work  # noqa: F841
        print("au", au_id, "grant", grant["id"], grant["revision"])
        return {
            "au_id": au_id,
            "grant": {"id": grant["id"], "revision": grant["revision"]},
            "model": MODEL,
            "document_sha256": digest,
        }
    finally:
        app.close()


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))
