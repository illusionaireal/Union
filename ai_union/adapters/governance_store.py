"""One AU transaction for effective governance, immutable origins and receipts."""
from contextlib import closing, contextmanager
import hashlib
import json
import sqlite3

from .core_au_store import encoded
from ..domain import governance as rules
from ..domain import responsibility
from ..errors import CoreError, require

EVENT_FIELDS = ("version", "command_id", "principal_id", "kind", "reason", "created_at", "prior_policy_version", "command_hash", "previous_hash", "hash", "snapshot")
COMMAND_FIELDS = ("id", "principal_id", "payload", "receipt", "hash")


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def origin_in(cx):
    rows = cx.execute("SELECT state,charter FROM governance_origin WHERE id=1").fetchall()
    require(len(rows) == 1, "缺少原创建快照")
    require(cx.execute("SELECT data FROM charters WHERE version=1").fetchone()[0] == rows[0][1], "原章程快照发生改变")
    return json.loads(rows[0][0]), digest(list(rows[0]))


def commands_in(cx, au_id):
    records = {}
    for raw in cx.execute("SELECT " + ",".join(COMMAND_FIELDS) + " FROM governance_commands"):
        row = dict(zip(COMMAND_FIELDS, raw))
        require(row["hash"] == digest({key: value for key, value in row.items() if key != "hash"}), "原治理请求或回执完整性校验失败")
        request, receipt = json.loads(row["payload"]), json.loads(row["receipt"])
        require(request["id"] == receipt["id"] == row["id"] and request["organization_id"] == receipt["organization_id"] == au_id
                and receipt["actor_principal_id"] == row["principal_id"] and request["kind"] == receipt["kind"]
                and request["base_version"] == receipt["base_version"], "原治理请求、主体或回执不一致")
        records[row["id"]] = row | {"request": request, "value": receipt}
    return records


def read_in(cx, state, origin):
    charter_row = cx.execute("SELECT data FROM charters WHERE version=?", (state["charter_version"],)).fetchone()
    require(charter_row is not None, "缺少有效章程版本")
    charter = json.loads(charter_row[0])
    rules.validate_state(state, origin, charter)
    responsibility.validate_state(state)
    if state["schema_version"] == 3:
        from .model_access_store import ModelAccessStore
        ModelAccessStore.validate(cx, state)
    records = commands_in(cx, state["id"])
    charters = {row[0]: json.loads(row[1]) for row in cx.execute("SELECT version,data FROM charters")}
    _, previous = origin_in(cx)
    history = []
    rows = cx.execute("SELECT " + ",".join(EVENT_FIELDS) + " FROM governance_events ORDER BY version").fetchall()
    require(len(rows) == state["version"], "治理审计版本不连续")
    last = None
    for version, raw in enumerate(rows, 1):
        event = dict(zip(EVENT_FIELDS, raw))
        require(event["version"] == version and event["previous_hash"] == previous
                and event["hash"] == digest({key: value for key, value in event.items() if key != "hash"}), "治理审计完整性校验失败")
        command = records.get(event["command_id"])
        require(command is not None and command["principal_id"] == event["principal_id"]
                and command["hash"] == event["command_hash"], "治理采用缺少原请求或原回执")
        request, receipt = command["request"], command["value"]
        adopted = receipt["status"] == "succeeded" or (request["kind"] == "submit_local_result" and receipt.get("effect") == "evidence_only" and receipt["status"] == "rejected")
        require(request["kind"] == event["kind"] and request["base_version"] == version - 1
                and request["organization_id"] == state["id"] and adopted
                and receipt["version"] == version, "治理回执与有效状态不一致")
        last = json.loads(event["snapshot"])
        require(last["state"]["version"] == version and last["state"]["governance_root"] == origin["governance_root"], "治理历史身份不连续")
        require(last["charter"] == charters.get(last["state"]["charter_version"]), "历史有效章程与采用依据不一致")
        previous = event["hash"]
        history.append({key: event[key] for key in EVENT_FIELDS[:7]})
    require(last == {"state": state, "charter": charter}, "当前治理记录与最后有效采用不一致")
    require(cx.execute("SELECT COUNT(*) FROM charters").fetchone()[0] == state["charter_version"], "章程历史不连续")
    return {"protocol": "core.au.v1", "au": state | {"charter": charter}, "history": history,
            "capabilities": {"read": True, "local_governance": True, "autonomous_business": False,
                "charter_enforcement": "supported_local_rules", "supported_operations": ["record_memory"],
                "unavailable": ["model_dispatch", "resource_use", "external_commitment", "autonomous_business"]}}


