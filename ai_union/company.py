"""Optional novel-company experiment. Platform facts are host-owned, never model-written."""
import copy

from .engine import require, text, now, uid

OPERATIONS = {"submit_chapter", "review_cycle"}
CONFIG_FIELDS = {"initial_budget_minor", "input_price_minor_per_million", "output_price_minor_per_million"}


def validate_config(config):
    require(isinstance(config, dict) and set(config) == CONFIG_FIELDS, "小说公司需要启动预算和输入/输出单价")
    for key in CONFIG_FIELDS:
        require(type(config[key]) is int and 0 <= config[key] <= 10**10, "金额必须为有界整数分")
    require(config["initial_budget_minor"] > 0, "启动预算须大于零")
    return copy.deepcopy(config)


def create(config):
    return {"kind": "novel", "currency": "CNY", "config": validate_config(config),
            "platform": {"version": "novel-mock-v1", "simulated": True, "subscriptions": [12, 2, 8],
                         "price_minor": 30, "server_minor": 20, "tax_basis_points": 600},
            "target_cycles": 3, "book_title": None, "chapters": [], "reviews": [], "ledger": [],
            "scope": "同一本小说连续三章；第二周期低订阅是受控实验，不能推断市场或质量。"}


def ledger_entry(company, entry_id, kind, amount, source, reference, **extra):
    require(not any(row["id"] == entry_id for row in company["ledger"]), "账本条目重复")
    company["ledger"].append({"id": entry_id, "kind": kind, "amount_minor": amount, "currency": "CNY",
                              "source": source, "reference": reference, "created_at": now(), **extra})


def totals(company):
    ledger = company["ledger"]
    def total(kind):
        return sum(row["amount_minor"] for row in ledger if row["kind"] == kind and row["amount_minor"] is not None)
    return {"initial_budget_minor": company["config"]["initial_budget_minor"],
            "balance_minor": company["config"]["initial_budget_minor"] + sum(row["amount_minor"] or 0 for row in ledger),
            "income_minor": total("subscription"), "operating_cost_minor": -total("server") - total("tax"),
            "model_estimate_minor": -total("model"),
            "unknown_model_costs": sum(row["kind"] == "model" and row["amount_minor"] is None for row in ledger)}


