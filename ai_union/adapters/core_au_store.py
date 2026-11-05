"""Narrow V1 create/read storage. It never constructs or invokes legacy Engine."""
from contextlib import closing
import json
import os
import sqlite3

from ..domain.creation import FIELDS, prepared_state, valid_principal, validate_creation
from ..errors import CoreError, Rejected, require

INCOMPATIBLE = "AU 准备态记录不完整或不兼容；请保留原记录核对"
CAPABILITIES = {"read": True, "autonomous_business": False, "charter_enforcement": "not_activated"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class CoreAUStore:
    def create(self, directory, data, *, au_id, principal, request_id, created_at):
        require(not directory.exists(), "分配目录已存在；请核对原创建请求")
        directory.mkdir(parents=True, mode=0o700)
        database = directory / "state.sqlite3"
        fd = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        state = prepared_state(au_id, data, principal)
        with closing(sqlite3.connect(database)) as cx, cx:
            cx.execute("BEGIN IMMEDIATE")
            cx.execute("CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)")
            cx.execute("CREATE TABLE charters(version INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            cx.execute("CREATE TABLE creation_adoptions(request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, au_id TEXT NOT NULL, profile TEXT NOT NULL, charter_version INTEGER NOT NULL, adopted_at TEXT NOT NULL)")
            cx.execute("INSERT INTO state VALUES(1,?)", (encoded(state),))
            cx.execute("INSERT INTO charters VALUES(1,?)", (encoded(data["charter"]),))
            cx.execute("INSERT INTO creation_adoptions VALUES(?,?,?,?,?,?)", (request_id, principal, au_id, "core_v1", 1, created_at))
        return state

    @staticmethod
    def read_in(cx, au_id, *, creation=None):
        try:
            row = cx.execute("SELECT data FROM state WHERE id=1").fetchone()
            require(row is not None, INCOMPATIBLE)
            state = json.loads(row[0])
            require(isinstance(state, dict) and state.get("id") == au_id, INCOMPATIBLE)
            require(state.get("runtime_profile") == "core_v1" and type(state.get("schema_version")) is int and state["schema_version"] == 1, INCOMPATIBLE)
            require(state.get("autonomy_state") == "inactive" and state.get("resource_state") == "planned", INCOMPATIBLE)
            for name, expected in (("version", 0), ("charter_version", 1), ("policy_version", 0)):
                require(type(state.get(name)) is int and state[name] == expected, INCOMPATIBLE)
            root = state.get("governance_root")
            require(isinstance(root, dict) and set(root) == {"creator_principal_id", "governor_principal_id"}, INCOMPATIBLE)
            require(valid_principal(root["creator_principal_id"]) and root["creator_principal_id"] == root["governor_principal_id"], INCOMPATIBLE)
            charter = cx.execute("SELECT data FROM charters WHERE version=1").fetchone()
            require(charter is not None, INCOMPATIBLE)
            data = {key: state.get(key) for key in FIELDS if key != "charter"} | {"charter": json.loads(charter[0])}
            validate_creation(data)
            adoptions = cx.execute("SELECT request_id,principal_id,au_id,profile,charter_version,adopted_at FROM creation_adoptions").fetchall()
            require(len(adoptions) == 1, INCOMPATIBLE)
            adoption = adoptions[0]
            require(adoption[1:5] == (root["creator_principal_id"], au_id, "core_v1", 1)
                    and isinstance(adoption[0], str) and bool(adoption[0]) and isinstance(adoption[5], str) and bool(adoption[5]), INCOMPATIBLE)
            if creation is not None:
                receipt = json.loads(creation["receipt"])
                request = json.loads(creation["payload"])
                require(creation["profile"] == "core_v1" and creation["allocated_au_id"] == au_id
                        and tuple(adoption) == (creation["id"], creation["creator_principal_id"], au_id,
                                                "core_v1", 1, receipt["created_at"]), INCOMPATIBLE)
                require(request["id"] == creation["id"] and request["kind"] == "create_v1"
                        and request["data"] == data, INCOMPATIBLE)
            return {"protocol": "core.au.v1", "au": state | {"charter": data["charter"]}, "capabilities": dict(CAPABILITIES)}
        except (Rejected, ValueError, TypeError, KeyError) as error:
            raise CoreError("incompatible_state", INCOMPATIBLE) from error
        except sqlite3.DatabaseError as error:
            if getattr(error, "sqlite_errorcode", None) in (sqlite3.SQLITE_ERROR, sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_SCHEMA):
                raise CoreError("incompatible_state", INCOMPATIBLE) from error
            raise

    def read(self, directory, au_id, *, creation=None):
        database = directory / "state.sqlite3"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as cx:
            cx.execute("PRAGMA query_only=ON")
            cx.execute("BEGIN")
            return self.read_in(cx, au_id, creation=creation)
