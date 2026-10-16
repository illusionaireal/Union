"""Objective checks over actual records; scripted fixtures cannot pass a real eval."""
import json

from .engine import Rejected, now


def simulated_run(run):
    return run["executor"] not in ("codex", "api") or (run["executor"] == "api" and run["package"].get("execution", {}).get("transport_source") != "provider_api")


def execution_receipt(engine, run):
    folder = engine.root / "executions" / run["id"]
    if not (run["status"] == "delivered" and run["usage"] is not None and (folder / "result.json").is_file()):
        return False
    if run["executor"] == "codex":
        return True
    try:
        receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
        expected = run["package"]["execution"]
        return receipt.get("transport_source") == "provider_api" and all(receipt.get(k) == expected[k] for k in
            ("connection_id", "connection_revision", "protocol", "requested_model")) and bool(receipt.get("response_id") or receipt.get("provider_request_id"))
    except (ValueError, OSError, KeyError):
        return False


def evaluate(engine):
    s = engine.state()
    # A paid connection test is accounting evidence, never organizational capability evidence.
    runs = [r for r in engine.runs() if r["kind"] != "connection_test"]
    work_runs = [r for r in runs if r["kind"] == "work" and r["status"] == "delivered"]
    real_runs = [r for r in runs if not simulated_run(r)]
    checks = {}
    errors = []
    checks["organization_formed"] = s["phase"] == "active" and len(s["members"]) >= 2
    checks["distinct_members_executed"] = len({r["package"]["member_id"] for r in work_runs}) >= 2
    checks["artifacts_verified"] = bool(s["artifacts"])
    for a in s["artifacts"].values():
        try:
            engine._read_artifact(a)
        except (Rejected, OSError, UnicodeError) as e:
            checks["artifacts_verified"] = False
            errors.append(str(e))
    cross = []
    for r in work_runs:
        w = r["package"]["context"]["task"]
        provided = {a["id"] for a in r["package"]["context"]["artifacts"]}
        for dep in w["dependencies"]:
            source = s["work"][dep]
            if source["member_id"] != r["package"]["member_id"] and provided.intersection(source["artifact_ids"]):
                cross.append({"source_work": dep, "dependent_work": w["id"], "run_id": r["id"]})
    checks["cross_member_artifact_dependency"] = bool(cross)
    facts = {r["work_id"] for r in work_runs} | set(s["artifacts"])
    facts |= {e["id"] for e in engine.events() if e["kind"] in ("work_delivered", "novel_feedback")}
    followups = []
    for d in engine.decisions():
        if d["status"] != "accepted" or d["actor"] == "bootstrap":
            continue
        proposal = d["data"]
        if not facts.intersection(proposal["evidence_refs"]):
            continue
        new_work = {o["id"] for o in proposal["operations"] if o["op"] == "create_work"}
        for r in work_runs:
            if r["work_id"] in new_work and r["started_at"] > d["created_at"]:
                followups.append({"decision_id": d["id"], "work_id": r["work_id"], "run_id": r["id"], "evidence_refs": proposal["evidence_refs"]})
    checks["evidence_to_followup_action"] = bool(followups)
    simulated = any(simulated_run(r) for r in runs)
    checks["real_executor_only"] = bool(real_runs) and not simulated
    checks["real_executor_receipts"] = bool(real_runs) and all(execution_receipt(engine, r) for r in real_runs)
    mechanism = all(v for k, v in checks.items() if k not in ("real_executor_only", "real_executor_receipts"))
    return {"evaluated_at": now(), "status": "passed" if all(checks.values()) else ("simulated" if simulated and mechanism else "incomplete"),
            "real_agent_verified": all(checks.values()), "mechanism_scenario_passed": mechanism,
            "checks": checks, "cross_member_dependencies": cross, "followup_actions": followups,
            "usage": engine.usage(), "errors": errors,
            "external_delivery_verified": False, "external_market_feedback_verified": False,
            "scope": "E1/E2 首轮闭环；E3/E4 由独立机制测试验证，未声称模型能力或首版经营验收通过"}
