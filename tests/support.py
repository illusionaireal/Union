from ai_union.engine import Engine

CHARTER = {
    "text": "测试章程：有限的本地组织协作；无对外发布授权。",
    "allowed_operations": ["create_member", "create_position", "update_position", "assign", "set_policy",
                           "create_work", "handoff", "pause_work", "resume_work",
                           "cancel_work", "update_work", "wait", "set_strategy", "record_memory"],
    "allowed_tools": ["produce_artifact"],
    "reserved_matters": ["goal", "resources", "charter", "funding", "dissolution"],
    "board_can_amend": True,
}
RESOURCES = {"max_calls": 12, "timeout_seconds": 30}


def decision(e, ops, **changes):
    s = e.state()
    d = {"id": "d-" + str(s["version"]), "base_state_version": s["version"],
         "charter_version": s["charter_version"], "policy_version": s["policy_version"],
         "issue": "测试问题", "rationale": "测试依据", "expected_effect": "测试效果",
         "evidence_refs": [], "operations": ops}
    d.update(changes)
    return d


def organization(e):
    ops = [
        {"op": "create_member", "id": "m1", "name": "Member One"},
        {"op": "create_member", "id": "m2", "name": "Member Two"},
        {"op": "create_position", "id": "p1", "title": "Test responsibility 1",
         "mandate": "Coordinate test work", "permissions": CHARTER["allowed_operations"] + ["produce_artifact"]},
        {"op": "create_position", "id": "p2", "title": "Test responsibility 2",
         "mandate": "Perform test work", "permissions": ["produce_artifact"]},
        {"op": "assign", "id": "a1", "position_id": "p1", "member_id": "m1"},
        {"op": "assign", "id": "a2", "position_id": "p2", "member_id": "m2"},
        {"op": "set_policy", "decision_position_id": "p1"},
        {"op": "create_work", "id": "w1", "title": "First work", "instruction": "Produce a test artifact",
         "position_id": "p1", "dependencies": []},
        {"op": "create_work", "id": "w2", "title": "Dependent work", "instruction": "Use the first artifact",
         "position_id": "p2", "dependencies": ["w1"]},
    ]
    e.apply_decision(decision(e, ops), "bootstrap")


def init(root, **resources):
    return Engine.create(root, "test-org", "一个持续经营线上内容品牌的 AI 内容工作室。",
                         CHARTER, RESOURCES | resources, "test-board", "test-key")
