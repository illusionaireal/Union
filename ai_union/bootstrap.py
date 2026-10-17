"""Host-owned bootstrap drafts. No official member exists until adoption."""
import copy
import json

from .agent_protocol import compile_tool, fields
from .engine import encoded, now, require, text
from .protocol import STRING, STRINGS, obj


BOOTSTRAP_TOOLS = {
    "prepare_member": ("筹建一名成员及其初始岗位；同名再次调用更新草案，不重复建立。", obj({"name": STRING, "role": STRING, "mandate": STRING})),
    "arrange_work": ("安排或修改首批工作草案；owner 为成员姓名，dependencies 为任务标题。", fields({"title": STRING, "instruction": STRING, "owner": STRING, "dependencies": STRINGS}, ["title", "instruction", "owner"])),
    "configure_bootstrap": ("确定承担后续组织决策责任的成员及初始策略。", fields({"coordinator": STRING, "strategy": STRING}, ["coordinator"])),
    "inspect_bootstrap": ("查看已保存的成员、任务和协调责任草案。", obj({})),
    "discard_bootstrap_item": ("移除不再需要的筹建成员或任务；正式组织不受影响。", obj({"kind": {"type": "string", "enum": ["member", "task"]}, "name": STRING})),
    "activate_organization": ("校验并提交已保存草案，正式成立组织。请单独调用本工具。", obj({})),
}


def setup(cx):
    cx.execute("CREATE TABLE IF NOT EXISTS bootstrap_draft(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL, updated_at TEXT NOT NULL)")


def read(cx):
    if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='bootstrap_draft'").fetchone():
        return None
    row = cx.execute("SELECT data,updated_at FROM bootstrap_draft WHERE id=1").fetchone()
    return (json.loads(row["data"]) | {"updated_at": row["updated_at"]}) if row else None


def guard(engine, cx, package):
    state = engine._state(cx)
    require(package.get("actor") == "bootstrap" and state["phase"] == "bootstrap", "启动授权已经结束")
    require(engine._run(cx, package["run_id"])["status"] == "running", "筹建调用已经结束")
    for field, expected in (("state_version", state["version"]), ("charter_version", state["charter_version"]), ("policy_version", state["policy_version"])):
        require(package["context_manifest"][field] == expected, "筹建依据已变化，请读取当前资料继续")
    return state


def operate(engine, package, name, args):
    from .model_api import reject_saved_secrets, validate_output
    require(name in BOOTSTRAP_TOOLS, "本轮未授权该工具")
    validate_output(args, BOOTSTRAP_TOOLS[name][1])
    with engine.transaction() as cx:
        guard(engine, cx, package)
        reject_saved_secrets(cx, args)
        setup(cx)
        draft = read(cx) or {"members": [], "tasks": []}
        draft.pop("updated_at", None)
        if name == "prepare_member":
            for key in ("name", "role", "mandate"):
                text(args[key], key, 200 if key != "mandate" else 10000)
            old = next((m for m in draft["members"] if m["name"] == args["name"]), None)
            if old is None:
                require(len(draft["members"]) < 20, "初始化需要至少两名成员，最多二十名")
                draft["members"].append(copy.deepcopy(args))
            else:
                old.update(args)
        elif name == "arrange_work":
            text(args["title"], "任务标题", 200)
            text(args["instruction"], "交付要求", 100000)
            text(args["owner"], "负责人", 200)
            require(len(args.get("dependencies", [])) <= 30, "任务依赖过多")
            old = next((t for t in draft["tasks"] if t["title"] == args["title"]), None)
            if old is None:
                require(len(draft["tasks"]) < 30, "初始化需要一至三十项首批任务")
                draft["tasks"].append(copy.deepcopy(args))
            else:
                old.clear()
                old.update(copy.deepcopy(args))
        elif name == "configure_bootstrap":
            text(args["coordinator"], "协调负责人", 200)
            if "strategy" in args:
                text(args["strategy"], "策略", 10000)
            draft.update(args)
        elif name == "activate_organization":
            # Compile using the current host package, never draft-supplied versions.
            return compile_tool(package, "initialize_organization", draft)
        elif name == "discard_bootstrap_item":
            collection, key = ("members", "name") if args["kind"] == "member" else ("tasks", "title")
            draft[collection] = [item for item in draft[collection] if item[key] != args["name"]]
            if args["kind"] == "member" and draft.get("coordinator") == args["name"]:
                draft.pop("coordinator")
        if name != "inspect_bootstrap":
            require(len(encoded(draft)) <= 300000, "筹建草案超出容量")
            cx.execute("INSERT INTO bootstrap_draft VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at", (encoded(draft), now()))
        return draft
