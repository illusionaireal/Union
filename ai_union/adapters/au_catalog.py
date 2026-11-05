"""Resolve a registered legacy AU before any runtime writes are allowed."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from ..engine import Rejected, identifier, require, validate_charter, validate_resources


INCOMPATIBLE = "组织存储不完整或不兼容；请保留原记录并在宿主核对"
LEGACY_TABLES = {
    "state": {"id", "data"},
    "meta": {"key", "value"},
    "charters": {"version", "data", "board", "reason", "adopted_at"},
    "events": {"id", "kind", "data", "created_at", "consumed"},
    "decisions": {"id", "actor", "data", "status", "reason", "created_at"},
    "runs": {"id", "kind", "work_id", "executor", "status", "package", "result", "usage", "started_at", "ended_at"},
}


def _check_legacy_state(cx, organization_id):
    tables = {row[0] for row in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    require(LEGACY_TABLES.keys() <= tables, INCOMPATIBLE)
    schemas = LEGACY_TABLES | ({"commands": {"id", "payload", "receipt"}} if "commands" in tables else {})
    for table, columns in schemas.items():
        actual = {row[1] for row in cx.execute(f"PRAGMA table_info({table})")}
        require(columns <= actual, INCOMPATIBLE)
    row = cx.execute("SELECT data FROM state WHERE id=1").fetchone()
    require(row is not None, INCOMPATIBLE)
    state = json.loads(row[0])
    require(isinstance(state, dict), INCOMPATIBLE)
    require(state.get("id") == organization_id, "组织标识与登记目录不一致；请保留原记录并在宿主核对")
    require(state.get("runtime_profile", "legacy_v0") == "legacy_v0", INCOMPATIBLE)
    # Existing legacy state has no schema marker. Do not infer support for a
    # future schema from a familiar AU ID or from the rest of its fields.
    require("schema_version" not in state, INCOMPATIBLE)
    for name in ("name", "goal", "phase"):
        require(isinstance(state.get(name), str) and bool(state[name]), INCOMPATIBLE)
    for name, minimum in (("version", 0), ("charter_version", 1), ("policy_version", 0)):
        require(type(state.get(name)) is int and state[name] >= minimum, INCOMPATIBLE)
    for name in ("members", "positions", "assignments", "policy", "work", "artifacts", "resources"):
        require(isinstance(state.get(name), dict), INCOMPATIBLE)
    for name in ("memory", "strategy", "wakeups"):
        require(isinstance(state.get(name), list), INCOMPATIBLE)
    charter = cx.execute("SELECT data FROM charters WHERE version=?", (state["charter_version"],)).fetchone()
    require(charter is not None, INCOMPATIBLE)
    try:
        validate_charter(json.loads(charter[0]))
        validate_resources(state["resources"])
    except Rejected as error:
        raise Rejected(INCOMPATIBLE) from error
    authority = dict(cx.execute("SELECT key,value FROM meta WHERE key IN ('board_name','board_salt','board_hash')"))
    require(set(authority) == {"board_name", "board_salt", "board_hash"}
            and all(isinstance(value, str) and value for value in authority.values()), INCOMPATIBLE)


def legacy_directory(root, entry):
    root = Path(root).resolve()
    identifier(entry["id"])
    require(entry.get("profile", "legacy_v0") == "legacy_v0", INCOMPATIBLE)
    require(isinstance(entry["folder"], str) and bool(entry["folder"]), INCOMPATIBLE)
    try:
        directory = (root / entry["folder"]).resolve()
    except (ValueError, RuntimeError) as error:
        raise Rejected(INCOMPATIBLE) from error
    require(directory != root / "organizations" and directory.is_relative_to(root / "organizations"),
            "组织目录超出服务范围；请保留原记录并在宿主核对")
    database = directory / "state.sqlite3"
    require(directory.is_dir() and database.is_file(), INCOMPATIBLE)
    require(database.resolve() == database, INCOMPATIBLE)
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=10)) as cx:
            cx.execute("PRAGMA query_only=ON")
            cx.execute("BEGIN")
            _check_legacy_state(cx, entry["id"])
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise Rejected(INCOMPATIBLE) from error
    except sqlite3.DatabaseError as error:
        if getattr(error, "sqlite_errorcode", None) in (
                sqlite3.SQLITE_ERROR, sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_SCHEMA):
            raise Rejected(INCOMPATIBLE) from error
        # Busy/I/O failures remain storage failures, not an invented identity verdict.
        raise
    return directory
