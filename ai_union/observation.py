"""Single read-only snapshots. This module never dispatches or recovers executions."""
import json

from .activity import host_activity
from .engine import instant, now, require


def pick(obj, keys):
    return {k: obj[k] for k in keys.split() if k in obj}


def snapshot(engine, offset=0, limit=50):
    require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 100, "无效分页")
    with engine.read_transaction() as cx:
        state = engine._state(cx)
        budget = engine._budget(cx, state)
        live = host_activity(engine)
        runs = []
        host_failures = set()
        for row in cx.execute("SELECT id,kind,work_id,executor,status,started_at,ended_at,usage,package,json_type(result,'$.reason') AS host_failure FROM runs ORDER BY rowid"):
            r = dict(row)
            if r.pop("host_failure"):
                host_failures.add(r["id"])
            package = json.loads(r.pop("package"))
            r["member_id"] = package.get("member_id", package.get("actor"))
            r["usage"] = json.loads(r["usage"]) if r["usage"] else None
            r["simulated"] = r["executor"] == "fixture"
            r["host_confirmed"] = live["confirmed"] and package.get("host_owner") == live["owner"]
            r["display_status"] = ("running" if r["host_confirmed"] else "unconfirmed") if r["status"] == "running" else r["status"]
            runs.append(r)
        pending = cx.execute("SELECT COUNT(*) FROM events WHERE consumed=0").fetchone()[0]
        event_count = cx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        decision_count = cx.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        events = []
        for row in cx.execute("SELECT * FROM events ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset)):
            e = dict(row)
            data = json.loads(e["data"])
            if e["kind"] in ("execution_failed", "execution_unknown"):
                data = pick(data, "run_id") | {"reason": "执行失败；请在宿主核对私有执行记录" if e["kind"] == "execution_failed" else "执行结果未知，需要核对"}
            e["data"] = data
            events.append(e)
        decisions = []
        for row in cx.execute("SELECT * FROM decisions ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset)):
            d = dict(row)
            d["data"] = pick(json.loads(d["data"]), "id issue rationale expected_effect evidence_refs operations base_state_version charter_version policy_version")
            decisions.append(d)
        paused = engine.paused(cx)
        receipts = []
        if cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='commands'").fetchone():
            receipts = [json.loads(r[0]) for r in cx.execute("SELECT receipt FROM commands ORDER BY rowid DESC LIMIT 30")]
        charter = engine._charter(cx, state["charter_version"])
        organization = pick(state, "id name goal version charter_version policy_version phase members positions assignments policy work strategy wakeups resources")
        organization["artifacts"] = {k: pick(a, "id name version sha256 work_id work_version run_id member_id charter_version commit_charter_version created_at") for k, a in state["artifacts"].items()}
        run_by_id = {r["id"]: r for r in runs}
        for work in organization["work"].values():
            r = run_by_id.get(work.get("run_id"))
            if r and (r["status"] in ("unknown", "failed") or r["id"] in host_failures):
                work["summary"] = "执行结果未知，需要核对" if r["status"] == "unknown" else "执行失败；请在宿主核对私有执行记录"
            work["display_status"] = r["display_status"] if work["status"] == "running" and r else work["status"]
            if work["status"] == "pending" and any(state["work"][d]["status"] != "delivered" for d in work["dependencies"]):
                work["display_status"] = "dependent"
        ready = [w["id"] for w in state["work"].values() if w["status"] == "pending" and all(state["work"][d]["status"] == "delivered" for d in w["dependencies"])]
        unknown = [r for r in runs if r["status"] == "unknown"]
        running = [r for r in runs if r["status"] == "running"]
        execution = "unknown" if unknown else ("running" if all(r["host_confirmed"] for r in running) else "unconfirmed") if running else "idle"
        dispatch = ("needs_review" if unknown else "pause_requested" if running or live["confirmed"] else "paused") if paused else "enabled"
        blocked = [w["id"] + ": " + w.get("summary", w["display_status"]) for w in organization["work"].values() if w["display_status"] in ("blocked", "failed", "needs_review", "paused", "dependent")]
        if budget["blocked_reason"]:
            blocked.append(budget["blocked_reason"])
        if unknown:
            blocked.append("需要核对执行：" + ", ".join(r["id"] for r in unknown))
        if execution == "unconfirmed":
            blocked.append("执行活性未确认；读取不会触发恢复或重派")
        next_step = "bootstrap" if state["phase"] == "bootstrap" else "execute_work" if ready else "decide" if pending else "wait"
        if budget["blocked_reason"] or unknown:
            next_step = "blocked"
        elif running:
            next_step = execution
        elif paused:
            next_step = "paused"
        wakes = [w["until"] for w in state["wakeups"] if not w["fired"]]
        return {"organization": organization, "charter": charter, "budget": budget, "ready_work": ready,
                "execution_config": {"codex_model": state.get("execution_config", {}).get("codex_model")},
                "pending_events": pending, "next_step": next_step, "blocked_reasons": blocked,
                "next_review_at": min(wakes, key=instant) if wakes else None, "collected_at": now(),
                "execution_state": execution, "dispatch_state": dispatch, "host_activity": live,
                "runs": runs, "events": events, "decisions": decisions, "receipts": receipts,
                "pagination": {"offset": offset, "limit": limit, "event_count": event_count, "decision_count": decision_count},
                "source": "mixed" if any(r["simulated"] for r in runs) and any(not r["simulated"] for r in runs) else "fixture" if runs and all(r["simulated"] for r in runs) else "real" if runs else "not_run"}


def artifact(engine, artifact_id):
    with engine.read_transaction() as cx:
        state = engine._state(cx)
        a = state["artifacts"].get(artifact_id)
        require(a is not None, "成果不存在")
        return pick(a, "id name version sha256 work_id run_id member_id") | {"content": engine._read_artifact(a), "verified": True}
