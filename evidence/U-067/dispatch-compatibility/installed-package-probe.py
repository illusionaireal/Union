"""Validate a complete installed candidate against a schema declaration control.

The negative package has identical runtime bytes and an intentionally older schema
declaration. It tests the release gate, not execution of a historical binary.
All credentials/state are disposable; models use the existing explicit doubles.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import zipfile


def release_module(directory):
    spec = importlib.util.spec_from_file_location("installed_release", directory / "scripts/release_package.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(args):
    installed = Path(args.installed).resolve()
    # Only fixtures come from the checkout; every product import is installed.
    sys.path[:0] = [str(installed), str(Path(args.checkout).resolve())]
    from ai_union import console
    from tests.test_work_dispatch_compatibility import WorkDispatchCompatibilityTests
    from tests.test_work_dispatch import CallbackTransport
    assert Path(console.__file__).resolve().is_relative_to(installed)
    release = release_module(installed)
    config = release.read_config(Path(args.config))
    case = WorkDispatchCompatibilityTests("test_failed_prepare_rolls_back_marker_and_intent_before_transport")
    case.setUp()
    try:
        case.work_with_listing()
        case.prepare_materials()
        case.directory, case.intent = case.app.governance.locate(case.au_id)
        config["console_state"] = case.root
        config_path = Path(args.config)
        persisted_config = json.loads(config_path.read_text(encoding="utf-8"))
        persisted_config["console_state"] = str(case.root)
        config_path.write_text(json.dumps(persisted_config), encoding="utf-8")
        assert case.state()["schema_version"] == 3
        original_root = copy.deepcopy(case.state()["governance_root"])
        case.stop()
        release.activate("schema3-declaration-control", config, stopped=True)
        case.start()
        # Start the attempt on this service instance, after the planned stop.
        case.attempt_id = case.start_attempt()
        request = case.request_value()
        channel = case.interrupt_call(request)
        original = copy.deepcopy(case.card()["steps"][0])
        assert case.state()["schema_version"] == 4
        case.stop()
        database_bytes = case.database().read_bytes()
        catalog_bytes = (case.root / "console.sqlite3").read_bytes()
        pointer = config["installation_root"] / "current.json"
        pointer_bytes = pointer.read_bytes()
        rejected = []
        for action in ("activate", "rollback", "run"):
            command = [sys.executable, "-I", "-B", "-X", "utf8", str(installed / "scripts/release_package.py"),
                       action, "console" if action == "run" else "schema3-declaration-control",
                       "--config", str(config_path)]
            if action != "run":
                command.append("--services-stopped")
            result = subprocess.run(command, cwd=installed, capture_output=True, text=True, timeout=15,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            assert result.returncode == 1 and "persisted AU schema" in result.stderr, action
            rejected.append(action)
            assert pointer.read_bytes() == pointer_bytes
            assert case.database().read_bytes() == database_bytes
            assert (case.root / "console.sqlite3").read_bytes() == catalog_bytes
        release.activate(installed.name, config, stopped=True)
        assert case.database().read_bytes() == database_bytes
        assert (case.root / "console.sqlite3").read_bytes() == catalog_bytes
        case.start()
        case.app.work.transport = replay = CallbackTransport()
        status, value, _ = case.request("/api/v1/work/commands", request)
        assert status == 200 and value["receipt"]["model_outcome"] == "unknown", value
        assert case.card()["steps"][0] == original
        assert case.state()["governance_root"] == original_root
        assert replay.calls == [] and len(channel.calls) == 1
        case.stop()
        release.verify_directory(installed)
        release.verify_directory(config["installation_root"] / "releases/schema3-declaration-control")
        print(json.dumps({
            "installed_product_import": True, "real_preflight": True,
            "ordinary_schema3_selection": True, "persisted_schema": 4,
            "incompatible_declaration_rejected": rejected,
            "rejection_preserves_database_catalog_and_pointer_bytes": True,
            "compatible_selection_preserves_database_and_catalog_bytes": True,
            "original_identity_and_reservation_preserved": True,
            "http_reopen_outcome": "unknown", "redispatched_calls": len(replay.calls),
            "installed_directories_immutable": True, "real_model_calls": 0,
            "negative_control": "same executable bytes; intentionally schema-3-only manifest",
        }))
    finally:
        case.tearDown()
        case.doCleanups()


def main(args):
    checkout = Path(args.checkout).resolve()
    archive = Path(args.archive).resolve()
    release = release_module(checkout)
    manifest = release.verify_archive(archive)
    assert manifest["source_state"] == "committed" and 4 in manifest["core_au_schemas"]
    with tempfile.TemporaryDirectory(prefix="union-installed-dispatch-") as folder:
        root = Path(folder)
        private = root / "private"
        private.mkdir(mode=0o700)
        for role in ("admin", "worker"):
            path = private / (role + ".token")
            path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
            path.chmod(0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        model_config = private / "modeld.json"
        model_config.write_text(json.dumps({"origin": f"http://127.0.0.1:{port}", "state_directory": "state",
            "admin_token_file": "admin.token", "worker_token_file": "worker.token"}), encoding="utf-8")
        model_config.chmod(0o600)
        config_path = root / "deployment.json"
        config_path.write_text(json.dumps({"installation_root": str(root / "code"),
            "console_state": str(root / "unused-empty-business"), "modeld_config": str(model_config),
            "python": sys.executable, "bun": str(Path(args.bun).resolve()), "console_port": port}), encoding="utf-8")
        config = release.read_config(config_path)
        release.install(archive, config)
        negative = root / "negative-control.zip"
        older = copy.deepcopy(manifest)
        older.update(release_id="schema3-declaration-control", core_au_schemas=[1, 2, 3])
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(negative, "w", zipfile.ZIP_DEFLATED) as target:
            for entry in source.infolist():
                target.writestr(entry, release.encoded(older) if entry.filename == "manifest.json" else source.read(entry))
        release.install(negative, config)
        installed = config["installation_root"] / "releases" / manifest["release_id"]
        result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(Path(__file__).resolve()),
            "--worker", "--installed", str(installed), "--config", str(config_path), "--checkout", str(checkout)],
            cwd=root, capture_output=True, text=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        if result.returncode:
            # Diagnostics remain local when the caller redirects this probe log.
            raise RuntimeError(result.stderr)
        observed = json.loads(result.stdout)
        observed.update(git_baseline=manifest["git_baseline"], source_state=manifest["source_state"],
            archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), files=len(manifest["files"]),
            deployment=False, scope="Windows installed package, disposable HTTP/SQLite fixture")
        Path(args.output).write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(observed))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "bun", "output", "installed", "config"):
        parser.add_argument("--" + name)
    parser.add_argument("--checkout", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    worker(args) if args.worker else main(args)