def charge(company, run, usage):
    simulated = run["executor"] == "fixture" or (run["executor"] == "api" and run["package"].get("execution", {}).get("transport_source") == "local_test")
    source = "simulated_usage" if simulated else "provider_usage_estimate"
    inp, out = usage.get("input_tokens"), usage.get("output_tokens")
    amount = None
    if type(inp) is int and type(out) is int:
        prices = company["config"]
        amount = -((inp * prices["input_price_minor_per_million"] + out * prices["output_price_minor_per_million"] + 999999) // 1000000)
    ledger_entry(company, "model-" + run["id"], "model", amount, source, run["id"],
                 input_tokens=inp, output_tokens=out, prices=copy.deepcopy(company["config"]), run_status=run.get("status"))


def operate(engine, cx, state, operation, decision):
    c = state.get("company")
    require(c is not None, "此组织没有启用小说公司试验")
    op = operation["op"]
    if op == "submit_chapter":
        require(set(operation) == {"op", "artifact_id", "chapter_number", "book_title", "title"}, "投稿字段不正确")
        aid = operation["artifact_id"]
        require(isinstance(aid, str) and aid in state["artifacts"], "投稿必须引用已有实际成果")
        n = operation["chapter_number"]
        require(type(n) is int and 1 <= n <= c["target_cycles"], "章节序号超出试验范围")
        title = text(operation["title"], "章节名", 200)
        book = text(operation["book_title"], "小说名称", 200)
        previous = next((ch for ch in c["chapters"] if ch["chapter_number"] == n), None)
        if previous:
            require((previous["artifact_id"], previous["title"], c["book_title"]) == (aid, title, book), "章节已提交，不能重复结算或替换")
            return
        require(n == len(c["chapters"]) + 1 and len(c["reviews"]) == n - 1, "请按章节顺序投稿，并先复盘上一周期反馈")
        require(not c["book_title"] or c["book_title"] == book, "首版须持续交付同一本小说")
        require(not any(ch["artifact_id"] == aid for ch in c["chapters"]), "不能将同一成果重复作为新章节")
        artifact = state["artifacts"][aid]
        require(aid in decision["evidence_refs"], "投稿决定必须引用正文成果")
        require(state["work"][artifact["work_id"]]["status"] == "delivered" and artifact["work_version"] == state["work"][artifact["work_id"]]["version"], "投稿须使用当前已完成工作版本的正文")
        content = engine._read_artifact(artifact)
        require(len(content.strip()) >= 800, "章节正文至少 800 字符；提纲不能作为首版章节交付")
        require(not any(state["artifacts"][ch["artifact_id"]]["sha256"] == artifact["sha256"] for ch in c["chapters"]), "不能重复提交相同正文")
        if n > 1:
            review = c["reviews"][-1]
            # Follow execution-time artifact provenance, never a dependency graph edited later.
            manuscript_run = engine._run(cx, artifact["run_id"])
            require(manuscript_run["started_at"] > review["created_at"], "下一章必须在反馈决定后实际执行")
            candidates = [artifact] + manuscript_run["package"]["context"]["artifacts"]
            follows = any(a["work_id"] in review["next_work_ids"]
                          and a["work_version"] >= review["next_work_versions"][a["work_id"]]
                          and engine._run(cx, a["run_id"])["started_at"] > review["created_at"] for a in candidates)
            require(follows, "下一章须实际使用上一周期决定后交付的成果")
        platform = c["platform"]
        subscriptions = platform["subscriptions"][n - 1]
        income = subscriptions * platform["price_minor"]
        tax = (income * platform["tax_basis_points"] + 9999) // 10000
        feedback = ("受控负面反馈：订阅由 12 降到 2。读者认为冲突出现太晚、叙述像流水账；请自行决定可执行调整，并在下一章落实。" if n == 2
                    else "模拟反馈：章节已接收。请核算本轮收支并安排下一步；订阅数不代表实际市场质量。")
        event_id = uid("novel-feedback-" + str(n))
        chapter = {"chapter_number": n, "title": title, "artifact_id": aid, "work_id": artifact["work_id"],
                   "decision_id": decision["id"], "feedback_event_id": event_id, "subscriptions": subscriptions,
                   "income_minor": income, "feedback": feedback, "negative_feedback": n == 2,
                   "simulated": True, "submitted_at": now()}
        c["book_title"] = book
        c["chapters"].append(chapter)
        for kind, amount in (("subscription", income), ("server", -platform["server_minor"]), ("tax", -tax)):
            ledger_entry(c, f"chapter-{n}-{kind}", kind, amount, "mock_platform", event_id)
        require(engine._event(cx, "novel_feedback", chapter | {"source": platform["version"], "totals": totals(c)}, event_id), "平台反馈 ID 冲突；本次投稿和结算均未提交")
    elif op == "review_cycle":
        require(set(operation) == {"op", "chapter_number", "response", "next_work_ids"}, "复盘字段不正确")
        n = operation["chapter_number"]
        require(type(n) is int and n == len(c["reviews"]) + 1 and n == len(c["chapters"]), "此周期尚未投稿或已完成复盘")
        chapter = c["chapters"][-1]
        require(chapter["decision_id"] != decision["id"], "必须在取得平台反馈后另作经营决定")
        require(chapter["feedback_event_id"] in decision["evidence_refs"], "复盘必须引用本周期平台反馈")
        response = text(operation["response"], "反馈分析与下一步措施", 10000)
        ids = operation["next_work_ids"]
        require(isinstance(ids, list) and all(isinstance(w, str) for w in ids) and len(ids) == len(set(ids)), "后续工作引用不正确")
        changed = {o.get("id", o.get("work_id")) for o in decision["operations"] if o["op"] in ("create_work", "update_work")}
        require(all(w in state["work"] and w in changed and state["work"][w]["status"] == "pending" for w in ids), "先创建或修改后续工作，再复盘；不能只写反思")
        require(bool(ids) if n < c["target_cycles"] else not ids, "前两周期须安排实际后续工作，第三周期结束有限试验")
        c["reviews"].append({"chapter_number": n, "decision_id": decision["id"], "feedback_event_id": chapter["feedback_event_id"],
                             "response": response, "next_work_ids": ids, "next_work_versions": {wid: state["work"][wid]["version"] for wid in ids}, "created_at": now()})


def view(state):
    c = state.get("company")
    if not c:
        return None
    result = copy.deepcopy(c)
    result["totals"] = totals(c)
    result["completed"] = len(c["reviews"]) == c["target_cycles"]
    result["feedback_actions"] = [r | {"delivered_work_ids": [wid for wid in r["next_work_ids"] if state["work"][wid]["status"] == "delivered"]} for r in c["reviews"]]
    result["quality_review"] = "待人工审读：设定、情节衔接、每章推进、负面反馈后的实际改变。"
    return result


def guidance():
    return ("This organization is running the three-cycle novel-company experiment in context.company. "
            "Choose the genre, book, team, roles and production process yourselves. At least two members should do real work with artifact dependencies. "
            "Produce readable Chinese chapters of 1000–1800 characters, one coherent book. Host operations submit_chapter and review_cycle are authorized ONLY by the effective charter/position. "
            "A decision can submit an already delivered chapter artifact with book_title, chapter_number, title, artifact_id and evidence_refs. "
            "The host returns immutable mock subscriptions, feedback and settlement in a new novel_feedback event. "
            "In a later decision, analyze that feedback and financial totals, create/update pending next work, then review_cycle with response, next_work_ids and feedback evidence_refs. "
            "Prioritize feedback before existing work. The next chapter must follow that new work. Actual changes must appear in task instructions AND the next manuscript. "
            "Do not just write a reflection. After chapter three, review_cycle with empty next_work_ids ends this bounded experiment. "
            "Never claim mock revenue is real or that fixed mock subscriptions prove quality. Published chapters and financial history are in context.company. ")


def resolve_usage(engine, board_key, run_id, input_tokens, output_tokens, reason):
    """Audited board transcription of a provider receipt; original run usage stays unchanged."""
    for value in (input_tokens, output_tokens):
        require(type(value) is int and 0 <= value <= 10**9, "核对用量须为非负整数")
    text(reason, "用量核对依据", 1000)
    with engine.transaction() as cx:
        board = engine._board(cx, board_key)
        state = engine._state(cx)
        require(state.get("company") is not None, "没有小说公司账本")
        run = engine._run(cx, run_id)
        require(run["status"] not in ("running", "unknown"), "先核对未知执行结果，再核对费用")
        company = state["company"]
        row = next((row for row in company["ledger"] if row["kind"] == "model" and row["reference"] == run_id), None)
        require(row is not None and row["amount_minor"] is None, "只可补录缺失用量，不能覆盖已结算费用")
        prices = row["prices"]
        row["amount_minor"] = -((input_tokens * prices["input_price_minor_per_million"] + output_tokens * prices["output_price_minor_per_million"] + 999999) // 1000000)
        row["original_usage"] = {"input_tokens": row["input_tokens"], "output_tokens": row["output_tokens"], "source": row["source"]}
        row.update(input_tokens=input_tokens, output_tokens=output_tokens, source="board_usage_estimate", correction_reason=reason, corrected_at=now())
        engine._event(cx, "company_usage_reconciled", {"run_id": run_id, "input_tokens": input_tokens, "output_tokens": output_tokens, "reason": reason, "board": board})
        state["version"] += 1
        engine._save(cx, state)
