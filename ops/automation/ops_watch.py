"""Host-local deployment watch. No project state is inferred or written here."""
from contextlib import contextmanager
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".watch-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        held = False
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = True
        except (BlockingIOError, OSError):
            pass
        try:
            yield held
        finally:
            if held:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)


def poll(root, read_snapshot):
    root = Path(root)
    with lock(root / "poll.lock") as held:
        if not held:
            return {"status": "busy"}
        state = read_json(root / "status.json")
        state["last_attempt"] = now()
        try:
            snapshot = read_snapshot()
            digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
            state.update(status="ok", last_success=now(), fingerprint=digest,
                         snapshot=snapshot, error=None,
                         pending=digest != state.get("acknowledged_fingerprint"))
        except Exception as error:
            # Error text may contain a private URL or request credentials.
            state.update(status="failed", error=type(error).__name__)
        write_json(root / "status.json", state)
        return state


def acknowledge(root, fingerprint):
    root = Path(root)
    with lock(root / "poll.lock") as held:
        if not held:
            return False
        state = read_json(root / "status.json")
        state["acknowledged_fingerprint"] = fingerprint
        state["pending"] = fingerprint != state.get("fingerprint")
        write_json(root / "status.json", state)
        return True


def environment(file):
    return dict(line.split("=", 1) for line in Path(file).read_text(encoding="utf-8").splitlines()
                if "=" in line and not line.lstrip().startswith("#"))


def run_command(*args, **kwargs):
    if os.name == "nt":
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.run(*args, **kwargs)


def collect(config):
    env = environment(config["env_file"])
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({
        "http": env.get("HTTP_PROXY", ""), "https": env.get("HTTPS_PROXY", "")}))

    def get(url, token):
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 UnionOps", "Authorization": "Bearer " + token,
            "Accept": "application/json"})
        with opener.open(request, timeout=25) as response:
            return json.load(response)

    board_url = env["UNION_KANBAN_URL"].rstrip("/") + "/api"
    board = get(board_url + "/board", env["UNION_KANBAN_KEY"])
    messages = get(board_url + "/messages?limit=50", env["UNION_KANBAN_KEY"])
    credential = run_command(["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True,
        timeout=15, check=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    token = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)["password"]
    github = "https://api.github.com/repos/" + config["github_repository"]
    prs = get(github + "/pulls?state=open&per_page=100", token)
    changes = []
    for pr in prs:
        checks = get(github + "/commits/" + pr["head"]["sha"] + "/check-runs?per_page=100", token)
        changes.append({"number": pr["number"], "sha": pr["head"]["sha"], "base": pr["base"]["ref"],
                        "draft": pr["draft"], "updated_at": pr["updated_at"],
                        "checks": sorted((c["name"], c["status"], c["conclusion"] or "") for c in checks["check_runs"])})
    runs = get(github + "/actions/runs?branch=rewrite%2Fcharter-v1&per_page=6", token)
    health = run_command(["ssh", "-p", str(config["ssh_port"]), "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8", config["ssh_target"],
        config["health_command"]], text=True, capture_output=True, timeout=20)
    return {"board_revision": board["revision"], "latest_message_id": messages.get("latest_id"),
            "messages": [{"id": m["id"], "deleted": bool(m.get("deleted_at"))} for m in messages["messages"]],
            "cards": [{k: t.get(k) for k in ("id", "version", "status", "assignee")} for t in board["tasks"] if not t["archived"]],
            "prs": changes,
            "runs": [{k: r.get(k) for k in ("id", "head_sha", "status", "conclusion")} for r in runs["workflow_runs"]],
            "nas": {"exit_code": health.returncode,
                    "health": health.stdout.strip() if health.returncode == 0 else "ssh_or_probe_failed"}}


def run_agent(config, state, run=run_command):
    root = Path(config["state_dir"])
    if state.get("status") != "ok" or not state.get("pending"):
        return "idle"
    if not config.get("agent_enabled", False):
        write_json(root / "agent.json", {"status": "disabled", "at": now()})
        return "disabled"
    with lock(root / "agent.lock") as held:
        if not held:
            return "busy"
        login = run([config["codex"], "login", "status"], capture_output=True, timeout=20)
        if login.returncode:
            write_json(root / "agent.json", {"status": "login_required", "at": now()})
            return "login_required"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = root / (stamp + "-result.json")
        schema = root / "result-schema.json"
        write_json(schema, {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["handled", "follow_up"]},
            "summary": {"type": "string"}}, "required": ["status", "summary"], "additionalProperties": False})
        prompt = Path(config["prompt_file"]).read_text(encoding="utf-8")
        write_json(root / "agent.json", {"status": "running", "at": now(), "run": stamp})
        # stdin keeps the prompt out of the process command line. No fixed job timeout.
        with (root / (stamp + ".log")).open("w", encoding="utf-8") as log:
            result = run([config["codex"], "exec", "-C", config["repository"],
                "-s", "danger-full-access", "-c", 'approval_policy="never"',
                "--color", "never", "--output-schema", str(schema), "-o", str(output), "-"],
                input=prompt, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
        try:
            response = read_json(output)
        except (ValueError, OSError):
            response = {}
        handled = result.returncode == 0 and response.get("status") == "handled"
        if handled:
            acknowledge(root, state["fingerprint"])
        status = "handled" if handled else "follow_up"
        write_json(root / "agent.json", {"status": status, "at": now(), "run": stamp, "exit_code": result.returncode})
        return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = read_json(Path(args.config))
    state = poll(config["state_dir"], lambda: collect(config))
    try:
        agent = run_agent(config, state)
    except Exception as error:
        agent = "failed"
        write_json(Path(config["state_dir"]) / "agent.json", {"status": agent, "error": type(error).__name__, "at": now()})
    print(json.dumps({"poll": state["status"], "last_success": state.get("last_success"), "agent": agent}))
    return 0 if state["status"] in ("ok", "busy") else 1


if __name__ == "__main__":
    raise SystemExit(main())
