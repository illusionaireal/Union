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


class PartialCollectionError(Exception):
    """Some independent sources were observed, but no complete snapshot exists."""

    def __init__(self, observations):
        super().__init__("incomplete source observations")
        self.observations = observations


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
            state.pop("observations", None)
        except PartialCollectionError as error:
            state.update(status="failed", error=type(error).__name__, observations=error.observations)
        except Exception as error:
            # Error text may contain a private URL or request credentials.
            state.update(status="failed", error=type(error).__name__)
        write_json(root / "status.json", state)
        return state


def acknowledge(root, fingerprint, *, partial=False):
    root = Path(root)
    with lock(root / "poll.lock") as held:
        if not held:
            return False
        state = read_json(root / "status.json")
        if partial:
            state["acknowledged_partial_fingerprint"] = fingerprint
        else:
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
    env_error = None
    try:
        env = environment(config["env_file"])
    except (OSError, ValueError, KeyError) as error:
        env, env_error = {}, error
    proxies = {scheme: env[key] for scheme, key in (("http", "HTTP_PROXY"), ("https", "HTTPS_PROXY"))
               if env.get(key)}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))

    def get(url, token):
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 UnionOps", "Authorization": "Bearer " + token,
            "Accept": "application/json"})
        with opener.open(request, timeout=25) as response:
            return json.load(response)

    def read_board():
        if env_error is not None:
            raise env_error
        board_url = env["UNION_KANBAN_URL"].rstrip("/") + "/api"
        board = get(board_url + "/board", env["UNION_KANBAN_KEY"])
        messages = get(board_url + "/messages?limit=50", env["UNION_KANBAN_KEY"])
        return {"board_revision": board["revision"], "latest_message_id": messages.get("latest_id"),
                "messages": [{"id": m["id"], "deleted": bool(m.get("deleted_at"))} for m in messages["messages"]],
                "cards": [{k: t.get(k) for k in ("id", "version", "status", "assignee")}
                          for t in board["tasks"] if not t["archived"]]}

    def read_github():
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
        return {"prs": changes,
                "runs": [{k: r.get(k) for k in ("id", "head_sha", "status", "conclusion")}
                         for r in runs["workflow_runs"]]}

    def read_nas():
        health = run_command(["ssh", "-p", str(config["ssh_port"]), "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8", config["ssh_target"],
            config["health_command"]], text=True, capture_output=True, timeout=20)
        return {"nas": {"exit_code": health.returncode,
                        "health": health.stdout.strip() if health.returncode == 0 else "ssh_or_probe_failed"}}

    snapshot, observations = {}, {}
    for name, read in (("board", read_board), ("github", read_github), ("nas", read_nas)):
        try:
            value = read()
            observations[name] = {"status": "ok", "at": now(), "data": value}
            snapshot.update(value)
        except Exception as error:
            # Keep sources independent; exception messages can contain private URLs or credentials.
            observations[name] = {"status": "failed", "at": now(), "error": type(error).__name__}
    if any(value["status"] == "failed" for value in observations.values()):
        raise PartialCollectionError(observations)
    return snapshot


def execution_signal(state):
    if state.get("status") == "ok" and state.get("fingerprint"):
        return {"kind": "complete", "fingerprint": state["fingerprint"], "pending": state.get("pending", False)}
    if state.get("status") != "failed" or state.get("error") != "PartialCollectionError":
        return None
    observations = state.get("observations") or {}
    if not any(item.get("status") == "ok" for item in observations.values()):
        return None
    facts = {name: {key: value for key, value in item.items() if key != "at"}
             for name, item in observations.items()}
    fingerprint = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()
    return {"kind": "partial", "fingerprint": fingerprint,
            "pending": fingerprint != state.get("acknowledged_partial_fingerprint")}


def run_agent(config, state, run=run_command):
    root = Path(config["state_dir"])
    signal = execution_signal(state)
    if signal is None or not signal["pending"]:
        return "idle"
    if not config.get("agent_enabled", False):
        write_json(root / "agent.json", {"status": "disabled", "at": now()})
        return "disabled"
    with lock(root / "agent.lock") as held:
        if not held:
            return "busy"
        # A completed worker may have acknowledged this input while this caller waited for the lock.
        signal = execution_signal(read_json(root / "status.json") or state)
        if signal is None or not signal["pending"]:
            return "idle"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = root / (stamp + "-result.json")
        schema = root / "result-schema.json"
        write_json(schema, {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["handled", "follow_up"]},
            "summary": {"type": "string"}}, "required": ["status", "summary"], "additionalProperties": False})
        prompt = Path(config["prompt_file"]).read_text(encoding="utf-8")
        if signal["kind"] == "partial":
            prompt = ("Watch mode: partial. Read the current status.json observations. Continue independently "
                      "authorized work supported by fresh successful sources. Failed sources are unavailable, "
                      "not current facts; Kanban mutations still require a fresh successful board read.\n\n" + prompt)
        record = {"run": stamp, "signal_kind": signal["kind"], "fingerprint": signal["fingerprint"]}
        write_json(root / "agent.json", record | {"status": "running", "at": now()})
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
            acknowledge(root, signal["fingerprint"], partial=signal["kind"] == "partial")
        status = "handled" if handled else "follow_up"
        write_json(root / "agent.json", record | {"status": status, "at": now(), "exit_code": result.returncode})
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
