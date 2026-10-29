"""Audit the current AU capability surface with fresh fixtures; no model, Docker or private org reads.

Checks assert current observed mechanisms (including remaining gaps), not real organizational outcomes.
Run again before changing the contract; this script is deliberately not a permanent CI gate.
"""
import argparse
import copy
import json
import tempfile
from pathlib import Path

from ai_union.agent_protocol import compile_tool, model_input, tools_for
from ai_union.engine import Engine, Rejected
from ai_union.runner import step
from ai_union.workspace import available
from tests.support import CHARTER, RESOURCES, decision, organization


def audit():
    checks = []

    def check(id, result, detail, *, finding="available"):
        assert result, f"{id}: observed behavior differs from audit baseline"
        checks.append({"id": id, "finding": finding, "verified": True, "detail": detail})

    def rejected(call):
        try:
            call()
        except Rejected:
            return True
        return False

    with tempfile.TemporaryDirectory(prefix="au-capability-audit-") as folder:
        root = Path(folder)
        e = Engine.create(root / "au", "Audit AU", "Produce useful work", CHARTER,
                          RESOURCES | {"max_calls": 40}, "Company sponsor", "audit-fixture-key")
        organization(e)
        # A first formal artifact, followed by an actionable blocked dependency.
        first = e.begin_work("w1", "fixture")
        e.finish_work(first["run_id"], {"status": "delivered", "summary": "Fixture delivery",
                      "artifacts": [{"name": "source.md", "content": "Source content for dependency"}]}, {})
        second = e.begin_work("w2", "fixture")
        work = model_input(second)["context"]
        names = {t["function"]["name"] for t in tools_for(second)}
        check("O01", all(k in work for k in ("organization", "charter", "resources", "budget", "memory", "task", "member", "position", "assignment")), "Work sees goal/charter/budget, own responsibility and org memory.")
        check("O02", any(a["content"] == "Source content for dependency" for a in work["artifacts"]) and all("path" not in a for a in work["artifacts"]), "Dependency artifacts are inline; host file paths removed.")
        check("O03", not any(k in work for k in ("work", "members", "positions", "assignments", "events")), "Ordinary work does not get org-wide roster/work/events or dependency task metadata.", finding="gap")
        check("O04", names == {"report_blocked"}, "Normal work exposes report_blocked, not organization decision tools.", finding="boundary")
        check("O05", not available(e, second), "Workspace unavailable without host binding; charter text does not grant host access.", finding="boundary")
        blocked = compile_tool(second, "report_blocked", {"reason": "Need sponsor input"})
        e.finish_work(second["run_id"], blocked, {})
        decision_package = e.begin_decision("fixture")
        ctx = model_input(decision_package)["context"]
        tools = {t["function"]["name"] for t in tools_for(decision_package)}
        check("O06", all(k in ctx for k in ("members", "positions", "assignments", "work", "events")) and ctx["work"]["w2"]["summary"] == "Need sponsor input", "Decision context sees full local work graph, roster and pending blocked event.")
        check("O07", "Source content for dependency" in [a["content"] for a in ctx["artifacts"]], "Decision role sees all local formal artifacts, not a fine-grained data access policy.", finding="boundary")
        check("O08", "diagnostics" in ctx and "recent_runs" in ctx["diagnostics"] and ctx["diagnostics"]["limit"] == 12 and "cost_status" in ctx["budget"], "Decision context includes bounded host-owned runtime history and unknown-cost summary; raw packages are excluded.")
        check("A01", {"update_organization", "schedule_work", "wait_for_event"} <= tools, "Decision role can change local organization, schedule work and wait.")
        check("A02", not ({"request_resources", "request_tool", "inspect_organization", "observe_organization"} & tools), "No extra query tool; diagnostics are inline. Legacy charter does not automatically grant the opt-in request workflow.", finding="boundary")
        # Exercise real decision validation and commit, not merely schema inspection.
        proposal = compile_tool(decision_package, "update_organization", {
            "summary": "Record a test improvement hypothesis and move work responsibility",
            "evidence_refs": ["w2"], "operations": [
                {"op": "record_memory", "content": "Ask for necessary input before retry", "conditions": "Missing input", "uncertainty": "Effect unverified"},
                {"op": "update_position", "position_id": "p2", "title": "Delivery", "mandate": "Use evidence and report blocked", "permissions": ["produce_artifact"]},
                {"op": "handoff", "position_id": "p2", "member_id": "m1", "assignment_id": "a3"},
                {"op": "resume_work", "work_id": "w2"}]})
        e.finish_decision(decision_package["run_id"], proposal, {})
        state = e.state()
        check("A03", len(state["memory"]) == 1 and state["work"]["w2"]["status"] == "pending" and state["work"]["w2"]["member_id"] == "m1" and not state["assignments"]["a2"]["active"], "Memory, mandate update, local handoff and blocked work resume commit together.")
        follow = e.begin_decision("fixture")
        check("A04", rejected(lambda: compile_tool(follow, "schedule_work", {"owner": "m1", "title": "Follow-up", "instruction": "Improve workflow"})), "One member may have multiple positions; schedule_work shorthand then rejects ambiguous assignment.", finding="gap")
        e.finish_decision(follow["run_id"], compile_tool(follow, "update_organization", {"operations": [
            {"op": "create_work", "id": "w3", "title": "Explicit-position follow-up", "instruction": "Improve workflow", "position_id": "p1", "dependencies": ["w1"]}]}), {})
        check("A05", "w3" in e.state()["work"], "Explicit create_work by position remains valid for multi-position member.")
        unauth = e.begin_decision("fixture")
        check("A06", rejected(lambda: compile_tool(unauth, "request_resources", {"max_calls": 99})), "Missing grant/request tool cannot be invoked.", finding="boundary")
        operations = copy.deepcopy(unauth)
        operation_schemas = next(t for t in tools_for(operations) if t["function"]["name"] == "update_organization")["function"]["parameters"]["properties"]["operations"]["items"]["anyOf"]
        permitted = {s["properties"]["op"]["enum"][0] for s in operation_schemas}
        check("A07", not ({"retire_member", "unassign", "create_au", "delegate_work", "change_goal", "amend_charter", "configure_resources"} & permitted), "Member exit, cross-AU evolution and governance/resource changes are not decision operations.", finding="boundary")
        e.fail_run(unauth["run_id"], "Fixture interruption", unknown=True)

        class NeverCalled:
            name = "fixture"
            def execute(self, _package):
                raise AssertionError("Unknown execution must block before dispatch")
        action = step(e, NeverCalled())
        check("R01", action["action"] == "blocked", "Unknown execution stops dispatcher before any new decision/model call.", finding="boundary")
        e.reconcile("audit-fixture-key", unauth["run_id"], "confirmed_not_executed", "Fixture evidence only")
        failed = e.begin_work("w2", "fixture")
        e.fail_run(failed["run_id"], "Synthetic diagnostic for audit", failure={})
        diagnostic = model_input(e.begin_decision("fixture"))["context"]
        check("O09", "execution_failed" in {ev["kind"] for ev in diagnostic["events"]} and diagnostic["work"]["w2"]["status"] == "failed", "Pending failure event/work summary visible, but this is not a persistent filtered history query.")
        check("O10", diagnostic["work"]["w2"]["lifecycle"]["first_started_at"] is not None and diagnostic["work"]["w2"]["lifecycle"]["status_since"] is not None, "New work has host-observed lifecycle timestamps; legacy unknown history remains separately classified.")
        # Same local member id in another AU denotes a different scoped identity.
        other = Engine.create(root / "other", "Other AU", "Other work", CHARTER, RESOURCES, "Other sponsor", "other-fixture-key")
        organization(other)
        check("I01", e.state()["id"] != other.state()["id"] and "m1" in e.state()["members"] and "m1" in other.state()["members"], "Identity is effectively scoped by AU; local ID equality is not a shared global Agent.", finding="boundary")
        before = e.state()
        check("I02", rejected(lambda: e.apply_decision(decision(e, [{"op": "assign", "id": "bad-assignment", "position_id": "p2", "member_id": "foreign-member"}]), "m1", "a1")) and e.state() == before, "Unregistered member cannot acquire a local assignment; no cross-AU identity transfer protocol.", finding="boundary")
    return {"baseline": "c9b910b", "scope": "fresh fixture engine/tool projection; no actual model or Docker", "checks": checks,
            "total": len(checks), "passed": len(checks), "model_calls": 0, "docker_commands": 0,
            "note": "Fixture run records were created; these are not actual provider requests or autonomous improvement evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # New evidence only: do not overwrite an earlier run.
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"checks": result["total"], "passed": result["passed"], "model_calls": 0}))


if __name__ == "__main__":
    main()
