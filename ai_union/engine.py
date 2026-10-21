"""Persistent organization mechanisms. Agent proposals never grant authority."""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import math
import re
import sqlite3
import threading
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path


OPERATIONS = {"create_member", "create_position", "update_position", "assign", "set_policy", "create_work",
              "handoff", "pause_work", "resume_work", "cancel_work", "update_work",
              "wait", "set_strategy", "record_memory", "submit_chapter", "review_cycle"}
TOOLS = {"produce_artifact", "workspace_execute"}
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class Rejected(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Rejected(reason)


def model_name(value):
    if value is None or value == "":
        return None
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value) is not None,
            "模型名称需为 1–128 位字母、数字或 . _ : / -，且以字母或数字开头；留空使用 CLI 默认")
    return value


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return prefix + "-" + uuid.uuid4().hex


def instant(value):
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(d.tzinfo is not None, "复查时间必须包含时区")
        return d.astimezone(timezone.utc)
    except (TypeError, AttributeError, ValueError) as e:
        raise Rejected("无效的带时区时间") from e


def text(value, label, limit=100000):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit, label + "必须是非空且有界的文本")
    return value


def identifier(value):
    require(isinstance(value, str) and bool(ID.fullmatch(value)), "无效对象标识")
    return value


def validate_charter(c):
    require(isinstance(c, dict), "章程必须是对象")
    fields = {"text", "allowed_operations", "allowed_tools", "reserved_matters", "board_can_amend"}
    require(set(c) == fields, "章程只支持明确的正文、操作、工具、保留事项和修章字段")
    text(c["text"], "章程正文")
    for field, known in (("allowed_operations", OPERATIONS), ("allowed_tools", TOOLS),
                         ("reserved_matters", {"goal", "resources", "charter", "funding", "dissolution"})):
        require(isinstance(c[field], list) and all(isinstance(v, str) for v in c[field])
                and set(c[field]) <= known, "章程含不支持的 " + field)
    require(type(c["board_can_amend"]) is bool, "修章权限必须显式为布尔值")


def validate_resources(r):
    require(isinstance(r, dict) and set(r) <= {"max_calls", "timeout_seconds", "max_cost", "cost_reserve_per_call"}, "不支持的资源配置；token 仅记录用量")
    require(type(r.get("max_calls")) is int and 0 < r["max_calls"] <= 10000, "必须提供有限的正整数调用上限")
    timeout = r.get("timeout_seconds")
    require(type(timeout) is int and 1 <= timeout <= 3600, "必须提供 1–3600 秒的每次超时")
    for name in ("max_cost", "cost_reserve_per_call"):
        if name in r:
            require(type(r[name]) in (int, float) and math.isfinite(r[name]) and r[name] > 0, "费用配置必须是有限正数")


