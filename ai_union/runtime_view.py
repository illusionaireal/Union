"""Read-only runtime and member-execution projections.

This module deliberately derives status from persisted work/runs and the current
host activity evidence.  It never creates a runtime registration, starts a
dispatcher, or reads checkpoint bodies.
"""
import json
import stat


def _table(cx, name):
    return bool(cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def _workspace(cx, state, member_id, current):
    """Summarize configured permission for the representative work's assignment.

    This is not workspace.available(package): dispatch, package/version, pause,
    and execution checks remain in the actual command authorization path.
    """
    if not _table(cx, "workspace_grant"):
        return {"mode": "virtual_only", "revision": None, "available": False, "reason_codes": ["workspace_unconfigured"]}
    row = cx.execute("SELECT revision,config FROM workspace_grant WHERE id=1").fetchone()
    if not row:
        return {"mode": "virtual_only", "revision": None, "available": False, "reason_codes": ["workspace_unconfigured"]}
    config = json.loads(row["config"])
    summary = {"mode": "shared_business", "revision": row["revision"], "available": False, "reason_codes": []}
    if not config.get("enabled"):
        return summary | {"reason_codes": ["workspace_disabled"]}
    if not any(a["active"] and a["member_id"] == member_id for a in state["assignments"].values()):
        return summary | {"reason_codes": ["no_active_assignment"]}
    if not current:
        return summary | {"reason_codes": ["no_current_work"]}
    assignment = state["assignments"].get(current["assignment_id"])
    if not (assignment and assignment["active"] and assignment["member_id"] == member_id
            and current["member_id"] == member_id and assignment["position_id"] == current["position_id"]):
        return summary | {"reason_codes": ["workspace_not_authorized"]}
    position = state["positions"].get(current["position_id"])
    charter_row = cx.execute("SELECT data FROM charters WHERE version=?", (state["charter_version"],)).fetchone()
    charter_tools = set(json.loads(charter_row["data"])["allowed_tools"]) if charter_row else set()
    allowed = bool(position and "workspace_execute" in position.get("permissions", []) and "workspace_execute" in charter_tools)
    return summary | {"available": allowed, "reason_codes": [] if allowed else ["workspace_not_authorized"]}


def _checkpoint(root, session_id):
    """Only probe fixed-path metadata; a present store cannot prove a session row.

    Keep session_id for caller compatibility. No SQLite/header/content open is
    safe against external journal-mode changes or replacement without a writer
    protocol, so presence stays unknown and never authorizes actual recovery.
    """
    folder = root / "harness"
    path = folder / "checkpoints.sqlite3"
    try:
        if not stat.S_ISDIR(folder.lstat().st_mode):
            return None
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return None
    return None  # Existence/type/errors never become proof of checkpoint rows.


def _session(cx, run, root):
    if not run or not _table(cx, "agent_sessions"):
        return {"id": None, "updated_at": None, "has_checkpoint": False, "resume_state": "not_available"}
    row = cx.execute("SELECT id,status,updated_at,last_run_id FROM agent_sessions WHERE last_run_id=? ORDER BY rowid DESC LIMIT 1", (run["id"],)).fetchone()
    if not row:
        return {"id": None, "updated_at": None, "has_checkpoint": False, "resume_state": "not_available"}
    status = row["status"]
    exists = _checkpoint(root, row["id"])
    if run["status"] in ("unknown", "reconciled") or status == "unknown":
        resume = "requires_reconciliation"
    elif run["status"] == "running" or status == "completed":
        resume = "not_available"
    elif status in ("paused", "running", "failed"):
        resume = "unknown" if exists is None else "requires_validation" if exists else "not_available"
    else:
        resume = "unknown"
    return {"id": row["id"], "updated_at": row["updated_at"], "has_checkpoint": exists, "resume_state": resume}


def _member_work(work, member_runs, state, runs_by_id, unknown, active_runs, budget, paused):
    """Choose a representative work item, not a new dispatch or recovery action.

    Keep the persisted state order within each tier. Unresolved execution takes
    precedence over apparent readiness; settled failures do not hide other work.
    """
    review = next((w for w in work if w["status"] == "needs_review"), None)
    member_unknown = next((r for r in member_runs if r["status"] == "unknown"), None)
    if review or member_unknown:
        current = review or next((w for w in work if w["id"] == member_unknown.get("work_id")
                                  and w["status"] not in ("delivered", "cancelled")), None)
        return current, "blocked", ["run_requires_reconciliation" if member_unknown else "work_needs_review"]
    current = next((w for w in work if w["status"] == "running"), None)
    if current:
        matching = runs_by_id.get(current.get("run_id"))
        if matching and matching["status"] == "running" and matching.get("host_confirmed"):
            return current, "executing", []
        return current, "blocked", ["run_failed" if matching and matching["status"] == "failed" else "activity_unconfirmed"]
    current = next((w for w in work if w["status"] == "pending"
                    and all(state["work"][dep]["status"] == "delivered" for dep in w["dependencies"])), None)
    if current:
        # These AU-wide gates mirror the existing serial dispatch constraints,
        # but do not relabel dependency waits or members without unfinished work.
        if unknown:
            return current, "blocked", ["run_requires_reconciliation"]
        if any(not r.get("host_confirmed") for r in active_runs):
            return current, "blocked", ["activity_unconfirmed"]
        if active_runs:
            return current, "waiting", ["dispatch_busy"]
        if budget["blocked_reason"]:
            return current, "blocked", ["budget_limited"]
        if paused:
            return current, "waiting", ["dispatch_paused"]
        return current, "ready", []
    current = next((w for w in work if w["status"] in ("blocked", "failed")), None)
    if current:
        return current, "blocked", ["work_" + current["status"]]
    current = next((w for w in work if w["status"] == "pending"), None)
    if current:
        return current, "waiting", ["dependency_pending"]
    current = next((w for w in work if w["status"] == "paused"), None)
    if current:
        return current, "waiting", ["work_paused"]
    return None, "idle", []


def view(cx, state, runs, live, budget, paused, root, dispatch):
    """Return public runtime/member summaries from an existing read transaction."""
    active_runs = [r for r in runs if r["status"] == "running"]
    unknown = [r for r in runs if r["status"] == "unknown"]
    runs_by_id = {r["id"]: r for r in runs}
    active = next((r for r in active_runs if r.get("host_confirmed")), None)
    runtime = {
        "runtime_id": None,
        # Host activity confirms execution, not a registered deployment mode.
        "name": "部署位置未登记",
        "mode": "unregistered",
        "instance_id": None,
        "observed_at": None,
        "liveness": "confirmed" if live["confirmed"] else "unknown",
        "dispatch_state": dispatch,
        "active_run_id": active["id"] if active else None,
        "capabilities": [],  # No registered instance capability declaration.
    }
    by_member = {}
    for r in runs:
        if r.get("member_id"):
            by_member.setdefault(r["member_id"], []).append(r)
    rows = []
    for member in state["members"].values():
        assignments = [a for a in state["assignments"].values() if a["active"] and a["member_id"] == member["id"]]
        work = [w for w in state["work"].values() if w["member_id"] == member["id"]]
        # snapshot supplies persisted insertion order, oldest first; timestamps/IDs
        # are not ordering keys.
        member_runs = by_member.get(member["id"], [])
        latest = member_runs[-1] if member_runs else None
        current, work_state, reason_codes = _member_work(work, member_runs, state, runs_by_id, unknown, active_runs, budget, paused)
        session_run = runs_by_id.get(current.get("run_id")) if current else latest
        # Handoff moves responsibility, not ownership of the old run/session.
        session_run = session_run if session_run and session_run.get("member_id") == member["id"] else None
        rows.append({"member_id": member["id"], "assignment_ids": [a["id"] for a in assignments],
                     "current_work_id": current["id"] if current else None,
                     "work_state": work_state, "reason_codes": reason_codes,
                     "recent_run": ({k: latest.get(k) for k in ("id", "status", "display_status", "started_at", "ended_at", "work_id")} if latest else None),
                     "session": _session(cx, session_run, root),
                     "workspace": _workspace(cx, state, member["id"], current)})
    return {"runtime": runtime, "member_execution": rows}
