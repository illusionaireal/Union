"""The single catalog writer for durable creation intents and registration."""
import hashlib
import json

from ..domain import creation as rules
from ..engine import encoded, uid
from ..errors import CoreError, Rejected, require


class CreationCatalog:
    def __init__(self, app):
        self.app = app

    def allocate(self, request, receipt, profile, authorize=None):
        with self.app.catalog() as cx:
            principal = authorize(cx) if authorize else None
            row = cx.execute("SELECT * FROM creations WHERE id=?", (request["id"],)).fetchone()
            if row:
                if profile == "core_v1":
                    if row["profile"] != profile or row["creator_principal_id"] != principal:
                        raise CoreError("not_authorized")
                    if row["payload"] != encoded(request):
                        raise CoreError("id_conflict", "请求标识已用于不同参数；请查询原回执")
                else:
                    require(row["profile"] == "legacy_v0", "未找到此请求；请保留原请求标识核对")
                    require(row["payload"] == encoded(request), "请求标识已用于不同参数；请查询原回执")
                return dict(row), False
            if profile == "core_v1":
                try:
                    rules.validate_creation(request["data"])
                except Rejected as error:
                    raise CoreError("invalid_request", str(error)) from error
            allocated = uid("org") if profile == "core_v1" else None
            folder = "organizations/" + hashlib.sha256(request["id"].encode()).hexdigest()
            if allocated:
                receipt = receipt | {"organization_id": allocated}
            intent = {"id": request["id"], "payload": encoded(request), "receipt": encoded(receipt), "folder": folder,
                      "profile": profile, "creator_principal_id": principal, "allocated_au_id": allocated}
            cx.execute("INSERT INTO creations(id,payload,receipt,folder,profile,creator_principal_id,allocated_au_id) VALUES(?,?,?,?,?,?,?)",
                       tuple(intent[key] for key in ("id", "payload", "receipt", "folder", "profile", "creator_principal_id", "allocated_au_id")))
            return intent, True

    def save_receipt(self, intent, receipt):
        with self.app.catalog() as cx:
            cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), intent["id"]))

    def register(self, intent, receipt):
        with self.app.catalog() as cx:
            cx.execute("INSERT INTO organizations(id,folder,profile) VALUES(?,?,?)", (receipt["organization_id"], intent["folder"], intent["profile"]))
            cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), intent["id"]))

    def recover(self):
        with self.app.catalog() as cx:
            for row in cx.execute("SELECT id,receipt FROM creations").fetchall():
                receipt = json.loads(row["receipt"])
                if receipt["status"] == "accepted":
                    receipt.update(status="unknown", message="创建过程被中断；保留原目录，请在宿主核对。不要重复创建。")
                    cx.execute("UPDATE creations SET receipt=? WHERE id=?", (encoded(receipt), row["id"]))

    def receipt(self, request_id, principal):
        with self.app.read_catalog() as cx:
            row = cx.execute("SELECT * FROM creations WHERE id=?", (request_id,)).fetchone()
        if row is None or row["profile"] != "core_v1" or row["creator_principal_id"] != principal:
            raise CoreError("not_authorized")
        return json.loads(row["receipt"])

    def creator(self, au_id):
        intent = self.intent_for_au(au_id)
        return intent["creator_principal_id"] if intent else None

    def intent_for_au(self, au_id):
        with self.app.read_catalog() as cx:
            rows = cx.execute("SELECT * FROM creations WHERE allocated_au_id=? AND profile='core_v1'", (au_id,)).fetchall()
        return dict(rows[0]) if len(rows) == 1 else None

    def authorized_entry(self, au_id, principal):
        with self.app.read_catalog() as cx:
            row = cx.execute("SELECT * FROM organizations WHERE id=?", (au_id,)).fetchone()
        intent = self.intent_for_au(au_id)
        if row is None or intent is None or intent["creator_principal_id"] != principal:
            raise CoreError("not_authorized")
        return dict(row), intent
