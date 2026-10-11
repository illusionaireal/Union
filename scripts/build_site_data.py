"""Export a whitelist of public fixture evidence. Never read databases or credentials."""
import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/001-org-bootstrap"
SITE = ROOT / "site"


def read(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def main():
    validation = read("validation.json")
    evaluation = read("fixture-evaluation.json")
    status = read("status.log")["organization"]
    match = re.search(r"Ran (\d+) tests", (EVIDENCE / "tests.log").read_text())
    if not match or not (EVIDENCE / "tests.log").read_text().rstrip().endswith("OK"):
        raise SystemExit("Cannot confirm a completed passing mechanism test run")
    if evaluation["status"] != "simulated" or validation["model_calls"] != 0:
        raise SystemExit("This exporter only accepts explicitly simulated, zero-model-call evidence")
    artifacts = []
    target = SITE / "data"
    target.mkdir(parents=True, exist_ok=True)
    for item in sorted(status["artifacts"].values(), key=lambda a: a["created_at"]):
        name = item["name"]
        if name not in ("source.md", "dependent.md", "followup.md"):
            raise SystemExit("Unexpected public artifact; review before exporting")
        content = (EVIDENCE / name).read_text(encoding="utf-8")
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != item["sha256"]:
            raise SystemExit("Public artifact integrity check failed: " + name)
        artifacts.append({"name": name, "work_id": item["work_id"], "version": item["version"],
                          "sha256": item["sha256"], "content": content, "path": "data/" + name})
        (target / name).write_text(content, encoding="utf-8")
    capabilities = [
        ["F01 · 目标与章程", "组织身份、目标、章程采用与资源持久化", "当前仅本地测试采用"],
        ["F02 · 临时启动", "启动权限一次性提交，至少两成员任职", "模型自组织尚未运行"],
        ["F03 · 正式决定", "身份、权限、版本、引用与事务校验", "真实执行器输出待实测"],
        ["F04 · 成员协作", "Codex CLI 适配与跨成员依赖接口", "当前执行来自 fixture"],
        ["F05 · 成果保存", "文件、版本、SHA-256 与任务来源", "当前为模拟文本成果"],
        ["F06 · 后续行动", "成果进入组织决定并派发后续工作", "真实模型判断待验证"],
        ["F07 · 责任交接", "任职调整、未完成责任与旧权限撤回", "受控机制测试通过"],
        ["F08 · 等待与恢复", "持久复查、事件唤醒、未知执行核对", "无长期运行可靠性结论"],
        ["F09 · 章程修订", "受信董事会入口、历史与新授权生效", "本地身份信任边界"],
        ["F10 · 资料与上下文", "岗位、任务、依赖与版本清单", "仅支持文本资料"],
        ["F11 · 状态观察", "CLI 状态、事件、决定与用量", "网站展示验证快照"],
        ["F12 · 有限资源", "调用占用、超时和 token 回执记录", "Codex 金额费用未知"],
    ]
    steps = [
        {"title": "从一句目标开始", "label": "目标", "description": "原始目标、章程与有限资源已保存。此刻还没有成员或工作。", "phase": "待启动", "version": 0, "calls": 0, "members": False, "work": [], "event": "目标与测试章程已准备"},
        {"title": "组织安排成为正式状态", "label": "组织", "description": "通用启动决定建立两名测试成员、岗位与任职，并派发存在依赖的工作。有效提交后，临时启动授权结束。", "phase": "组织已形成", "version": 1, "calls": 1, "members": True, "work": ["pending", "dependent"], "event": "启动决定提交；临时启动授权结束"},
        {"title": "成员 A 保存第一份成果", "label": "首次行动", "description": "测试成员 A 执行 work-one，实际测试程序保存 source.md，并登记任务来源与文件校验摘要。", "phase": "协作进行中", "version": 3, "calls": 2, "members": True, "work": ["done", "pending"], "event": "work-one 交付；source.md 已保存"},
        {"title": "成员 B 使用依赖资料", "label": "依赖协作", "description": "成员 B 的工作包包含成员 A 的成果和资料版本。work-two 交付 dependent.md，跨成员依赖得到机制验证。", "phase": "首次协作完成", "version": 5, "calls": 3, "members": True, "work": ["done", "done"], "event": "work-two 交付；跨成员资料依赖可追踪"},
        {"title": "成果触发下一轮决定", "label": "后续决定", "description": "决策责任岗位引用已交付工作，创建 work-followup。决定、状态变更和待办在同一事务中保存。", "phase": "后续工作已派发", "version": 6, "calls": 4, "members": True, "work": ["done", "done", "pending"], "event": "依据 work-one / work-two 创建后续任务"},
        {"title": "后续决定落实为行动", "label": "后续行动", "description": "成员 B 实际执行测试程序中的后续工作，保存 followup.md。闭环包含行动与可读取文件，不止一份计划。", "phase": "后续工作完成", "version": 8, "calls": 5, "members": True, "work": ["done", "done", "done"], "event": "work-followup 交付；第 3 份成果已保存"},
        {"title": "等待新事件，保留状态", "label": "持久等待", "description": "最后的决定登记等待；没有新事件时不再调用执行器。新进程读取已有成员、工作和成果，保持等待。", "phase": "等待新事件", "version": 9, "calls": 6, "members": True, "work": ["done", "done", "done"], "event": "持久等待；重启后没有新增调用"},
    ]
    if steps[-1]["version"] != status["version"] or len(evaluation["usage"]) != steps[-1]["calls"]:
        raise SystemExit("Fixture evidence changed; update the replay rather than misrepresenting it")
    data = {"schema_version": 1, "iteration": "001-org-bootstrap", "source": "local fixture validation snapshot",
            "validated_at": validation["date"], "base_commit": validation["base_commit"],
            "metrics": {"tests_passed": int(match[1]), "members": len(status["members"]), "artifacts": len(artifacts),
                        "real_model_calls": validation["model_calls"], "fixture_calls": len(evaluation["usage"])},
            "verification": {"mechanism_scenario_passed": evaluation["mechanism_scenario_passed"], "real_agent_verified": False,
                             "external_delivery_verified": False, "external_market_feedback_verified": False,
                             "wheel_installed_in_isolation": True},
            "limitations": ["本页面是验证快照，不是实时组织后台", "演示是 fixture 重放，不调用模型或修改数据库", "真实 Agent 协作尚未试跑", "真实发布与市场反馈尚未接入"],
            "capabilities": capabilities, "artifacts": artifacts, "steps": steps,
            "work": [{"id": "work-one", "title": "生成模拟资料", "member": "A", "dependency": "无依赖"},
                     {"id": "work-two", "title": "使用依赖成果", "member": "B", "dependency": "依赖 work-one"},
                     {"id": "work-followup", "title": "完成后续动作", "member": "B", "dependency": "依赖 work-two"}]}
    js = json.dumps(data, ensure_ascii=False, indent=2)
    (target / "progress.json").write_text(js + "\n", encoding="utf-8")
    (target / "progress.js").write_text("window.UNION_DATA = " + js + ";\n", encoding="utf-8")
    print(f"public website snapshot: {data['metrics']['tests_passed']} tests, {len(artifacts)} simulated artifacts, 0 real model calls")


if __name__ == "__main__":
    main()
