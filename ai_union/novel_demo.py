"""Explicit scripted fixture for UI/regression demos. Never an AI-capability claim."""
from pathlib import Path

from .engine import OPERATIONS

CONFIG = {"initial_budget_minor": 10000, "input_price_minor_per_million": 100, "output_price_minor_per_million": 500}


class NovelDemoExecutor:
    name = "fixture"

    def execute(self, package):
        ctx = package["context"]
        company = ctx["company"]
        if package["kind"] == "work":
            task = ctx["task"]
            n = int(task["id"].split('-')[-1]) if task["id"].startswith('chapter-') else 0
            content = (Path(__file__).resolve().parents[1] / f"examples/novel-demo/chapter-{n}.txt").read_text(encoding="utf-8") if n else (
                "明确标识的脚本演示设定：城钟停转三十年，修表师林渡追索父亲的时间债。"
                "阿禾带来明天的报纸。三章依次抵达修表铺、北站和登记走廊。第二章故意放慢节奏，第三章在受控反馈后把威胁前置。")
            return {"status": "delivered", "summary": "脚本演示成果；非真实模型生成", "artifacts": [{"name": f"chapter-{n}.txt" if n else "story-bible.txt", "content": content}]}, {"input_tokens": 1200, "output_tokens": 1000}
        ops, refs = [], []
        if package["actor"] == "bootstrap":
            ops = [
                {"op": "create_member", "id": "planner", "name": "演示成员 · 林策"},
                {"op": "create_member", "id": "writer", "name": "演示成员 · 江墨"},
                {"op": "create_position", "id": "coordination", "title": "演示经营与策划", "mandate": "仅为回归测试安排计划", "permissions": sorted(OPERATIONS) + ["produce_artifact"]},
                {"op": "create_position", "id": "writing", "title": "演示创作", "mandate": "仅为回归测试交付脚本正文", "permissions": ["produce_artifact"]},
                {"op": "assign", "id": "a-planner", "position_id": "coordination", "member_id": "planner"},
                {"op": "assign", "id": "a-writer", "position_id": "writing", "member_id": "writer"},
                {"op": "set_policy", "decision_position_id": "coordination"},
                {"op": "create_work", "id": "bible", "title": "建立小说设定", "instruction": "明确小说世界与连续三章规划", "position_id": "coordination", "dependencies": []},
                self.work(1, ["bible"]),
            ]
        elif len(company["chapters"]) > len(company["reviews"]):
            n = len(company["chapters"])
            refs = [company["chapters"][-1]["feedback_event_id"]]
            if n < 3:
                ops.append(self.work(n + 1, [f"chapter-{n}"]))
            response = ("固定低订阅不证明市场需求。将第三章开头改为十秒限时威胁，减少行程说明，以角色主动行动解决冲突。" if n == 2 else
                        "核算本周期模拟收入和估算成本，保留人物与设定，继续下一章。" if n == 1 else "三章已交付并完成模拟核算；停止本次试验，等待董事会审读正文与衔接。")
            ops.append({"op": "review_cycle", "chapter_number": n, "response": response, "next_work_ids": [f"chapter-{n+1}"] if n < 3 else []})
        else:
            n = len(company["chapters"]) + 1
            aid = ctx["work"][f"chapter-{n}"]["artifact_ids"][-1]
            refs = [aid]
            ops = [{"op": "submit_chapter", "artifact_id": aid, "chapter_number": n, "book_title": "借来的明天", "title": ["借来的明天", "不存在的车站", "我不选"][n-1]}]
        m = package["context_manifest"]
        return {"base_state_version": m["state_version"], "charter_version": m["charter_version"], "policy_version": m["policy_version"],
                "issue": "脚本演示经营步骤", "rationale": "仅用于确定性验证，非模型判断", "expected_effect": "验证持久经营机制", "evidence_refs": refs, "operations": ops}, {"input_tokens": 1000, "output_tokens": 300}

    def work(self, n, dependencies):
        return {"op": "create_work", "id": f"chapter-{n}", "title": f"交付第 {n} 章",
                "instruction": "延续同一本小说和前文设定。" + ("根据第二周期负面反馈，把十秒限时威胁放在开头，减少流水账式行程叙述，增加主动选择与即时后果。" if n == 3 else "交付可阅读的完整正文。"),
                "position_id": "writing", "dependencies": dependencies}


def seed(app):
    """Idempotent separate demo creation, only used under the explicit --novel-demo flag."""
    from .runner import run
    charter = {"text": "明确标识的小说公司脚本演示；无真实发布或支付。", "allowed_operations": sorted(OPERATIONS),
               "allowed_tools": ["produce_artifact"], "reserved_matters": ["goal", "resources", "charter", "funding", "dissolution"], "board_can_amend": True}
    board = app.new_session("board")
    receipt = app.command(board, {"id": "novel-demo-creation-v1", "organization_id": None, "base_version": None, "kind": "create",
        "data": {"name": "借来的明天 · 模拟小说公司", "goal": "明确标识的脚本演示：连续交付同一本小说三章，验证反馈、决策与后续交付。",
                 "board_name": "本机演示采用人", "charter": charter, "resources": {"max_calls": 32, "timeout_seconds": 180}, "company": CONFIG}})
    if receipt["status"] != "succeeded":
        raise RuntimeError(receipt["message"])
    engine = app.engine(board, receipt["organization_id"])
    if not engine.runs():
        run(engine, NovelDemoExecutor(), 30)
    return engine
