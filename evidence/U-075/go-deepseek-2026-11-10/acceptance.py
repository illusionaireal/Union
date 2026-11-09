"""Explicit real-profile acceptance; all runtime data stays in --state-dir.

Each mode opens the same isolated services. Normal/interrupt dispatch once;
reopen/serve never start a check. No fake model, patched client or direct writes
to core/modeld databases are used. See contract.md before running.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import urlencode
import uuid

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from ai_union.console import Console
from ai_union.model_service import ModelServiceClient
from ai_union.server import Server
from tests.support import CHARTER


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


class Acceptance:
    def __init__(self, root, bun):
        self.root, self.bun = root.resolve(), bun
        self.meta_path = self.root / "acceptance-private.json"
        self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        self.app = self.server = self.modeld = None
        self.token = None
        os.environ["UNION_MODELD_CONFIG"] = str(self.root / "modeld/modeld.json")

    def start(self):
        self.log = (self.root / "modeld-private.log").open("ab")
        self.modeld = subprocess.Popen([self.bun, str(REPO / "services/modeld/dist/main.js")],
            cwd=REPO, stdout=self.log, stderr=self.log, creationflags=0x08000000 if os.name == "nt" else 0)
        self.client = ModelServiceClient()
        deadline = time.monotonic() + 30
        while True:
            try:
                self.client.runtime()
                break
            except Exception:
                if self.modeld.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Isolated modeld did not start; inspect private log")
                time.sleep(.1)
        self.app = Console(self.root / "core")
        self.server = Server(self.app, static_dir=REPO / "web/console/dist")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.meta["origin"] = self.server.origin
        self.persist()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.thread.join(10)
            self.server.server_close()
        if self.app and not self.app.closed:
            self.app.close()
        if self.modeld and self.modeld.poll() is None:
            self.modeld.terminate()
            self.modeld.wait(timeout=15)
        if hasattr(self, "log"):
            self.log.close()

    def persist(self):
        save(self.meta_path, self.meta)

    def request(self, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=30)
        headers = {"Origin": self.server.origin, "Content-Type": "application/json"}
        if self.token:
            headers["Cookie"] = self.server.cookie_name + "=" + self.token
        try:
            conn.request("POST" if body is not None else "GET", path,
                json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None, headers)
            response = conn.getresponse()
            value = json.loads(response.read())
            if response.status != 200:
                save(self.root / "last-http-error-private.json", {"path": path, "status": response.status, "response": value})
                raise RuntimeError("Core HTTP rejected request: " + str(response.status))
            cookie = response.getheader("Set-Cookie")
            if cookie:
                self.token = cookie.split("=", 1)[1].split(";", 1)[0]
            return value
        finally:
            conn.close()

    def login(self, setup=False):
        value = self.request("/api/auth/" + ("setup" if setup else "login"),
            {"username": self.meta["username"], "password": self.meta["password"], "remember": True})
        principal = value["session"]["principal_id"]
        assert self.meta.get("principal", principal) == principal, "Original principal changed"
        self.meta["principal"] = principal
        self.persist()

    def au(self):
        return self.request("/api/v1/aus/" + self.meta["au_id"])["au"]

    def models(self):
        return self.request("/api/v1/models?" + urlencode({"organization_id": self.meta["au_id"]}))

    def command(self, family, kind, data, label):
        commands = self.meta.setdefault("commands", {})
        assert label not in commands, "Original command already recorded; query it, never replay the run"
        command = {"id": str(uuid.uuid4()), "organization_id": self.meta["au_id"],
                   "base_version": self.au()["version"], "kind": kind, "data": data}
        # Deliberately omit command data: a save command contains a private key.
        commands[label] = {"id": command["id"], "kind": kind, "state": "intent_saved"}
        self.persist()
        response = self.request("/api/v1/" + family + "/commands", command)
        commands[label].update(state="receipt_received", receipt=response["receipt"])
        self.persist()
        assert response["receipt"]["status"] == "succeeded", "Command rejected; inspect original private receipt"
        return response["receipt"]

    def wait(self, table, key, timeout=600):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            item = next((x for x in self.models()[table] if x["id"] == key), None)
            if item and item["status"] not in ("queued", "running", "saving", "cancel_requested"):
                return item
            time.sleep(.05)
        raise RuntimeError("Observation deadline reached; original request retained")

    def prepare(self, provider_config):
        assert "au_id" not in self.meta, "Already prepared; use the original AU"
        self.login(setup=True)
        charter = copy.deepcopy(CHARTER)
        charter["text"] = "Go DeepSeek接入验收；仅授权合成公开资料和模型验证，无业务发布。"
        creation = {"id": str(uuid.uuid4()), "organization_id": None, "base_version": None,
            "kind": "create_v1", "data": {"name": "Go DeepSeek 接入验收", "goal": "核验指定模型的资料往返和原请求恢复",
            "board_name": "验收发起人", "charter": charter, "resources": {"max_calls": 6, "timeout_seconds": 600}}}
        self.meta["creation_id"] = creation["id"]
        self.persist()
        receipt = self.request("/api/commands", creation)["receipt"]
        assert receipt["status"] == "succeeded"
        self.meta["au_id"] = receipt["organization_id"]
        self.persist()
        governance = {"profile": "local_governance.v1", "final_decision_principal_id": self.meta["principal"],
            "reserved_matters": ["charter", "goal", "resources", "appointments", "mandates", "dissolution"],
            "unavailability": {"mode": "exit_after_timeout", "timeout_seconds": 3600}}
        self.command("governance", "adopt_governance", {"config": governance, "reason": "Adopt isolated acceptance governance"}, "governance")
        self.command("governance", "activate_governance", {"reason": "Enable this isolated connection acceptance"}, "activate")
        charter["allowed_tools"].append("read_document")
        self.command("governance", "amend_charter", {"charter": charter, "reason": "Read only explicitly supplied synthetic material"}, "document")
        key = json.loads(provider_config.read_text(encoding="utf-8-sig"))["api_key"]
        receipt = self.command("models", "save_connection", {"connection_id": "go-deepseek", "expected_revision": 0,
            "name": "OpenCode Go · DeepSeek V4.1 Flash", "profile": "openai_compatible", "model": "deepseek-v4.1-flash",
            "max_output_tokens": 2048, "base_url": "https://opencode.ai/inference/go/openai/v1", "api_key": key}, "connection")
        operation = self.wait("operations", receipt["operation_id"])
        assert operation["status"] == "succeeded", "Connection not saved"
        self.command("models", "grant_model_resources", {"max_calls": 6, "allow_unknown_cost": True,
            "reason": "User-authorized Go subscription; initial six-call acceptance batch, unknown actual cost retained"}, "resources")
        self.command("models", "set_connection", {"connection_id": "go-deepseek", "expected_revision": 1,
            "enabled": True, "make_default": True}, "default")
        assert not self.request_rows(), "Saving/configuring must not start inference"
        self.meta["prepared"] = True
        self.persist()

    def request_rows(self):
        database = self.root / "modeld/state/modeld.sqlite3"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as cx:
            return list(cx.execute("SELECT id,au_id,state,digest FROM requests ORDER BY rowid"))

    def run(self, interrupt=False):
        self.login()
        label = "interrupt" if interrupt else "normal"
        material = "合成公开项目：共有三个模块，认证、模型接入、成果交付。交付负责人代号ALPHA。资料标识=" + secrets.token_hex(12)
        receipt = self.command("models", "start_model_check", {"connection_id": "go-deepseek", "expected_revision": 1,
            "binding_id": None, "document_name": label + "-synthetic.txt", "document_text": material}, label)
        check_id = receipt["check_id"]
        if interrupt:
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                check = next(x for x in self.models()["checks"] if x["id"] == check_id)
                if check["status"] not in ("queued", "running"):
                    raise RuntimeError("Check ended before cancellation observation; preserve this attempt")
                for attempt in check["attempts"]:
                    params = {"organization_id": self.meta["au_id"], "check_id": check_id, "attempt_id": attempt["id"], "after": 0}
                    stream = self.request("/api/v1/models/events?" + urlencode(params))
                    text = "".join(e.get("text", "") for e in stream["events"] if e["type"] == "text_delta")
                    if text and stream["state"] not in ("completed", "failed", "interrupted"):
                        self.meta["before_cancel"] = {"check_id": check_id, "request_id": attempt["id"],
                            "state": stream["state"], "cursor": stream["cursor"], "text_sha256": digest(text), "text_bytes": len(text.encode())}
                        self.persist()
                        self.command("models", "cancel_model_check", {"check_id": check_id,
                            "reason": "Acceptance: stop after actual original model text was observed"}, "cancel")
                        break
                else:
                    time.sleep(.03)
                    continue
                break
            else:
                raise RuntimeError("No original text observed; cancellation case not passed")
        check = self.wait("checks", check_id)
        self.meta[label + "_check"] = check
        self.persist()
        if not interrupt:
            assert check["status"] == "succeeded", "Real model check not successful; preserve original failure"
            self.verify_normal(check)
        else:
            self.meta["cancel_remote"] = self.client.request(self.meta["before_cancel"]["request_id"], self.meta["au_id"])
            self.persist()
            assert self.meta["cancel_remote"]["state"] == "interrupted", "Cancellation raced with completion; not interrupted evidence"

    def verify_normal(self, check):
        folder = self.app.creation.catalog.intent_for_au(self.meta["au_id"])["folder"]
        database = self.root / "core" / folder / "state.sqlite3"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as cx:
            content, sha, challenge = cx.execute("SELECT content,sha256,challenge FROM model_materials WHERE check_id=?", (check["id"],)).fetchone()
            rows = list(cx.execute("SELECT payload,result FROM model_attempts WHERE check_id=? ORDER BY rowid", (check["id"],)))
            tool = cx.execute("SELECT result FROM model_tool_receipts WHERE check_id=?", (check["id"],)).fetchone()
        assert len(rows) == 2 and tool
        first, second = [json.loads(row[0]) for row in rows]
        assert content not in rows[0][0] and challenge not in rows[0][0]
        assert json.loads(second["messages"][-1]["content"])["content"] == content
        assert second["messages"][-2].get("_native"), "Original native tool context missing"
        assert challenge in check["output"] and digest(content) == sha
        assert json.loads(tool[0])["sha256"] == sha
        self.meta["normal_verified"] = {"material_sha256": sha, "output_sha256": digest(check["output"]),
            "challenge_sha256": digest(challenge), "first_request_excludes_material": True, "tool_result_in_second_request": True,
            "native_tool_context_preserved": True, "original_tool_receipt": True}
        self.persist()

    def reopen(self):
        before = self.request_rows()
        self.login()
        models = self.models()
        for label in ("normal", "interrupt"):
            original = self.meta[label + "_check"]
            current = next(x for x in models["checks"] if x["id"] == original["id"])
            assert current["attempt_ids"] == original["attempt_ids"] and current["work_id"] == original["work_id"]
            if label == "normal":
                assert current["output"] == original["output"] and current["status"] == "succeeded"
                self.verify_normal(current)
        check_id = self.meta["interrupt_check"]["id"]
        self.command("models", "reconcile_model_check", {"check_id": check_id}, "reconcile")
        reconciled = self.wait("checks", check_id)
        assert reconciled["attempt_ids"] == self.meta["interrupt_check"]["attempt_ids"]
        assert self.request_rows() == before, "Original-request observation/reconciliation dispatched again"
        self.meta["reopened"] = {"principal_preserved": True, "normal_output_preserved": True,
            "requests_unchanged": True, "request_count": len(before), "reserved_calls": self.models()["resources"]["reserved_calls"],
            "reconciled_status": reconciled["status"]}
        self.persist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "normal", "interrupt", "reopen", "serve"])
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--bun", required=True)
    parser.add_argument("--provider-config", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.provider_config, "Explicit authorized provider configuration required"
        args.state_dir.mkdir(parents=True, exist_ok=False)
        config_dir = args.state_dir / "modeld"
        config_dir.mkdir()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        for role in ("admin", "worker"):
            path = config_dir / (role + ".token")
            path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
            os.chmod(path, 0o600)
        save(config_dir / "modeld.json", {"origin": "http://127.0.0.1:" + str(port), "state_directory": "state",
            "admin_token_file": "admin.token", "worker_token_file": "worker.token"})
        save(args.state_dir / "acceptance-private.json", {"username": "acceptance-owner", "password": secrets.token_urlsafe(32),
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "modeld_sha256": hashlib.sha256((REPO / "services/modeld/dist/main.js").read_bytes()).hexdigest()})
    runner = Acceptance(args.state_dir, args.bun)
    try:
        runner.start()
        if args.mode == "prepare":
            runner.prepare(args.provider_config)
        elif args.mode in ("normal", "interrupt"):
            runner.run(args.mode == "interrupt")
        elif args.mode == "reopen":
            runner.reopen()
        else:
            runner.login()
            print("Isolated persisted acceptance service ready; private origin saved", flush=True)
            while not (runner.root / "stop-requested").exists():
                time.sleep(1)
        print(json.dumps({"mode": args.mode, "passed": True, "provider_request_count": len(runner.request_rows())}), flush=True)
    except Exception as error:
        runner.meta.setdefault("failures", []).append({"mode": args.mode, "type": type(error).__name__, "message": str(error)})
        runner.persist()
        print(json.dumps({"mode": args.mode, "passed": False, "error_type": type(error).__name__, "error": str(error)}), flush=True)
        raise
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