class GovernanceStore:
    @staticmethod
    def has_commands(cx):
        return cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='governance_commands'").fetchone() is not None

    def ensure_commands(self, cx):
        # An explicit first command may reject without adopting schema 2; its
        # immutable issuer receipt still needs the same durable owner.
        if not self.has_commands(cx):
            cx.execute("CREATE TABLE governance_commands(id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, payload TEXT NOT NULL, receipt TEXT NOT NULL, hash TEXT NOT NULL)")

    @contextmanager
    def transaction(self, directory):
        database = directory / "state.sqlite3"
        with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True, timeout=10)) as cx, cx:
            cx.row_factory = sqlite3.Row
            cx.execute("BEGIN IMMEDIATE")
            yield cx

    def initialize(self, cx):
        state = cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0]
        charter = cx.execute("SELECT data FROM charters WHERE version=1").fetchone()[0]
        cx.execute("CREATE TABLE governance_origin(id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL, charter TEXT NOT NULL)")
        self.ensure_commands(cx)
        cx.execute("CREATE TABLE governance_events(version INTEGER PRIMARY KEY, command_id TEXT NOT NULL UNIQUE, principal_id TEXT NOT NULL, kind TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, prior_policy_version INTEGER NOT NULL, command_hash TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL, snapshot TEXT NOT NULL)")
        cx.execute("INSERT INTO governance_origin VALUES(1,?,?)", (state, charter))

    def existing(self, cx, request, principal):
        if not self.has_commands(cx):
            return None
        row = cx.execute("SELECT principal_id,payload,receipt FROM governance_commands WHERE id=?", (request["id"],)).fetchone()
        if row is None:
            return None
        if row[0] != principal:
            raise CoreError("not_authorized")
        if row[1] != encoded(request):
            raise CoreError("id_conflict", "请求标识已用于不同参数；请查询原回执")
        return json.loads(row[2])

    def save(self, cx, state, charter, request, receipt, prior_policy, *, changed):
        if changed:
            rules.validate_state(state, origin_in(cx)[0], charter)
            responsibility.validate_state(state)
            require(json.loads(encoded(state)) == state, "状态序列化不能改变对象身份或事实")
        command = {"id": request["id"], "principal_id": receipt["actor_principal_id"], "payload": encoded(request), "receipt": encoded(receipt)}
        command["hash"] = digest(command)
        cx.execute("INSERT INTO governance_commands VALUES(?,?,?,?,?)", tuple(command[key] for key in COMMAND_FIELDS))
        if not changed:
            return
        previous = cx.execute("SELECT hash FROM governance_events ORDER BY version DESC LIMIT 1").fetchone()
        event = {"version": state["version"], "command_id": request["id"], "principal_id": receipt["actor_principal_id"],
                 "kind": request["kind"], "reason": request["data"].get("reason", ""), "created_at": receipt["created_at"],
                 "prior_policy_version": prior_policy, "command_hash": command["hash"], "previous_hash": previous[0] if previous else origin_in(cx)[1],
                 "snapshot": encoded({"state": state, "charter": charter})}
        event["hash"] = digest(event)
        cx.execute("INSERT INTO governance_events VALUES(?,?,?,?,?,?,?,?,?,?,?)", tuple(event[key] for key in EVENT_FIELDS))
        if not cx.execute("SELECT 1 FROM charters WHERE version=?", (state["charter_version"],)).fetchone():
            cx.execute("INSERT INTO charters VALUES(?,?)", (state["charter_version"], encoded(charter)))
        cx.execute("UPDATE state SET data=? WHERE id=1", (encoded(state),))

    def receipt(self, directory, au_id, request_id, principal, creation):
        from .core_au_store import CoreAUStore
        with closing(sqlite3.connect((directory / "state.sqlite3").as_uri() + "?mode=ro", uri=True)) as cx:
            cx.execute("PRAGMA query_only=ON")
            cx.execute("BEGIN")
            value = CoreAUStore.read_in(cx, au_id, creation=creation)
            if not self.has_commands(cx):
                raise CoreError("not_authorized")
            row = cx.execute("SELECT principal_id,receipt FROM governance_commands WHERE id=?", (request_id,)).fetchone()
            if row is None or row[0] != principal:
                raise CoreError("not_authorized")
            return json.loads(row[1])
