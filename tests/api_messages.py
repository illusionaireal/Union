"""Translate historical scripted fixtures into API messages for regression tests only."""
import json


def tool_message(name, arguments):
    return {"role": "assistant", "content": "明确标识的本地 HTTP 模拟。", "tool_calls": [
        {"id": "local-call", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}]}


def aliases(package, bootstrap):
    if not bootstrap:
        return {}
    ctx = package["context"]
    result = {}
    collections = {"create_member": ("members", "member", "name"), "create_position": ("positions", "position", "title"),
                   "create_work": ("work", "task", "title")}
    for op in bootstrap["operations"]:
        if op["op"] not in collections:
            continue
        plural, singular, label = collections[op["op"]]
        current = list(ctx.get(plural, {}).values()) + ([ctx[singular]] if singular in ctx else [])
        for entity in current:
            if entity[label] == op[label]:
                result[op["id"]] = entity["id"]
    return result


def replace(value, mapping):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [replace(item, mapping) for item in value]
    if isinstance(value, dict):
        return {mapping.get(key, key): replace(item, mapping) for key, item in value.items()}
    return value


def historical_package(package, bootstrap=None):
    result = replace(package, {new: old for old, new in aliases(package, bootstrap).items()})
    result["context_manifest"] = {"state_version": 0, "charter_version": 1, "policy_version": 0}
    result["run_id"] = "explicit-local-double"
    return result


def fixture_message(package, value, bootstrap=None):
    if package["kind"] == "connection_test":
        return {"role": "assistant", "content": "本地 HTTP 替身连接正常。"}
    if package["kind"] == "work":
        if value["status"] != "delivered":
            return tool_message("report_blocked", {"reason": value["summary"]})
        return {"role": "assistant", "content": "\n\n".join(a["content"] for a in value["artifacts"])}
    if package["actor"] == "bootstrap":
        ops = value["operations"]
        members = {o["id"]: o for o in ops if o["op"] == "create_member"}
        positions = {o["id"]: o for o in ops if o["op"] == "create_position"}
        assignments = {o["position_id"]: o["member_id"] for o in ops if o["op"] == "assign"}
        works = {o["id"]: o for o in ops if o["op"] == "create_work"}
        policy = next((o["decision_position_id"] for o in ops if o["op"] == "set_policy"), None)
        plan = {"strategy": value["rationale"], "coordinator": members[assignments[policy]]["name"] if policy else "missing",
                "members": [{"name": members[m]["name"], "role": positions[p]["title"], "mandate": positions[p]["mandate"]} for p, m in assignments.items()],
                "tasks": [{"title": w["title"], "instruction": w["instruction"], "owner": members[assignments[w["position_id"]]]["name"],
                           "dependencies": [works[d]["title"] for d in w["dependencies"]]} for w in works.values()]}
        return tool_message("initialize_organization", plan)
    value = replace(value, aliases(package, bootstrap))
    if value.get("evidence_refs") == ["$latest_work"]:
        value["evidence_refs"] = [key for key, work in package["context"]["work"].items() if work["status"] == "delivered"]
    return tool_message("update_organization", {"summary": value["rationale"], "evidence_refs": value.get("evidence_refs", []), "operations": value["operations"]})
