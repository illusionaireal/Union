"""Run mechanisms and a fresh, explicitly simulated CLI scenario; preserve real exit codes."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="evidence/001-org-bootstrap")
    p.add_argument("--root", help="New local state directory; must not already exist")
    args = p.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(args.root).resolve() if args.root else Path(tempfile.mkdtemp(prefix="ai-union-validation-")) / "org"
    if root.exists():
        raise SystemExit("Refusing to overwrite validation state; use a fresh --root")
    commands = [
        ("tests", ["-m", "unittest", "discover", "-v"], 0),
        ("init", ["-m", "ai_union", "--root", str(root), "init", "--name", "validated fixture",
                  "--board-name", "local developer (test adoption)", "--charter", "examples/charter.local.json",
                  "--resources", "examples/resources.local.json"], 0),
        ("fixture-run", ["-m", "ai_union", "--root", str(root), "run", "--executor", "fixture",
                         "--fixture", "examples/fixture.json", "--max-steps", "8"], 0),
        ("status", ["-m", "ai_union", "--root", str(root), "status"], 0),
        ("followup-context", ["-m", "ai_union", "--root", str(root), "context", "--work-id", "work-followup"], 0),
        ("evaluation", ["-m", "ai_union", "--root", str(root), "evaluate", "--output", str(output / "fixture-evaluation.json")], 3),
        ("restart-wait", ["-m", "ai_union", "--root", str(root), "run", "--executor", "fixture",
                          "--fixture", "examples/fixture.json", "--max-steps", "1"], 0),
    ]
    records = []
    for label, cmd, expected in commands:
        result = subprocess.run([sys.executable, *cmd], cwd=REPO, capture_output=True, text=True)
        (output / (label + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        records.append({"command": ["python3", *cmd], "exit_code": result.returncode,
                        "expected_exit_code": expected, "log": label + ".log"})
        if result.returncode != expected:
            print(result.stdout + result.stderr, file=sys.stderr)
            return result.returncode or 1
        print(label + ": " + str(result.returncode))
    from ai_union.engine import Engine
    from ai_union.evaluation import evaluate
    engine = Engine(root)
    report = evaluate(engine)
    if not report["mechanism_scenario_passed"] or report["real_agent_verified"] or len(engine.runs()) != 6:
        raise SystemExit("Unexpected fixture verdict or run count")
    for artifact in engine.state()["artifacts"].values():
        (output / artifact["name"]).write_text(engine._read_artifact(artifact), encoding="utf-8")
    for label, data in (("events", engine.events()), ("decisions", engine.decisions())):
        (output / (label + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    files = [p for folder in ("ai_union", "tests", "examples", "scripts") for p in (REPO / folder).rglob("*")
             if p.is_file() and p.suffix in (".py", ".json")]
    snapshot = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}
    source = REPO / "docs/inputs/AI_UNION_开发执行交接文档_v1.0.md"
    summary = {"date": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
               "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
               "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip(),
               "python": sys.version.split()[0], "model_calls": 0,
               "real_agent_status": "not_run: finite real-model authorization not supplied",
               "commands": records, "local_state": str(root), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None,
               "workspace_code_snapshot": snapshot}
    (output / "validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("mechanisms validated; model calls: 0; real eval: not run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
