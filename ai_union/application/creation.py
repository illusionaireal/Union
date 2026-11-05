"""One durable creation workflow; profile selects an explicit storage contract."""
import json
import sqlite3

from ..adapters.au_catalog import allocated_directory, resolve_directory
from ..adapters.core_au_store import CoreAUStore
from ..adapters.creation_catalog import CreationCatalog
from ..adapters.legacy_au_store import LegacyAUStore
from ..domain.creation import valid_principal
from ..engine import encoded, identifier, now
from ..errors import CoreError, Rejected, require


class CreationService:
    def __init__(self, app):
        self.app = app
        self.catalog = CreationCatalog(app)
        self.legacy = LegacyAUStore()
        self.core = CoreAUStore()

    @staticmethod
    def principal(session):
        if not valid_principal(session.get("principal_id")) or not session.get("account"):
            raise CoreError("not_authorized")
        return session["principal_id"]

    def create_v1(self, token, session, request):
        self.principal(session)
        try:
            require(set(request) == {"id", "organization_id", "base_version", "kind", "data"}, "无效命令字段")
            identifier(request["id"])
            require(request["organization_id"] is None and request["base_version"] is None, "创建不应引用已有组织版本")
            require(isinstance(request["data"], dict) and len(encoded(request)) <= 200000, "命令数据无效或过大")
        except (Rejected, ValueError, TypeError, KeyError) as error:
            raise CoreError("invalid_request", str(error)) from error
        receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")}
        receipt.update(actor=session["actor"], created_at=now(), status="accepted", message="创建已受理，保留原请求标识")
        return self.create(request, receipt, authorize=lambda cx: self.app.identity.principal_in(cx, token))

    def create(self, request, receipt, authorize=None):
        require(request["organization_id"] is None and request["base_version"] is None, "创建不应引用已有组织版本")
        profile = "core_v1" if request["kind"] == "create_v1" else "legacy_v0"
        with self.app.mutex:
            intent, allocated = self.catalog.allocate(request, receipt, profile, authorize)
            receipt = json.loads(intent["receipt"])
            if not allocated:
                return receipt
            try:
                store = self.core if profile == "core_v1" else self.legacy
                directory = allocated_directory(self.app.root, intent["folder"])
                state = store.create(directory, request["data"], au_id=intent["allocated_au_id"],
                                     principal=intent["creator_principal_id"], request_id=request["id"], created_at=receipt["created_at"])
                receipt.update(organization_id=state["id"], status="succeeded",
                               message="AU已准备；治理根已绑定，自主行动尚未启用" if profile == "core_v1" else "组织已创建并采用章程；尚未启动执行")
                self.catalog.register(intent, receipt)
            except (Rejected, KeyError, TypeError) as error:
                receipt.update(status="rejected", message=str(error) if isinstance(error, Rejected) else "创建字段类型不正确")
                self.catalog.save_receipt(intent, receipt)
            except (OSError, sqlite3.Error):
                receipt.update(status="unknown", message="创建存储过程未确认；保留分配目录与原请求，请在宿主核对")
                self.catalog.save_receipt(intent, receipt)
            return receipt

    def read(self, session, au_id):
        principal = self.principal(session)
        try:
            identifier(au_id)
        except Rejected as error:
            raise CoreError("invalid_request", str(error)) from error
        entry, intent = self.catalog.located_entry(au_id)
        try:
            directory, profile = resolve_directory(self.app.root, entry, creation=intent)
            require(profile == "core_v1", "AU profile 不兼容")
            result = self.core.read(directory, au_id, creation=intent)
        except Rejected as error:
            raise CoreError("incompatible_state", "AU 目录或治理记录不完整或不兼容；请保留原记录核对") from error
        return self.app.governance.project(result, principal)