class Engine:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.db = self.root / "state.sqlite3"
        self._local = threading.local()
        require(self.db.is_file(), "组织尚未初始化")

    @classmethod
    def create(cls, root, name, goal, charter, resources, board_name, board_key):
        validate_charter(charter)
        validate_resources(resources)
        text(name, "组织名称", 200)
        text(goal, "目标")
        text(board_name, "董事会身份", 200)
        text(board_key, "董事会凭据")
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        db = root / "state.sqlite3"
        require(not db.exists(), "不能覆盖已有组织")
        salt = uuid.uuid4().hex
        state = {"id": uid("org"), "name": name, "goal": goal, "version": 0,
                 "charter_version": 1, "policy_version": 0, "phase": "bootstrap",
                 "members": {}, "positions": {}, "assignments": {}, "policy": {},
                 "work": {}, "artifacts": {}, "memory": [], "strategy": [], "wakeups": [],
                 "resources": copy.deepcopy(resources)}
        with closing(sqlite3.connect(db)) as cx, cx:
            cx.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE charters (version INTEGER PRIMARY KEY, data TEXT NOT NULL, board TEXT NOT NULL, reason TEXT NOT NULL, adopted_at TEXT NOT NULL);
                CREATE TABLE events (id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE decisions (id TEXT PRIMARY KEY, actor TEXT NOT NULL, data TEXT NOT NULL, status TEXT NOT NULL, reason TEXT, created_at TEXT NOT NULL);
                CREATE TABLE runs (id TEXT PRIMARY KEY, kind TEXT NOT NULL, work_id TEXT, executor TEXT NOT NULL, status TEXT NOT NULL, package TEXT NOT NULL, result TEXT, usage TEXT, started_at TEXT NOT NULL, ended_at TEXT);
            """)
            cx.execute("INSERT INTO state VALUES(1,?)", (encoded(state),))
            cx.executemany("INSERT INTO meta VALUES(?,?)", [("board_name", board_name), ("board_salt", salt),
                           ("board_hash", hashlib.sha256((salt + board_key).encode()).hexdigest())])
            cx.execute("INSERT INTO charters VALUES(?,?,?,?,?)", (1, encoded(charter), board_name, "initial adoption", now()))
            cx.execute("INSERT INTO events(id,kind,data,created_at) VALUES(?,?,?,?)", (uid("event"), "organization_created", encoded({"charter_version": 1}), now()))
        db.chmod(0o600)
        (root / "assets").mkdir()
        return cls(root)

    @contextmanager
    def transaction(self):
        existing = getattr(self._local, "connection", None)
        if existing is not None:
            savepoint = "nested_" + uuid.uuid4().hex
            existing.execute("SAVEPOINT " + savepoint)
            try:
                yield existing
                existing.execute("RELEASE " + savepoint)
            except BaseException:
                existing.execute("ROLLBACK TO " + savepoint)
                existing.execute("RELEASE " + savepoint)
                raise
            return
        cx = sqlite3.connect(self.db, timeout=10)
        cx.row_factory = sqlite3.Row
        try:
            cx.execute("BEGIN IMMEDIATE")
            self._local.connection = cx
            yield cx
            cx.commit()
        except BaseException:
            cx.rollback()
            raise
        finally:
            self._local.connection = None
            cx.close()

    @contextmanager
    def read_transaction(self):
        with closing(sqlite3.connect(self.db.as_uri() + "?mode=ro", uri=True, timeout=10)) as cx:
            cx.row_factory = sqlite3.Row
            cx.execute("PRAGMA query_only=ON")
            cx.execute("BEGIN")
            yield cx

    def paused(self, cx=None):
        if cx is None:
            with self.read_transaction() as connection:
                return self.paused(connection)
        row = cx.execute("SELECT value FROM meta WHERE key='dispatch_paused'").fetchone()
        return bool(row and row[0] == "true")

    def set_paused(self, value):
        require(type(value) is bool, "暂停意图必须为布尔值")
        with self.transaction() as cx:
            cx.execute("INSERT OR REPLACE INTO meta VALUES('dispatch_paused',?)", (encoded(value),))

    def _state(self, cx):
        return json.loads(cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0])

    def _save(self, cx, s):
        cx.execute("UPDATE state SET data=? WHERE id=1", (encoded(s),))

    def state(self):
        with self.transaction() as cx:
            return self._state(cx)

    def _charter(self, cx, version):
        row = cx.execute("SELECT data FROM charters WHERE version=?", (version,)).fetchone()
        require(row is not None, "章程版本不存在")
        return json.loads(row[0])

    def charter(self, version=None):
        with self.transaction() as cx:
            return self._charter(cx, version or self._state(cx)["charter_version"])

    def _event(self, cx, kind, data, event_id=None):
        cur = cx.execute("INSERT OR IGNORE INTO events(id,kind,data,created_at) VALUES(?,?,?,?)",
                         (event_id or uid("event"), kind, encoded(data), now()))
        return cur.rowcount == 1

    def add_event(self, event_id, kind, data):
        text(event_id, "事件 ID", 200)
        text(kind, "事件类型", 100)
        require(isinstance(data, dict), "事件数据必须是对象")
        with self.transaction() as cx:
            existing = cx.execute("SELECT kind,data FROM events WHERE id=?", (event_id,)).fetchone()
            if existing:
                require(existing["kind"] == kind and existing["data"] == encoded(data), "事件 ID 已被不同回执使用")
                return False
            return self._event(cx, kind, data, event_id)

    def events(self, pending_only=False):
        with self.transaction() as cx:
            rows = cx.execute("SELECT * FROM events " + ("WHERE consumed=0 " if pending_only else "") + "ORDER BY rowid").fetchall()
            return [dict(r) | {"data": json.loads(r["data"])} for r in rows]

    def _assignment(self, s, position_id):
        active = [a for a in s["assignments"].values() if a["position_id"] == position_id and a["active"]]
        require(len(active) == 1, "岗位必须有唯一的有效任职；多席位请建立独立岗位")
        return active[0]

    def _authorize(self, s, c, actor, assignment):
        if actor == "bootstrap":
            require(s["phase"] == "bootstrap", "启动授权已经结束")
            return set(c["allowed_operations"])
        a = s["assignments"].get(assignment)
        require(a is not None and a["active"] and a["member_id"] == actor, "调用身份没有有效任职")
        require(a["position_id"] == s["policy"].get("decision_position_id"), "该岗位没有组织决策责任")
        return set(s["positions"][a["position_id"]]["permissions"]) & set(c["allowed_operations"])

    def apply_decision(self, d, actor, assignment=None, event_ids=None, run_id=None, usage=None):
        require(isinstance(d, dict), "决定必须是对象")
        try:
            with self.transaction() as cx:
                s = self._state(cx)
                c = self._charter(cx, s["charter_version"])
                permissions = self._authorize(s, c, actor, assignment)
                require(d.get("actor_ref", actor) == actor, "决定不能改变绑定的调用身份")
                did = identifier(d.get("id"))
                prior = cx.execute("SELECT * FROM decisions WHERE id=?", (did,)).fetchone()
                if prior:
                    require(prior["actor"] == actor and prior["data"] == encoded(d) and prior["status"] == "accepted", "决定 ID 已被其他内容使用")
                    return s
                for field in ("base_state_version", "charter_version", "policy_version"):
                    expected = s["version"] if field == "base_state_version" else s[field]
                    require(type(d.get(field)) is int and d[field] == expected, "决定版本冲突：" + field)
                for field in ("issue", "rationale", "expected_effect"):
                    text(d.get(field), field)
                require(isinstance(d.get("evidence_refs"), list), "缺少证据引用列表")
                self._check_evidence(cx, s, d["evidence_refs"])
                ops = d.get("operations")
                require(isinstance(ops, list) and len(ops) <= 100, "操作必须是有界列表")
                for op in ops:
                    require(isinstance(op, dict) and op.get("op") in permissions, "操作不在当前章程及岗位授权内")
                    if op["op"] in ("submit_chapter", "review_cycle"):
                        from .company import operate
                        operate(self, cx, s, op, d)
                    else:
                        self._operate(s, c, op)
                if actor == "bootstrap":
                    require(len(s["members"]) >= 2, "启动需要至少两名可区分成员")
                    require(len({a["member_id"] for a in s["assignments"].values() if a["active"]}) >= 2, "启动需要至少两名实际任职成员")
                    require(bool(s["work"]) and s["policy"].get("decision_position_id") in s["positions"], "启动需要工作和决策责任")
                    self._assignment(s, s["policy"]["decision_position_id"])
                    s["phase"] = "active"
                s["version"] += 1
                cx.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)", (did, actor, encoded(d), "accepted", None, now()))
                for event_id in event_ids or []:
                    row = cx.execute("SELECT consumed FROM events WHERE id=?", (event_id,)).fetchone()
                    require(row is not None and not row[0], "决定引用的待处理事件已变化")
                    cx.execute("UPDATE events SET consumed=1 WHERE id=?", (event_id,))
                self._event(cx, "decision_applied", {"decision_id": did, "state_version": s["version"]})
                # The decision's own bookkeeping event must not cause an endless decision loop.
                cx.execute("UPDATE events SET consumed=1 WHERE kind='decision_applied' AND json_extract(data,'$.decision_id')=?", (did,))
                if run_id:
                    self._settle(cx, run_id, "delivered", d, usage or {}, s)
                self._save(cx, s)
                return s
        except (Rejected, TypeError, KeyError) as error:
            e = error if isinstance(error, Rejected) else Rejected("无效的决定字段或对象类型：" + type(error).__name__)
            with self.transaction() as cx:
                cx.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)", (uid("rejected"), actor, encoded(d), "rejected", str(e), now()))
            raise e from error

    def _check_evidence(self, cx, s, refs):
        for ref in refs:
            require(isinstance(ref, str), "证据引用必须是字符串")
            require(ref in s["artifacts"] or ref in s["work"] or cx.execute("SELECT 1 FROM events WHERE id=?", (ref,)).fetchone() is not None, "证据引用不存在：" + ref)

    def _new(self, mapping, value):
        key = identifier(value)
        require(key not in mapping, "对象 ID 已存在：" + key)
        return key

    def _dependencies(self, s, deps, work_id):
        require(isinstance(deps, list) and all(isinstance(d, str) for d in deps) and len(deps) == len(set(deps)) and all(d in s["work"] and d != work_id for d in deps), "无效工作依赖")
        def reaches(key, seen):
            if key == work_id:
                return True
            if key in seen:
                return False
            return any(reaches(x, seen | {key}) for x in s["work"][key]["dependencies"])
        require(not any(reaches(d, set()) for d in deps), "工作依赖不能成环")

    def _operate(self, s, c, o):
        op = o["op"]
        fields = {
            "create_member": {"op", "id", "name"},
            "create_position": {"op", "id", "title", "mandate", "permissions"},
            "update_position": {"op", "position_id", "title", "mandate", "permissions"},
            "assign": {"op", "id", "position_id", "member_id"},
            "set_policy": {"op", "decision_position_id"},
            "create_work": {"op", "id", "title", "instruction", "position_id", "dependencies"},
            "handoff": {"op", "position_id", "member_id", "assignment_id"},
            "pause_work": {"op", "work_id"}, "resume_work": {"op", "work_id"}, "cancel_work": {"op", "work_id"},
            "update_work": {"op", "work_id", "title", "instruction", "dependencies"},
            "wait": {"op", "until", "reason"}, "set_strategy": {"op", "hypothesis"},
            "record_memory": {"op", "content", "conditions", "uncertainty"},
        }
        require(set(o) == fields[op], "操作字段缺失或不支持：" + op)
        if op == "create_member":
            key = self._new(s["members"], o["id"])
            s["members"][key] = {"id": key, "name": text(o["name"], "成员名", 200)}
        elif op in ("create_position", "update_position"):
            key = self._new(s["positions"], o["id"]) if op == "create_position" else identifier(o["position_id"])
            require(op == "create_position" or key in s["positions"], "岗位不存在")
            ps = o["permissions"]
            require(isinstance(ps, list) and all(isinstance(p, str) for p in ps) and set(ps) <= set(c["allowed_operations"] + c["allowed_tools"]), "岗位权限超出章程")
            old = s["positions"].get(key, {})
            s["positions"][key] = {"id": key, "title": text(o["title"], "岗位名", 200), "mandate": text(o["mandate"], "岗位职责"), "permissions": ps, "version": old.get("version", 0) + 1}
            if op == "update_position" and "produce_artifact" not in ps:
                for w in s["work"].values():
                    if w["position_id"] == key and w["status"] not in ("delivered", "cancelled"):
                        w["status"] = "needs_review" if w["status"] == "running" else "paused"
                        w["version"] += 1
        elif op == "assign":
            key = self._new(s["assignments"], o["id"])
            require(o["position_id"] in s["positions"] and o["member_id"] in s["members"], "任职对象不存在")
            require(not any(a["active"] and a["position_id"] == o["position_id"] for a in s["assignments"].values()), "已有任职必须使用交接操作")
            s["assignments"][key] = {"id": key, "position_id": o["position_id"], "member_id": o["member_id"], "active": True}
        elif op == "set_policy":
            require(o["decision_position_id"] in s["positions"], "决策岗位不存在")
            self._assignment(s, o["decision_position_id"])
            s["policy"] = {"decision_position_id": o["decision_position_id"]}
            s["policy_version"] += 1
        elif op == "create_work":
            key = self._new(s["work"], o["id"])
            a = self._assignment(s, o["position_id"])
            require("produce_artifact" in s["positions"][a["position_id"]]["permissions"], "工作岗位缺少成果工具权限")
            self._dependencies(s, o["dependencies"], key)
            s["work"][key] = {"id": key, "title": text(o["title"], "工作名称", 200), "instruction": text(o["instruction"], "工作指令"),
                              "position_id": a["position_id"], "member_id": a["member_id"], "assignment_id": a["id"],
                              "dependencies": o["dependencies"], "version": 1, "status": "pending", "artifact_ids": [], "run_id": None}
        elif op == "handoff":
            a = self._assignment(s, o["position_id"])
            require(o["member_id"] in s["members"], "交接成员不存在")
            key = self._new(s["assignments"], o["assignment_id"])
            a["active"] = False
            s["assignments"][key] = {"id": key, "position_id": o["position_id"], "member_id": o["member_id"], "active": True}
            for w in s["work"].values():
                if w["position_id"] == o["position_id"] and w["status"] not in ("delivered", "cancelled"):
                    w.update(member_id=o["member_id"], assignment_id=key, version=w["version"] + 1)
                    if w["status"] == "running":
                        w["status"] = "needs_review"
        elif op in ("pause_work", "resume_work", "cancel_work", "update_work"):
            w = s["work"].get(o["work_id"])
            forbidden = ("cancelled", "running", "needs_review") if op == "update_work" else ("delivered", "cancelled", "running", "needs_review")
            require(w is not None and w["status"] not in forbidden, "该工作状态不能直接修改；在途工作先核对")
            if op == "resume_work":
                require(w["status"] in ("paused", "blocked", "failed"), "工作不在可恢复状态")
                w["status"] = "pending"
            elif op == "update_work":
                self._dependencies(s, o["dependencies"], w["id"])
                w.update(title=text(o["title"], "工作名称", 200), instruction=text(o["instruction"], "工作指令"), dependencies=o["dependencies"])
                if w["status"] == "delivered":
                    a = self._assignment(s, w["position_id"])
                    w.update(status="pending", member_id=a["member_id"], assignment_id=a["id"])
            else:
                w["status"] = "paused" if op == "pause_work" else "cancelled"
            w["version"] += 1
        elif op == "wait":
            instant(o["until"])
            s["wakeups"].append({"id": uid("wake"), "until": o["until"], "reason": text(o["reason"], "等待依据"), "fired": False})
        elif op == "set_strategy":
            s["strategy"].append({"version": len(s["strategy"]) + 1, "hypothesis": text(o["hypothesis"], "经营假设"), "state_version": s["version"] + 1})
        elif op == "record_memory":
            s["memory"].append({"id": uid("memory"), "version": 1, "content": text(o["content"], "组织记忆"),
                                "conditions": text(o["conditions"], "适用条件"), "uncertainty": text(o["uncertainty"], "不确定性")})

    def _board(self, cx, key):
        meta = dict(cx.execute("SELECT key,value FROM meta").fetchall())
        require(isinstance(key, str) and hmac.compare_digest(meta["board_hash"], hashlib.sha256((meta["board_salt"] + key).encode()).hexdigest()), "董事会凭据无效")
        return meta["board_name"]

    def amend(self, board_key, charter, reason):
        validate_charter(charter)
        text(reason, "修订依据")
        with self.transaction() as cx:
            board = self._board(cx, board_key)
            s = self._state(cx)
            old = self._charter(cx, s["charter_version"])
            require(old["board_can_amend"], "当前章程不允许此修订入口；新章程不能授权自身采用")
            s["charter_version"] += 1
            s["version"] += 1
            cx.execute("INSERT INTO charters VALUES(?,?,?,?,?)", (s["charter_version"], encoded(charter), board, reason, now()))
            # In-flight results must be reconciled; paused pending work can resume under new authority.
            for w in s["work"].values():
                if "produce_artifact" not in charter["allowed_tools"] and w["status"] not in ("delivered", "cancelled"):
                    w["status"] = "needs_review" if w["status"] == "running" else "paused"
                    w["version"] += 1
            self._event(cx, "charter_amended", {"version": s["charter_version"], "reason": reason, "board": board})
            self._save(cx, s)

    def configure_resources(self, board_key, resources, reason):
        validate_resources(resources)
        text(reason, "资源调整依据")
        with self.transaction() as cx:
            board = self._board(cx, board_key)
            s = self._state(cx)
            s["resources"] = resources
            s["version"] += 1
            self._event(cx, "resources_updated", {"board": board, "reason": reason, "resources": resources})
            self._save(cx, s)

    def configure_model(self, board_key, model, reason):
        model = model_name(model)
        text(reason, "模型设置依据")
        with self.transaction() as cx:
            board = self._board(cx, board_key)
            s = self._state(cx)
            s.setdefault("execution_config", {})["codex_model"] = model
            s["version"] += 1
            self._event(cx, "model_configured", {"board": board, "reason": reason, "model": model})
            self._save(cx, s)

    def _read_artifact(self, a):
        path = (self.root / a["path"]).resolve()
        require(path.is_relative_to(self.root / "assets") and path.is_file(), "成果文件不存在或越出资产范围")
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == a["sha256"], "成果完整性校验失败")
        return data.decode("utf-8")

    def _context(self, cx, s, work_id=None):
        c = self._charter(cx, s["charter_version"])
        manifest = {"state_version": s["version"], "charter_version": s["charter_version"], "policy_version": s["policy_version"], "artifacts": [], "work": {}}
        ctx = {"observed_at": now(), "organization": {k: s[k] for k in ("id", "name", "goal", "strategy")}, "charter": c, "policy": s["policy"], "memory": s["memory"], "artifacts": [], "resources": s["resources"], "budget": self._budget(cx, s)}
        if s.get("company"):
            from .company import view
            ctx["company"] = view(s)
            ctx["company"]["published_texts"] = [
                {"chapter_number": ch["chapter_number"], "content": self._read_artifact(s["artifacts"][ch["artifact_id"]])}
                for ch in s["company"]["chapters"]]
        if work_id:
            w = s["work"][work_id]
            a = s["assignments"][w["assignment_id"]]
            ctx.update(position=s["positions"][w["position_id"]], member=s["members"][w["member_id"]], assignment=a, task=w)
            manifest["assignment_id"] = a["id"]
            manifest["position_version"] = s["positions"][w["position_id"]]["version"]
            keys = set()
            def collect(key):
                if key in keys:
                    return
                keys.add(key)
                for dep in s["work"][key]["dependencies"]:
                    collect(dep)
            collect(work_id)
        else:
            keys = set(s["work"])
            ctx.update(members=s["members"], positions=s["positions"], assignments=s["assignments"], work=s["work"])
            ctx["events"] = [dict(r) | {"data": json.loads(r["data"])} for r in cx.execute("SELECT * FROM events WHERE consumed=0 ORDER BY rowid")]
        for key in sorted(keys):
            w = s["work"][key]
            manifest["work"][key] = w["version"]
            for aid in w["artifact_ids"]:
                a = s["artifacts"][aid]
                ctx["artifacts"].append(a | {"content": self._read_artifact(a)})
                manifest["artifacts"].append({"id": aid, "version": a["version"], "sha256": a["sha256"]})
        require(len(encoded(ctx)) <= 300000, "上下文超出首轮容量；需要减少资料范围")
        return {"context": ctx, "manifest": manifest}

    def context(self, work_id=None):
        with self.transaction() as cx:
            return self._context(cx, self._state(cx), work_id)

    def _budget(self, cx, s):
        calls = cx.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        r = s["resources"]
        reserve = r.get("cost_reserve_per_call")
        reason = None
        if calls >= r["max_calls"]:
            reason = "调用额度耗尽；需要董事会配置追加资源"
        elif "max_cost" in r and reserve is None:
            reason = "金额上限缺少可核实的单次费用保留值；禁止启动"
        elif "max_cost" in r and (calls + 1) * reserve > r["max_cost"]:
            reason = "可用金额不足以保留下一次调用费用"
        if s.get("company"):
            from .company import totals
            financials = totals(s["company"])
            if financials["unknown_model_costs"]:
                reason = reason or "模型用量缺失，成本未知；暂停新调用并核对供应商回执"
            elif financials["balance_minor"] <= 0:
                reason = reason or "试验预算已到限；保留进度并停止新派发"
        return {"calls_reserved": calls, "max_calls": r["max_calls"], "cost_status": "unknown",
                "estimated_cost_reserved": calls * reserve if reserve is not None else None, "blocked_reason": reason}

    def _reserve(self, cx, s, kind, executor, package, work_id=None, allow_paused=False):
        require(allow_paused or not self.paused(cx), "派发已暂停；请由受信入口继续")
        budget = self._budget(cx, s)
        require(budget["blocked_reason"] is None, budget["blocked_reason"])
        rid = package.get("run_id") or uid("run")
        package.update(run_id=rid, kind=kind, timeout_seconds=s["resources"]["timeout_seconds"])
        package["host_owner"] = getattr(self._local, "host_owner", None)
        cx.execute("INSERT INTO runs(id,kind,work_id,executor,status,package,started_at) VALUES(?,?,?,?,?,?,?)",
                   (rid, kind, work_id, executor, "running", encoded(package), now()))
        return package

    def begin_work(self, work_id, executor, execution=None):
        with self.transaction() as cx:
            s = self._state(cx)
            w = s["work"].get(work_id)
            require(w is not None and w["status"] == "pending", "工作不是可派发待办")
            require(all(s["work"][d]["status"] == "delivered" for d in w["dependencies"]), "工作依赖尚未交付")
            a = self._assignment(s, w["position_id"])
            require(a["id"] == w["assignment_id"] and a["member_id"] == w["member_id"], "工作责任已改变")
            c = self._charter(cx, s["charter_version"])
            require("produce_artifact" in c["allowed_tools"] and "produce_artifact" in s["positions"][w["position_id"]]["permissions"], "当前规则未授权本地成果工具")
            w["status"] = "running"
            w.pop("summary", None)
            w["run_id"] = uid("run")
            s["version"] += 1
            bundle = self._context(cx, s, work_id)
            package = {"run_id": w["run_id"], "work_id": work_id, "work_version": w["version"], "member_id": w["member_id"], "position_id": w["position_id"], "assignment_id": w["assignment_id"],
                       "context": bundle["context"], "context_manifest": bundle["manifest"], "tools": ["produce_artifact"]}
            if execution is not None:
                package["execution"] = copy.deepcopy(execution)
            self._reserve(cx, s, "work", executor, package, work_id)
            w["run_id"] = package["run_id"]
            self._save(cx, s)
            return package

    def begin_decision(self, executor, execution=None):
        with self.transaction() as cx:
            s = self._state(cx)
            c = self._charter(cx, s["charter_version"])
            actor, assignment = "bootstrap", None
            if s["phase"] != "bootstrap":
                a = self._assignment(s, s["policy"]["decision_position_id"])
                actor, assignment = a["member_id"], a["id"]
            self._authorize(s, c, actor, assignment)
            require(cx.execute("SELECT 1 FROM runs WHERE status IN ('running','unknown') AND kind='decision'").fetchone() is None, "已有决定执行尚未核对")
            bundle = self._context(cx, s)
            package = {"actor": actor, "assignment_id": assignment, "context": bundle["context"], "context_manifest": bundle["manifest"],
                       "event_ids": [r["id"] for r in bundle["context"]["events"]], "tools": []}
            if execution is not None:
                package["execution"] = copy.deepcopy(execution)
            return self._reserve(cx, s, "decision", executor, package)

    def begin_connection_test(self, execution):
        with self.transaction() as cx:
            s = self._state(cx)
            require("max_cost" not in s["resources"], "API 不支持金额硬上限")
            require(not cx.execute("SELECT 1 FROM runs WHERE status IN ('running','unknown')").fetchone(), "在途或未知执行必须先核对")
            package = self._reserve(cx, s, "connection_test", "api", {"execution": copy.deepcopy(execution)}, allow_paused=True)
            s["version"] += 1
            self._save(cx, s)
            return package

    def finish_connection_test(self, run_id, result, usage):
        with self.transaction() as cx:
            require(self._run(cx, run_id)["kind"] == "connection_test", "执行类型错误")
            self._settle(cx, run_id, "delivered", result, usage)
            s = self._state(cx)
            s["version"] += 1
            self._save(cx, s)

    def _run(self, cx, run_id):
        r = cx.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        require(r is not None, "执行记录不存在")
        return dict(r) | {"package": json.loads(r["package"])}

    def _settle(self, cx, run_id, status, result, usage, state=None):
        r = self._run(cx, run_id)
        require(r["status"] == "running", "执行已结算或需要核对")
        require(isinstance(usage, dict), "用量必须是对象")
        safe = {k: v for k, v in usage.items() if k in ("input_tokens", "output_tokens", "cached_input_tokens") and type(v) is int and v >= 0}
        if r["executor"] == "api":
            for field in ("connection_id", "protocol", "requested_model", "actual_model", "provider_request_id", "response_id", "transport_source"):
                value = usage.get(field)
                if isinstance(value, str) and 0 < len(value) <= 256 and all(32 <= ord(c) < 127 for c in value):
                    safe[field] = value
            for field in ("connection_revision", "elapsed_ms"):
                if type(usage.get(field)) is int and usage[field] >= 0:
                    safe[field] = usage[field]
        safe.update(cost=None, cost_status="unknown")
        current = state if state is not None else self._state(cx)
        if current.get("company"):
            from .company import charge
            charge(current["company"], r | {"status": status}, safe)
            if state is None:
                self._save(cx, current)
        cx.execute("UPDATE runs SET status=?,result=?,usage=?,ended_at=? WHERE id=?", (status, encoded(result), encoded(safe), now(), run_id))

    def finish_decision(self, run_id, result, usage):
        require(isinstance(result, dict), "决定结果必须是对象")
        with self.transaction() as cx:
            r = self._run(cx, run_id)
            require(r["kind"] == "decision", "执行类型错误")
            if r["status"] == "delivered":
                return self._state(cx)
        p = r["package"]
        d = copy.deepcopy(result)
        d["id"] = run_id
        return self.apply_decision(d, p["actor"], p["assignment_id"], p["event_ids"], run_id, usage)

    def finish_progress(self, run_id, usage):
        """One actual model call finished; its SDK task can continue later."""
        with self.transaction() as cx:
            r = self._run(cx, run_id)
            require(r["status"] == "running", "执行已结算或需要核对")
            s, p = self._state(cx), r["package"]
            require(s["charter_version"] == p["context_manifest"]["charter_version"], "生效章程已变化，进度需要核对")
            if r["work_id"]:
                w = s["work"][r["work_id"]]
                require(w["run_id"] == run_id and w["version"] == p["work_version"] and s["assignments"][p["assignment_id"]]["active"], "工作责任已改变")
                w.update(status="pending", summary="工具执行进度已保存，等待下一次调用继续")
            else:
                self._authorize(s, self._charter(cx, s["charter_version"]), p["actor"], p["assignment_id"])
            self._settle(cx, run_id, "continued", {"summary": "Agent 工具进度已保存；尚未交付或提交组织决定"}, usage, s)
            s["version"] += 1
            self._save(cx, s)

    def finish_work(self, run_id, result, usage):
        require(isinstance(result, dict), "执行结果必须是对象")
        with self.transaction() as cx:
            r = self._run(cx, run_id)
            require(r["kind"] == "work", "执行类型错误")
            s = self._state(cx)
            if r["status"] in ("delivered", "blocked", "failed"):
                require(r["result"] == encoded(result), "重复回执内容发生改变")
                return s
            require(r["status"] == "running", "未知执行必须先核对")
            p = r["package"]
            w = s["work"][r["work_id"]]
            a = s["assignments"][p["assignment_id"]]
            require(w["status"] == "running" and w["run_id"] == run_id and w["version"] == p["work_version"] and a["active"], "工作或任职已经改变，结果需要核对")
            c = self._charter(cx, s["charter_version"])
            require("produce_artifact" in c["allowed_tools"] and "produce_artifact" in s["positions"][w["position_id"]]["permissions"], "交付前生效权限检查失败")
            status = result.get("status")
            require(set(result) <= {"status", "summary", "artifacts"}, "结果含不支持的字段")
            require(status in ("delivered", "blocked", "failed"), "不支持的工作结果状态")
            arts = result.get("artifacts", [])
            require(isinstance(arts, list) and len(arts) <= 20, "成果必须是有界列表")
            require(status != "delivered" or bool(arts), "完成声明缺少实际成果")
            require(status == "delivered" or not arts, "受阻或失败结果不能同时声明交付")
            summary = result.get("summary", "")
            require(isinstance(summary, str) and len(summary) <= 100000, "结果摘要必须是有界文本")
            require(status == "delivered" or bool(text(summary, "阻塞或失败原因")), "缺少原因")
            for index, art in enumerate(arts):
                require(isinstance(art, dict) and set(art) == {"name", "content"}, "只支持名称与内容组成的文本成果")
                name = text(art["name"], "成果名称", 200)
                require(Path(name).name == name and name not in (".", "..") and "\\" not in name, "成果名称不能包含路径")
                data = text(art["content"], "成果内容", 200000).encode("utf-8")
                sha = hashlib.sha256(data).hexdigest()
                target = self.root / "assets" / (sha + ".txt")
                if not target.exists():
                    with target.open("xb") as f:
                        f.write(data)
                require(hashlib.sha256(target.read_bytes()).hexdigest() == sha, "已有资产校验失败")
                aid = run_id + "-artifact-" + str(index)
                # A work may be revised and rerun; historical versions remain in the organization.
                previous = [a for a in s["artifacts"].values() if a["work_id"] == w["id"] and a["name"] == name]
                s["artifacts"][aid] = {"id": aid, "version": len(previous) + 1, "name": name, "path": str(target.relative_to(self.root)), "sha256": sha,
                                       "work_id": w["id"], "work_version": w["version"], "run_id": run_id, "member_id": w["member_id"],
                                       "charter_version": p["context_manifest"]["charter_version"], "commit_charter_version": s["charter_version"], "created_at": now()}
                w["artifact_ids"].append(aid)
            w.update(status=status, summary=summary)
            s["version"] += 1
            self._settle(cx, run_id, status, result, usage, s)
            self._event(cx, "work_" + status, {"work_id": w["id"], "run_id": run_id, "artifact_ids": w["artifact_ids"], "summary": summary})
            self._save(cx, s)
            return s

    def fail_run(self, run_id, reason, unknown=False, usage=None, failure=None):
        with self.transaction() as cx:
            r = self._run(cx, run_id)
            if r["status"] != "running":
                return
            s = self._state(cx)
            from .failures import public_failure
            failure = public_failure(failure)
            result = {"reason": reason} | ({"failure": failure} if failure else {})
            self._settle(cx, run_id, "unknown" if unknown else "failed", result, usage or {}, s)
            if r["work_id"]:
                w = s["work"][r["work_id"]]
                if w["run_id"] == run_id:
                    w["status"] = "needs_review" if unknown else "failed"
                    w["summary"] = "执行结果未知，需要核对" if unknown else "执行失败；请在宿主核对私有执行记录"
            s["version"] += 1
            self._event(cx, "execution_unknown" if unknown else "execution_failed", {"run_id": run_id, "reason": reason})
            self._save(cx, s)

    def recover(self):
        # Only call on exclusive process startup, never concurrently with a live dispatcher.
        active = [r for r in self.runs() if r["status"] == "running"]
        for r in active:
            self.fail_run(r["id"], "进程中断；外部执行结果未知，请核对执行器记录", unknown=True)
        return len(active)

    def reconcile(self, board_key, run_id, resolution, reason):
        require(resolution in ("confirmed_not_executed", "abandon"), "只支持确认未执行或放弃；已有回执请人工核对后导入新事件")
        text(reason, "核对证据")
        with self.transaction() as cx:
            board = self._board(cx, board_key)
            r = self._run(cx, run_id)
            require(r["status"] == "unknown", "运行不在未知状态")
            cx.execute("UPDATE runs SET status='reconciled',ended_at=? WHERE id=?", (now(), run_id))
            s = self._state(cx)
            if r["work_id"]:
                w = s["work"][r["work_id"]]
                w["status"] = "pending" if resolution == "confirmed_not_executed" else "cancelled"
                w["version"] += 1
            s["version"] += 1
            self._event(cx, "execution_reconciled", {"run_id": run_id, "resolution": resolution, "evidence": reason, "board": board})
            self._save(cx, s)

    def wake_due(self, at=None):
        time = instant(at or now())
        fired = 0
        with self.transaction() as cx:
            s = self._state(cx)
            for wake in s["wakeups"]:
                if not wake["fired"] and instant(wake["until"]) <= time:
                    wake["fired"] = True
                    fired += 1
                    self._event(cx, "review_due", wake, wake["id"])
            if fired:
                s["version"] += 1
                self._save(cx, s)
        return fired

    def ready_work(self):
        s = self.state()
        return [w["id"] for w in s["work"].values() if w["status"] == "pending" and all(s["work"][d]["status"] == "delivered" for d in w["dependencies"])]

    def runs(self):
        with self.transaction() as cx:
            return [dict(r) | {"package": json.loads(r["package"]), "result": json.loads(r["result"]) if r["result"] else None, "usage": json.loads(r["usage"]) if r["usage"] else None} for r in cx.execute("SELECT * FROM runs ORDER BY rowid")]

    def usage(self):
        return [{"run_id": r["id"], "executor": r["executor"], "status": r["status"], "usage": r["usage"]} for r in self.runs()]

    def decisions(self):
        with self.transaction() as cx:
            return [dict(r) | {"data": json.loads(r["data"])} for r in cx.execute("SELECT * FROM decisions ORDER BY rowid")]

    def status(self):
        from .observation import snapshot
        return snapshot(self)
